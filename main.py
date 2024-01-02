# Import system modules
import os
import logging

# Import third-party modules
from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk.oauth.state_store import FileOAuthStateStore

import functions_framework

# Import local modules
from libs.gemini_ai import GeminiAI
from libs.weatherflow import WeatherFlow
from libs.slack import Slack
from libs.google_storage import GCPStorageInstallationStore

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s: %(message)s"
)

# Gather environment variables and configure
#######################################

# Your Google Cloud Storage bucket name
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")

# Your WeatherFlow station ID and API key
WF_API_KEY = os.getenv('WF_API_KEY')
WF_STATION_ID = os.getenv('WF_STATION_ID', '41817') # Defaults to Antartica

# Your Slack ID's, Tokens, and Secrets
SLACK_CLIENT_ID = os.getenv('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET = os.getenv('SLACK_CLIENT_SECRET')
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_SIGNING_SECRET = os.getenv('SLACK_SIGNING_SECRET')

# Your Gemini API key and Settings
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_CANDIDATE_COUNT = os.getenv('CANDIDATE_COUNT') # Optional
GEMINI_MAX_OUTPUT_TOKENS = os.getenv('MAX_OUTPUT_TOKENS') # Optional
GEMINI_TEMPERATURE = os.getenv('TEMPERATURE') # Optional

# Validate that variables have values
missing_variables = [var_name for var_name, var in
    {'GCS_BUCKET_NAME': GCS_BUCKET_NAME,
        'WF_API_KEY': WF_API_KEY,
        'WF_STATION_ID': WF_STATION_ID,
        'SLACK_CLIENT_ID': SLACK_CLIENT_ID,
        'SLACK_CLIENT_SECRET': SLACK_CLIENT_SECRET,
        'SLACK_BOT_TOKEN': SLACK_BOT_TOKEN,
        'SLACK_SIGNING_SECRET': SLACK_SIGNING_SECRET,
        'GEMINI_API_KEY': GEMINI_API_KEY}.items() if var is None or var == '']

if missing_variables:
    logging.error(
        "Error: The following configuration variables are missing or empty: %s", 
            ', '.join(missing_variables)
            )
    exit(1)



# Setup slack_bolt instance
#######################################

# OAuth settings see https://slack.dev/bolt-python/concepts#authenticating-oauth
slack_oauth_settings = OAuthSettings(
    client_id=SLACK_CLIENT_ID,
    client_secret=SLACK_CLIENT_SECRET,
    scopes=[
        "channels:read", 
        "channels:history", 
        "commands", 
        "users:read",
        "app_mentions:read",
        "chat:write",
        "im:history",
        ],
    # installation_store=FileInstallationStore(base_dir="/tmp"),
    installation_store=GCPStorageInstallationStore(bucket_name=GCS_BUCKET_NAME,client_id=SLACK_CLIENT_ID),
    state_store=FileOAuthStateStore(expiration_seconds=600, base_dir="/tmp")
)

app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
    oauth_settings=slack_oauth_settings,
#    process_before_response=True,
)
handler = SlackRequestHandler(app)

# Setup Slack Local Library instance
slack_instance = Slack()

# Setup GeminiAI instance
#######################################

gemini_ai_instance = GeminiAI(
    gemini_api_key=GEMINI_API_KEY,
    candidate_count=GEMINI_CANDIDATE_COUNT, 
    max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS, 
    temperature=GEMINI_TEMPERATURE
    )

# Setup WeatherFlow instance
#######################################

weatherflow_instance = WeatherFlow(wf_api_key=WF_API_KEY)


# Helper functions
#######################################

# ToDo, move to Slack Library
def get_bot_user_id(app):
    try:
        auth_info = app.client.auth_test(token=app._token)
        bot_user_id = auth_info["user_id"]
        return bot_user_id
    except SlackApiError as e:
        logging.error("Error retrieving bot user ID: %s", str(e.response.data))
        # Handle the error condition, maybe fallback to a default value or notify the user
        return None


##############
# Slack Slash Commands
##############
@app.command("/bard")
@app.command("/zbard")
def bard_command(ack, respond, command):
    ack()
    query = command["text"]
    user_id = command["user_id"]

    ai_response = gemini_ai_instance.query_ai(query)

    username = slack_instance.get_user_info(app, user_id)

    formatted_response = slack_instance.format_response([f"*{username}* asked \"_{query}_\"", slack_instance.adjust_markdown_for_slack(ai_response)])

    slack_message = formatted_response   

    logging.info(slack_message)
    
    try:
        respond({
            "response_type": "in_channel",
            "text": f"{username} asked \"{query}\".\n\n\nGenerated response:\n{ai_response}",  # Fallback text
            "blocks": slack_message
        })
    except Exception as e:
            logging.error("Error sending to Slack: %s", e)


@app.command("/wf")
@app.command("/zwf")
def wf_command(ack, respond, command):
    ack()

    station_id = WF_STATION_ID

    if command["text"] is not None and command["text"] != "":
        logging.debug("wf_command received: %s", command["text"])
        station_id = command["text"]
    else:
        logging.debug("wf_command received nothing, using station_id: %s", station_id)
        
    wf_response = weatherflow_instance.get_wf_weather(station_id=station_id)

    formatted_response = (slack_instance.format_response(wf_response))

    slack_message = formatted_response   
    
    respond({
        "response_type": "in_channel",
        "text": f"{wf_response}",  # Fallback text
        "blocks": slack_message
    })

##############
# Slack Messages and Events
##############
@app.message("bard")
@app.event("app_mention")
def bard_say(message, say, event):

    bot_user_id = get_bot_user_id(app)

    if message:
        if Slack.is_duplicate(message):
            logging.info("Duplicate message ID: %s ignored", message["ts"])
            return

        logging.debug("Message ID: %s", message["ts"])

        query = message.get("text", None)
        user_id = message.get("user", "")
        logging.info("bard_say received a message for %s, %s asked: %s", bot_user_id, user_id, query)
    elif event:     
        if Slack.is_duplicate(event):
            logging.info("Duplicate message ID: %s ignored", message["ts"])
            return

        logging.debug("Event ID: %s", event["ts"])

        query = event.get("text", None)
        user_id = event.get("user", "")
        logging.info("bard_say received an event for %s, %s asked: %s", bot_user_id, user_id, query)
    else:
        say({
            "response_type": "in_channel",
            "text": "Hi :wave:"
        })
        return

    if query and query != "" and query != "bard" and query != f"<@{bot_user_id}>":
        ai_response = gemini_ai_instance.query_ai(query)
    else:
        say({
            "response_type": "in_channel",
            "text": "Hi :wave:"
        })
        return

    # Check if user_id is not an empty string before formatting the response
    if user_id:
        formatted_response = slack_instance.format_response(f"<@{user_id}>, {slack_instance.adjust_markdown_for_slack(ai_response)}")
    else:
        # Handle the case where user_id is an empty string
        formatted_response = slack_instance.format_response(ai_response)

    slack_message = formatted_response

    logging.info(slack_message)
    
    try:
        say({
            "response_type": "in_channel",
            "text": f"<@{user_id}>, {slack_instance.adjust_markdown_for_slack(ai_response)}",  # Fallback text
            "blocks": slack_message
        })
    except Exception as e:
            logging.error("Error sending to Slack: %s", e)

# Handle events
@app.event("message")
def handle_message_events(body):
    logging.debug(body)

# Entry point function for Functions Framework when running on GCP Cloud Functions
@functions_framework.http
def main(request):
    return handler.handle(request)
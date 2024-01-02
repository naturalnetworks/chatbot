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

# Your Google Cloud Storage bucket name
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

# Setup slack_bolt instance

# OAuth settings see https://slack.dev/bolt-python/concepts#authenticating-oauth
slack_oauth_settings = OAuthSettings(
    client_id=os.environ["SLACK_CLIENT_ID"],
    client_secret=os.environ["SLACK_CLIENT_SECRET"],
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
    installation_store=GCPStorageInstallationStore(bucket_name=GCS_BUCKET_NAME,client_id=os.environ["SLACK_CLIENT_ID"]),
    state_store=FileOAuthStateStore(expiration_seconds=600, base_dir="/tmp")
)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    oauth_settings=slack_oauth_settings,
#    process_before_response=True,
)
handler = SlackRequestHandler(app)

# Setup GeminiAI instance
gemini_api_key = os.environ["GEMINI_API_KEY"]
gemini_ai_instance = GeminiAI(gemini_api_key=gemini_api_key,candidate_count=1, max_output_tokens=8192, temperature=0.0)

# Setup WeatherFlow instance
wf_api_key = os.environ.get("WF_API_KEY")
wf_station_id = os.environ.get("WF_STATION_ID")
weatherflow_instance = WeatherFlow(wf_api_key=wf_api_key)

# Setup Slack instance
slack_instance = Slack()

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

    station_id = wf_station_id

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
        query = message.get("text", None)
        user_id = message.get("user", "")
        logging.info("bard_say received a message for %s: %s asked %s", bot_user_id, user_id, query)
    elif event:     
        query = event.get("text", None)
        user_id = event.get("user", "")
        logging.info("bard_say received an event for %s: %s asked %s", bot_user_id, user_id, query)
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
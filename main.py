# Import system modules
import os
import logging
import re

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
GEMINI_CANDIDATE_COUNT = int(os.getenv('GEMINI_CANDIDATE_COUNT', '1'))
GEMINI_MAX_OUTPUT_TOKENS = int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', '8192'))
GEMINI_TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', '0.9'))
GEMINI_SAFETY_HARRASSMENT = os.getenv('GEMINI_SAFETY_HARRASSMENT') # Optional
GEMINI_SAFETY_SEX = os.getenv('GEMINI_SAFETY_SEX') # Optional
GEMINI_SAFETY_DANGER = os.getenv('GEMINI_SAFETY_DANGER') # OPtional
GEMINI_SAFETY_HATE = os.getenv('GEMINI_SAFETY_HATE') # Optional

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
    temperature=GEMINI_TEMPERATURE,
    safety_harrassment=GEMINI_SAFETY_HARRASSMENT,
    safety_sex=GEMINI_SAFETY_SEX,
    safety_danger=GEMINI_SAFETY_DANGER,
    safety_hate=GEMINI_SAFETY_HATE
    )

# Setup WeatherFlow instance
#######################################

weatherflow_instance = WeatherFlow(wf_api_key=WF_API_KEY)


def process_bard_request(data, say_function):
    """
    Process a Bard request and generate a response using the Google Gemini API.

    Args:
        data (dict): The data containing the message/event information.
        say_function (function): The function to send a response back to the channel.

    Returns:
        None: If the message/event is a duplicate or from another app.
        None: If the query is empty or equal to "bard" or the bot user ID.

    Raises:
        None

    Description:
        This function processes a Bard request and generates a response using the Google Gemini API.
        It checks if the message/event is a duplicate or from another app and returns None in such cases.
        It then retrieves the query and user ID from the data.
        If the query is not empty, not equal to "bard", and not equal to the bot user ID,
        it calls the gemini_ai_instance.query_ai function to generate the AI response.
        If the query is empty or equal to "bard" or the bot user ID, it sends a "Hi :wave:" message.
        It then formats the response using the user_id and the AI response.
        Finally, it sends the formatted response back to the channel using the say_function.

    """
    if Slack.is_duplicate(data):
        logging.info("Duplicate message/event ID: %s ignored", data["ts"])
        return

    bot_user_id = Slack.get_bot_user_id(app)

    if 'bot_id' in data:
        logging.info("Received message from another app: %s, ignoring", data.get("bot_id", None))
        return

    logging.debug("ID: %s", data["ts"])

    query = data.get("text", None)
    user_id = Slack.format_user_mention(data.get("user", ""))

    logging.info("bard_say received a message/event for %s, %s asked: %s", bot_user_id, user_id, query)

    if query and query != "" and query != "bard" and query != f"<@{bot_user_id}>":

        ai_response = gemini_ai_instance.query_ai(user_id, query)
        
    else:
        say_function({
            "response_type": "in_channel",
            "text": "Hi :wave:"
        })
        return

    # Check if user_id is not an empty string before formatting the response
    if user_id:
        formatted_response = slack_instance.format_response(f"{user_id}, {slack_instance.adjust_markdown_for_slack(ai_response)}")
    else:
        # Handle the case where user_id is an empty string
        formatted_response = slack_instance.format_response(ai_response)

    slack_message = formatted_response
    logging.info(slack_message)

    try:
        say_function({
            "response_type": "in_channel",
            "text": f"{user_id}, {slack_instance.adjust_markdown_for_slack(ai_response)}",  # Fallback text
            "blocks": slack_message
        })
    except Exception as e:
        logging.error("Error sending to Slack: %s", e)


##############
# Slack Slash Commands
##############

@app.command("/bard")
@app.command("/zbard")
def bard_command(ack, respond, command):
    """
    A Slack command function that generates a response using the Google Gemini API and sends it back to the channel.
    
    Parameters:
        - ack: Function to acknowledge the command.
        - respond: Function to send a response back to the channel.
        - command: A dictionary containing the command details, including the text and user ID.
        
    Returns:
        None
        
    Raises:
        Exception: If there is an error sending the response to Slack.
    """
    ack()
    
    query = command["text"]
    user_id = command["user_id"]

    ai_response = gemini_ai_instance.query_ai(user_id, query)

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
    """
    A Slack command function that retrieves weather information and sends it back to the channel.
    Parameters:
    - ack: Function to acknowledge the command.
    - respond: Function to send a response back to the channel.
    - command: The command object containing user input.
    """
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

# @app.command("/bardimage")
# def handle_image_command(ack, respond, command):
#     ack()  # Acknowledge the command receipt

#     prompt = command["text"]  # Get the user's prompt from the command

#     image_url = gemini_ai_instance.generate_image(prompt)

#     # Send the image URL back to Slack
#     respond(image_url)

##############
# Slack Messages and Events
##############

# Bard Message Route
# @app.message("bard")
# def handle_bard_message(message, say):
#     """
#     Handle the bard message event in Slack.

#     Args:
#         message (dict): The message data containing information about the bard message.
#         say (function): The function to send a message back to Slack.

#     Returns:
#         None
#     """
#     logging.debug("handle_bard_message received message: %s", message)
#     process_bard_request(message, say)

@app.message(re.compile(r"\bbard\b", re.IGNORECASE))
def handle_bard_message(message, say, context):
    """
    Handle the bard message event in Slack.

    This function is triggered when a message containing the word "bard" (case-insensitive) is received in Slack. It checks if there is a match in the context and if so, it processes the bard request by calling the `process_bard_request` function with the message and `say` as arguments.

    Args:
        message (dict): The message data containing information about the bard message.
        say (function): The function to send a message back to Slack.
        context (dict): The context data containing information about the message and its matches.

    Returns:
        None
    """
    # Check if there's a match (the list won't be empty)
    if context['matches']:
        logging.debug("handle_bard_message received and matched message: %s", message)
        process_bard_request(message, say)

# Bard Event Route
@app.event("app_mention")
def handle_bard_event(event, say):
    """
    Handle the app mention event in Slack.

    Args:
        event (dict): The event data containing information about the app mention.
        say (function): The function to send a message back to Slack.

    Returns:
        None
    """
    logging.debug("handle_bard_event received event: %s", event)
    process_bard_request(event, say)


# Handle other events
@app.event("message")
def handle_message_events(event, say, body):
    """
    Handle message events in the Slack app.

    Args:
        event (dict): The event object containing information about the message.
        say (function): The function to send a message to the Slack channel.
        body (dict): The body of the request.

    Returns:
        None
    """
    logging.debug("handle_message_events received event: %s", event)
    if event.get("channel_type") == "im":
        process_bard_request(event, say)
    else:
        logging.debug(body)


# Entry point function for Functions Framework when running on GCP Cloud Functions
@functions_framework.http
def main(request):
    return handler.handle(request)
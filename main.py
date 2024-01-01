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
    scopes=["channels:read", "channels:history", "commands", "users:read"],
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
            logging.error(f"Error sending to Slack: %e", e)
            respond({
                "response_type": "ephemeral",
                "text": f"Error sending to Slack: {e}",
            })


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

# Entry point function for Functions Framework when running on GCP Cloud Functions
@functions_framework.http
def main(request):
    return handler.handle(request)
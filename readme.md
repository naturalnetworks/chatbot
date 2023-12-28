# Slack Google Gemini AI Bot

This repository contains a Slack bot implemented in Python using the Slack Bolt framework. The bot leverages the Google Gemini API for text generation and integrates with the WeatherFlow API to provide weather reports. 

It is designed to run as a Google Cloud Function.

## Notes

### Cloud Function Cold Starts

Google Cloud Functions will close down and cause a 'cold start' upon next trigger. This exhibits as occasional latency when calling /bard or /wf . The way around this is to set the minimum instances to something more than 0. E.G:

gcloud functions deploy chatbot \
--project PROJECT_ID \
--gen2 \
--runtime=python312 \
--region=REGION \
--source=. \
--trigger-http \
--entry-point=main \
--env-vars-file .env.yaml \
--allow-unauthenticated \
--memory=256Mi
--min-instances=1

See https://cloud.google.com/functions/docs/configuring/min-instances for more information.

Note that this will cost money as it will no longer be 'free tier' usage.

## Features

### 1. AI Text Generation

The bot can generate responses to user queries using the Google Gemini API. The responses are formatted in Slack's `mrkdwn` syntax for better presentation.

### 2. Weather Reports

The bot can fetch real-time weather reports from a WeatherFlow Tempest station using the WeatherFlow API. The weather report is formatted in `mrkdwn` for easy readability.

## Setup

### Dependencies

- Python 3.x
- Slack Bolt (`pip install slack-bolt`)
- Google Generative AI (`pip install google-generativeai`)
- Flask Functions Framework (`pip install functions-framework`)
- Requests (`pip install requests`)

### Setup Slack

Create a new Slack App

This will provide the Slack tokens/secrets etc. You will also need set up a Bot Token (xoxb-) and Bot Token Scopes - I set 'commands' and 'users:read'.

Create two new slash commands, one for /bard and one for /wf

The URL for the above slash commands will be provided when you deploy the Google Cloud Function. Be sure to append /slack/events on the end. EG

https://australia-southeast1-tasty-koala-123456.cloudfunctions.net/chatbot/slack/events

### Get a Google AI key

Go to https://ai.google.dev/tutorials/setup and click "Get an API key" and then "Create API key in new project" . Fill out the details as you see fit.

### Environment Variables

Make sure to set the following environment variables:

- `GEMINI_API_KEY`: API key for the Google Gemini API.
- `SLACK_BOT_TOKEN`: Slack bot token.
- `SLACK_SIGNING_SECRET`: Slack app signing secret.
- `WF_API_KEY`: API key for the WeatherFlow API.
- `WF_STATION_ID`: WeatherFlow Tempest station ID.

### Usage

1. Clone the repository:

   ```bash
   git clone https://github.com/naturalnetworks/chatbot.git
   cd chatbot

### Set up Environment Variables

Create .env.yaml, add

GEMINI_API_KEY: your_gemini_api_key \
SLACK_BOT_TOKEN: your_slack_bot_token \
SLACK_SIGNING_SECRET: your_slack_signing_secret \
WF_API_KEY: your_wf_api_key \
WF_STATION_ID: your_wf_station_id 

### Deploy to your GCP project

gcloud functions deploy chatbot \
--project PROJECT_ID \
--gen2 \
--runtime=python312 \
--region=REGION \
--source=. \
--trigger-http \
--entry-point=main \
--env-vars-file .env.yaml \
--allow-unauthenticated \
--memory=256Mi


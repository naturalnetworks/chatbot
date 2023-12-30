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
--memory=256Mi \
--min-instances=1

See https://cloud.google.com/functions/docs/configuring/min-instances for more information.

Note that this will cost money as it will no longer be 'free tier' usage.

While you're looking at instance counts, maybe specify --max-instances too - by default a 2nd generation cloud function will set 100. A request will be held for 30 seconds while waiting for an instance to become available.

See https://cloud.google.com/functions/docs/configuring/max-instances for more information.

> I've included instructions below on how to deploy this as a 'Cloud Run' service which offers up better cold start performance

### API Keys and Secrets

In this case Environment Variables are being used - not particularly good practice, it's simple but not scalable.

Better to use Google's Secret Manager, see https://cloud.google.com/functions/docs/configuring/secrets

## Features

### 1. AI Text Generation

The bot can generate responses to user queries using the Google Gemini API. The responses are formatted in Slack's `mrkdwn` syntax for better presentation.

### 2. Weather Reports

The bot can fetch real-time weather reports from a WeatherFlow Tempest station using the WeatherFlow API. The weather report is formatted in `mrkdwn` for easy readability.

## Setup

### Google Compute Platform

Take a look at https://cloud.google.com/functions/docs/create-deploy-http-python to get an idea on what's required to set up GCP to host your Cloud Function.

### Dependencies

- Python 3.x
- Slack Bolt
- Google Generative AI
- Functions Framework
- Requests

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

   ```
   bash
   git clone https://github.com/naturalnetworks/chatbot.git
   cd chatbot
   ```

2. Download/Install python libraries locally:

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

### Set up Environment Variables

Create .env.yaml, add

```
GEMINI_API_KEY: your_gemini_api_key \
SLACK_BOT_TOKEN: your_slack_bot_token \
SLACK_SIGNING_SECRET: your_slack_signing_secret \
WF_API_KEY: your_wf_api_key \
WF_STATION_ID: your_wf_station_id
```

### Deploy to your GCP project to Cloud Functions

```
gcloud functions deploy chatbot \
--project-PROJECT_ID \
--gen2 \
--runtime=python312 \
--region=REGION \
--source=. \
--trigger-http \
--entry-point=main \
--env-vars-file .env.yaml \
--allow-unauthenticated \
--memory=256Mi
```

### Alternatively, you can build a docker image and use Cloud Run

**Create repository to store image** \
```
gcloud artifacts repositories create docker-repo \
--project=PROJECT_ID
--repository-format=docker \
--location=REGION \
--description="Docker Images"
```

**Use GCP's cloud based image building service to create the docker image** \
```
gcloud builds submit \
--pack image-us-west2-docker.pkg.dev/PROJECT_ID/docker-repo/bardbot,env=GOOGLE_FUNCTION_TARGET=main
```

**Deploy the new Cloud Run service using the image** \
```
gcloud run deploy bardbot \
--image us-west2-docker.pkg.dev/PROJECT_ID/docker-repo/bardbot:latest \
--region=us-west2 \
--platform=managed \
--env-vars-file=.env.yml \
--allow-unauthenticated
```

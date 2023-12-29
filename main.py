import os
import logging
import re # need regular expressions to adapt markdown to mrkdwn...

# Import modules from the local libs directory
# These can be downloaded/installed using:
#  'pip install -r requirements.txt -t libs'
# This saves Cloud Function cold start time
import libs.requests # needed for WeatherFlow API
from libs.slack_bolt import App
from libs.slack_bolt.adapter.flask import SlackRequestHandler
import libs.functions_framework

import libs.google.generativeai as genai

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "ERROR"), format="%(levelname)s: %(message)s"
)

# Instantiate the Google Gemini API
gemini_api_key = os.environ["GEMINI_API_KEY"]
genai.configure(api_key=gemini_api_key)

# gemini-pro: optimized for text-only prompts.
# gemini-pro-vision: optimized for text-and-images prompts.
model = genai.GenerativeModel('gemini-pro')

# Gemini Chat Conversations 
chat = model.start_chat(history=[])

# WeatherFlow API key and Station ID
api_key = os.environ.get("WF_API_KEY")
station_id = os.environ.get("WF_STATION_ID")

# Create a global HTTP session for connection pooling/persistence
http_session = requests.Session()

# instantiate the Slack app
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
#    process_before_response=True,
)
handler = SlackRequestHandler(app)

def adjust_markdown_for_slack(markdown_text):
    """
    Adjusts the given markdown text to be compatible with Slack's mrkdwn format.

    Parameters:
    - markdown_text (str): The original markdown text to be adjusted.

    Returns:
    - str: The adjusted markdown text.

    Example:
    ```
    original_text = "# Hello, world!"
    adjusted_text = adjust_markdown_for_slack(original_text)
    print(adjusted_text)
    # Output: "*Hello, world!*"
    ```
    """
    # Identify code blocks and store them in a list
    code_blocks = re.findall(r'```.*?```', markdown_text, flags=re.DOTALL)

    # Replace code blocks with a placeholder to avoid modifications
    for i, code_block in enumerate(code_blocks):
        placeholder = f'__CODE_BLOCK_{i}__'
        markdown_text = markdown_text.replace(code_block, placeholder)

    # Change double asterisks to single asterisks for emphasis
    markdown_text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', markdown_text)

    # Add a newline after list items
    # markdown_text = re.sub(r'(\d+\.)', r'\1\n', markdown_text)

    # Convert headers to Slack's mrkdwn format
    markdown_text = re.sub(r'^# (.+)$', r'*\1*', markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(r'^## (.+)$', r'**\1**', markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(r'^### (.+)$', r'***\1***', markdown_text, flags=re.MULTILINE)

    # Use a monospaced font for better table representation
    markdown_text = markdown_text.replace('|', '`|`')

    # Restore code blocks from placeholders
    for i, placeholder in enumerate(code_blocks):
        markdown_text = markdown_text.replace(f'__CODE_BLOCK_{i}__', placeholder)

    return markdown_text

def get_user_info(user_id):
    """
    Retrieves user information based on the provided user ID.

    :param user_id: The ID of the user for whom the information is to be retrieved.
    :type user_id: int or str
    :return: The normalized real name of the user.
    :rtype: str
    """
    try:
        user_info = app.client.users_info(user=user_id)
        return user_info["user"]["profile"]["real_name_normalized"]
    except Exception as e:
        logging.error(f"get_user_info returned: {e}")
        return "Unknown User"

def query_ai(respond, query):
    """
    Query the AI model with a given query and return the response.

    :param respond: a function to handle the response
    :param query: the query to be processed by the AI model
    :return: the generated response from the AI model

    The Ai query can be adjusted via parameters
    Refer to https://ai.google.dev/models/gemini#model_attributes and 
    https://ai.google.dev/docs/concepts#model_parameters .

    """
    try:
#        ai_query_response = model.generate_content(
        ai_query_response = chat.send_message(
            query,
            generation_config=genai.types.GenerationConfig(
                # Only one candidate for now.
                candidate_count=1,
                max_output_tokens=800,
                temperature=0.1)
            )
        # logging.debug(f"query_ai returned: {ai_query_response.text}")
        # return ai_query_response.text
        return adjust_markdown_for_slack(ai_query_response.text)
       
    except Exception as e:
        logging.error(f"query_ai returned: {e}")
        return "Error generating AI response. Please try again later."

# Bard slash command
@app.command("/bard")
def bard_command(ack, respond, command):
    """
    This function is a command handler for the "/bard" command in the Slack app. 
    It takes in four parameters: `ack`, `respond`, `command`. The `ack` parameter 
    is a function used to acknowledge the receipt of the command. The `respond` 
    parameter is a function used to send a response back to the user. 
    
    The `command` parameter is a dictionary containing information about the command.

    The function first calls the `ack` function to acknowledge the receipt of the 
    command. Then, it extracts the `text` and `user_id` from the `command` dictionary. 
    The `text` variable stores the text of the command, while the `user_id` variable 
    stores the id of the user who issued the command.

    Next, the function calls the `get_user_info` function to retrieve the username 
    associated with the `user_id`. The `username` variable stores the retrieved username.

    After that, the function calls the `query_ai` function to generate an AI response 
    based on the `query` text. The `query_ai` function takes in the `respond` function 
    and the `query` text as parameters. The generated AI response is stored in the 
    `ai_response` variable.

    The function then constructs a list of blocks for the Slack response. The list 
    contains a single dictionary with a `"type"` of `"section"`. The `"text"` field 
    of the dictionary contains a markdown-formatted string that includes the 
    `username`, the `query` text, and the `ai_response`.

    Finally, the function uses the `respond` function to send the response back to 
    the user. The response includes the `username`, the `query` text, and the 
    `ai_response` as both text and blocks.

    This function sends a formatted response message to the slack bot.
    """
    ack()
    query = command["text"]
    user_id = command["user_id"]

    username = get_user_info(user_id)

    ai_response = query_ai(respond, query)

    # Construct blocks for the Slack response
    response_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{username} asked \"{query}\".\nGenerated response:\n{ai_response}"
            }
        }
    ]

    # Use the app's respond method to send the response with blocks and fallback text
    respond({
        "response_type": "in_channel",
        "text": f"{username} asked \"{query}\".\nGenerated response:\n{ai_response}",  # Fallback text
        "blocks": response_blocks
    })

@app.command("/wf")
def get_tempest_weather_mrkdwn(ack, respond):
    """
    Generates a Weatherflow Tempest weather report in mrkdwn format and sends it as a response.

    Parameters:
    - ack: A function used to acknowledge the request.
    - respond: A function used to send the response.

    This function sends a formatted response message to the slack bot.
    """
    ack()

    url = f'https://swd.weatherflow.com/swd/rest/observations/station/{station_id}?api_key={api_key}'
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Use the global session for making the HTTP request
    response = http_session.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()

        # Extract relevant weather data points
        station_public_name = data["public_name"]
        temperature = data["obs"][0]["air_temperature"]
        feels_like = data["obs"][0]["feels_like"]
        humidity = data["obs"][0]["relative_humidity"]
        wind_gust = data["obs"][0]["wind_gust"]
        wind_direction = data["obs"][0]["wind_direction"]
        pressure = data["obs"][0]["sea_level_pressure"]
        rain_rate = data["obs"][0]["precip_accum_last_1hr"]
        rain_accumlated = data["obs"][0]["precip"]
        solar_radiation = data["obs"][0]["solar_radiation"]
        uv = data["obs"][0]["uv"]
        lightning_strike_distance = data["obs"][0]["lightning_strike_last_distance"]

        # Convert wind direction from degrees to cardinal direction
        if wind_direction < 22.5:
            wind_direction = "N"
        elif wind_direction < 67.5:
            wind_direction = "NE"
        elif wind_direction < 112.5:
            wind_direction = "E"
        elif wind_direction < 157.5:
            wind_direction = "SE"
        elif wind_direction < 202.5:
            wind_direction = "S"
        elif wind_direction < 247.5:
            wind_direction = "SW"
        elif wind_direction < 292.5:
            wind_direction = "W"
        elif wind_direction < 337.5:
            wind_direction = "NW"
        else:
            wind_direction = "N"

        # Format as mrkdwn
        wf_mrkdwn = f"""
*{station_public_name} Tempest Weather Report*
*Temperature/Feels Like:* {temperature}°C/{feels_like}°C | *Humidity:* {humidity}% | *Wind Gust/Direction:* {wind_gust}km/h - {wind_direction} | *Pressure:* {pressure} mb | *Rain Rate/Accumlated:* {rain_rate}mm/hr/{rain_accumlated}mm | *Last Lightning Strike Distance:* {lightning_strike_distance}km | *Solar Radiation:* {solar_radiation}W/m^2 | *UV Index:* {uv}
        """

        response_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{wf_mrkdwn}"
                }
            }
        ]
       
        # Use the app's respond method to send the response with blocks and fallback text
        respond({
            "response_type": "in_channel",
            "text": f"{wf_mrkdwn}",  # Fallback text
            "blocks": response_blocks
        })
    else:
        respond({
            "response_type": "in_channel",
            "text": "Could not retrieve weather data."
        })

# Entry point function for Functions Framework
@functions_framework.http
def main(request):
    return handler.handle(request)

import re
import logging
from collections import deque


class Slack:

    # Define a deque to store the last N messages
    last_messages = deque(maxlen=10)

    @staticmethod
    def format_response(responses):
        """
        Format response for Slack using Slack's building blocks.

        :param responses: Single response or list of responses from the query.
        :return: Formatted message for Slack.
        """
        if not isinstance(responses, list):
            responses = [responses]

        formatted_response = []

        for response in responses:
            # Assuming each response is in mrkdwn format
            formatted_response.append({"type": "divider"})

            # Split response into chunks of 3000 characters
            chunks = [response[i:i + 3000] for i in range(0, len(response), 3000)]

            for chunk in chunks:
                formatted_response.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": chunk
                    }
                })

        formatted_response.append({"type": "divider"})
        return formatted_response

    @staticmethod
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
        """
        if not markdown_text:
            return ""  # Handle the case where input is None or empty

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

        # Handle unordered list items
        markdown_text = re.sub(r'^\* (.+)$', r'• \1', markdown_text, flags=re.MULTILINE)

        # Restore code blocks from placeholders
        for i, placeholder in enumerate(code_blocks):
            markdown_text = markdown_text.replace(f'__CODE_BLOCK_{i}__', placeholder)

        return markdown_text


    @staticmethod
    def get_user_info(app, user_id):
        """
        Retrieves user information based on the provided user ID.

        :param app: The Slack Bolt app instance.
        :type app: slack_bolt.App
        :param user_id: The ID of the user for whom the information is to be retrieved.
        :type user_id: int or str
        :return: The normalized real name of the user.
        :rtype: str
        """
        try:
            user_info = app.client.users_info(user=user_id)
            return user_info["user"]["profile"]["real_name_normalized"]
        except Exception as e:
            return "Unknown User"

    @staticmethod
    def format_user_mention(user_id):
        if user_id is not None and user_id != "":
            return f"<@{user_id}>"
        else:
            return None

    @staticmethod
    def is_duplicate(message, key="ts"):
        """
        Check if a message is a duplicate based on a specified key.

        :param message: Message to check.
        :param key: Key to identify uniqueness (default is "ts").
        :return: True if the message is a duplicate, False otherwise.
        """
        message_key = message.get(key)
        if message_key and message_key in Slack.last_messages:
            return True
        Slack.last_messages.append(message_key)
        return False

    @staticmethod
    def get_bot_user_id(app):
        try:
            auth_info = app.client.auth_test(token=app._token)
            bot_user_id = auth_info["user_id"]
            return bot_user_id
        except SlackApiError as e:
            logging.error("Error retrieving bot user ID: %s", str(e.response.data))
            # Handle the error condition, maybe fallback to a default value or notify the user
            return None

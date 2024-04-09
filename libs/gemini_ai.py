import os
import logging
import google.generativeai as genai


class GeminiAI:
    def __init__(self,
                    gemini_api_key=None,
                    candidate_count=1,
                    max_output_tokens=8192,
                    temperature=0.9,
                    safety_sex='unspecified',
                    safety_harrassment='unspecified',
                    safety_danger='unspecified',
                    safety_hate='unspecified'
                ):
       
        if gemini_api_key == None:
            logging.error("Gemini API Key not provided")
            raise Exception("Gemini API Key not provided")

        # Instantiate the Google Gemini API
        genai.configure(api_key=gemini_api_key)
    

        # gemini-pro: optimized for text-only prompts.
        # gemini-pro-vision: optimized for text-and-images prompts.
        # gemini-1.5-pro-latest: updated gemini-pro model with more capabilities
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')

        # Gemini Chat Conversations
        self.chat = self.model.start_chat(history=[])

        # Configurable generation parameters
        self.candidate_count = candidate_count
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature

        self.safety_sex = safety_sex
        self.safety_harrassment = safety_harrassment
        self.safety_danger = safety_danger
        self.safety_hate = safety_hate

        # Dictionary to store user-specific chat sessions
        self.user_chat_sessions = {}

    def start_user_chat(self, user_id):
        # Create a new chat session for the user
        chat_session = self.model.start_chat(history=[])
        self.user_chat_sessions[user_id] = chat_session

    def query_ai(self, user_id, query):
        """
        Query the AI model with a given query and return the response.

        :param query: the query to be processed by the AI model
        :return: the generated response from the AI model

        The AI query can be adjusted via parameters.
        Refer to https://ai.google.dev/models/gemini#model_attributes and
        https://ai.google.dev/docs/concepts#model_parameters.
        """
        try:

            # Check if the user has an existing chat session
            if user_id not in self.user_chat_sessions:
                self.start_user_chat(user_id)

            # Get the user's chat session
            user_chat_session = self.user_chat_sessions[user_id]

            safety_settings = {
                'harassment': self.safety_harrassment,
                'hate': self.safety_hate,
                'sex': self.safety_sex,
                'danger': self.safety_danger
            }

            ai_query_response = user_chat_session.send_message(
                query,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=self.candidate_count,
                    max_output_tokens=self.max_output_tokens,
                    temperature=self.temperature),
                safety_settings=safety_settings
                )

            return ai_query_response.text

        except genai.types.generation_types.BlockedPromptException as e:
            # Handle BlockedPromptException
            logging.error("Error generating AI response: %s", e)
            return f"Error generating AI response. Blocked: {e}"

        except Exception as e:
            # Handle other exceptions
            logging.error("Error generating AI response: %s", e)

            return "Error generating AI response. Please try again later."

# Example of using the GeminiAI class with custom parameters
if __name__ == "__main__":
    gemini_ai_instance = GeminiAI(gemini_api_key=os.environ["GEMINI_API_KEY"],candidate_count=1, max_output_tokens=200, temperature=0.2)
    response = gemini_ai_instance.query_ai("Hello, Gemini!")
    print(response)

import os
import logging
import google.generativeai as genai
from libs.firestore_handler import FirestoreHandler


class GeminiAI:
    def __init__(self,
                    gemini_api_key=None,
                    candidate_count=1,
                    max_output_tokens=8192,
                    temperature=0.9,
                    safety_sex='unspecified',
                    safety_harrassment='unspecified',
                    safety_danger='unspecified',
                    safety_hate='unspecified',
                    system_instruction=["You are a chatbot.",
                                        "Your name is bard.",
                                        "You are an expert at responding to questions and providing advice.",
                                        "You are helpful, creative, clever, and have a deadpan sense of humour.",
                                        "You provide references where applicable.",
                                        "You provide clear, concise, actionable, relevant, and informative responses.",
                                        "You always follow the Australian style guide."
                                        ]
                ):
       
        if gemini_api_key == None:
            logging.error("Gemini API Key not provided")
            raise Exception("Gemini API Key not provided")

        # Instantiate the Google Gemini API
        genai.configure(api_key=gemini_api_key)
    

        # See https://ai.google.dev/gemini-api/docs/models
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17', system_instruction=system_instruction)

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

        # Initialize Firestore Handler
        self.firestore_handler = FirestoreHandler() # Dictionary to store user-specific chat sessions
        self.user_chat_sessions = {}

    def start_user_chat(self, user_id):
        """
        Start a new chat session for a given user.

        Args:
            user_id (str): The ID of the user starting the chat session.

        Returns:
            None

        This function retrieves the chat history of the user from Firestore and starts a new chat session using the
        loaded history. The chat session is then stored in the `user_chat_sessions` dictionary, indexed by the user's ID.

        Note:
            - The `firestore_handler` attribute is used to load the chat history from Firestore.
            - The `model` attribute is used to start a new chat session.
            - The `user_chat_sessions` dictionary is used to store the chat sessions for each user.
        """
        chat_history = self.firestore_handler.load_chat_history(user_id)

        # Format history correctly for Gemini
        formatted_history = []
        for i, message in enumerate(chat_history):
            role = "user" if i % 2 == 0 else "model"
            formatted_history.append({
                "role": role,
                "parts": [{"text": message}] 
            })

        chat_session = self.model.start_chat(history=formatted_history)
        self.user_chat_sessions[user_id] = chat_session

#    def start_user_chat(self, user_id):
#        # Create a new chat session for the user
#        chat_session = self.model.start_chat(history=[])
#        self.user_chat_sessions[user_id] = chat_session

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

            # Save the interaction to Firestore
            self.firestore_handler.save_chat_turn(user_id, query, ai_query_response.text)

            return ai_query_response.text

        except genai.types.generation_types.BlockedPromptException as e:
            # Handle BlockedPromptException
            logging.error("Error generating AI response: %s", e)
            return f"Error generating AI response. Blocked: {e}"

        except Exception as e:
            # Handle other exceptions
            logging.error("Error generating AI response: %s", e)

            return "Error generating AI response. Please try again later."

    # def generate_image(self, prompt: str) -> str:
    #     """Generates an image using the Gemini Image Generation API.
    #     Args:
    #          prompt: The text prompt to generate the image from.

    #     Returns:
    #         The URL of the generated image.
    #     """
    #     try:
    #         response = genai.generate_image(  # Adjust based on the actual API call
    #             model='image-generation',  # Or the specific Gemini image model
    #             prompt=prompt,
    #             # Add any other parameters like image size, number of images, etc.
    #         )

    #         # Extract the image URL from the response
    #         image_url = response.artifacts[0].uri 
    #         return image_url

    #     except Exception as e:
    #         logging.error("Error generating image: %s", e)
    #         return "Sorry, there was an error generating the image."

# Example of using the GeminiAI class with custom parameters
if __name__ == "__main__":
    gemini_ai_instance = GeminiAI(gemini_api_key=os.environ["GEMINI_API_KEY"],candidate_count=1, max_output_tokens=200, temperature=0.2)
    response = gemini_ai_instance.query_ai("Hello, Gemini!")
    print(response)

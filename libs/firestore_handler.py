import os
import firebase_admin
from firebase_admin import firestore

"""
Note that Firestore will use the (default) database in the google project
"""

class FirestoreHandler:
    def __init__(self):
        firebase_admin.initialize_app()
        self.db = firestore.client()
        self.collection_name = os.getenv('FIRESTORE_COLLECTION_NAME', 'chat_histories')

    def load_chat_history(self, user_id):
        """Loads chat history from Firestore for a given user."""
        # Use a single string for collection name
        docs = self.db.collection(f'{self.database_name}_{self.collection_name}') \
               .where('user_id', '==', user_id).stream()
        history = [(doc.get('user'), doc.get('ai')) for doc in docs]
        return history

    def save_chat_turn(self, user_id, user_message, ai_response):
        """Saves a single turn of the chat to Firestore."""
        data = {
            'user_id': user_id,
            'user': user_message,
            'ai': ai_response
        }
        # Use a single string for collection name
        self.db.collection(f'{self.database_name}_{self.collection_name}').add(data)
import os

import firebase_admin
from firebase_admin import firestore

class FirestoreHandler:
    def __init__(self):
        firebase_admin.initialize_app()
        self.db = firestore.client()
        self.collection_name = os.getenv('FIRESTORE_COLLECTION_NAME', 'chat_histories')
        self.max_entries = 25  # Maximum number of entries to store

    def load_chat_history(self, user_id):
        """Loads chat history from Firestore for a given user,
           limiting to the most recent 'max_entries' entries.
        """
        docs = self.db.collection(self.collection_name) \
               .where('user_id', '==', user_id) \
               .order_by('timestamp', direction=firestore.Query.DESCENDING) \
               .limit(self.max_entries) \
               .stream()

        # Since we're getting entries in descending order (newest first),
        # reverse the list to present them in chronological order (FIFO).
        history = []
        for doc in docs:
            history.append(doc.get('user'))
            history.append(doc.get('model'))

        return history[::-1]  # Reverse the list 

    def save_chat_turn(self, user_id, user_message, model_response):
        """Saves a single turn of the chat to Firestore with a timestamp,
           and then enforces the entry limit.
        """
        data = {
            'user_id': user_id,
            'user': user_message,
            'model': model_response,
            'timestamp': firestore.SERVER_TIMESTAMP 
        }
        self.db.collection(self.collection_name).add(data)
        self.enforce_entry_limit(user_id) 

    def enforce_entry_limit(self, user_id):
        """Deletes oldest entries beyond the 'max_entries' limit."""
        # Get entries beyond the limit (oldest first)
        docs_to_delete = self.db.collection(self.collection_name) \
                               .where('user_id', '==', user_id) \
                               .order_by('timestamp') \
                               .offset(self.max_entries) \
                               .stream()

        for doc in docs_to_delete:
            doc.reference.delete()
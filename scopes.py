"""OAuth scopes shared by auth_setup, chat_client, and gmail_client.

Keep the union of every scope any client in this project might use here. When
this list changes, delete token.json and re-run auth_setup.py to re-consent.
"""
SCOPES = [
    "https://www.googleapis.com/auth/chat.messages.create",
    "https://www.googleapis.com/auth/gmail.send",
]

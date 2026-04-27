"""Shared Google Chat client. Posts text messages to a space using OAuth token.json."""
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from scopes import SCOPES

HERE = Path(__file__).parent


class ChatAuthError(RuntimeError):
    """Raised when token.json is missing or cannot be refreshed."""


def _load_credentials() -> Credentials:
    token_path = HERE / "token.json"
    if not token_path.exists():
        raise ChatAuthError("token.json missing. Run auth_setup.py first.")

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        else:
            raise ChatAuthError(
                "Credentials invalid and cannot refresh. Re-run auth_setup.py."
            )
    return creds


def send_message(space: str, text: str) -> str:
    """Post `text` to `space` (e.g. 'spaces/AAQAEKYlR3E'). Returns the message resource name."""
    creds = _load_credentials()
    chat = build("chat", "v1", credentials=creds, cache_discovery=False)
    resp = chat.spaces().messages().create(parent=space, body={"text": text}).execute()
    return resp.get("name", "")

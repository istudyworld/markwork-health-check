"""Send a plain-text email via Gmail API using the shared OAuth token.json.

The authenticated user is the sender (`me`) and also commonly the recipient,
since this is meant for self-monitoring alerts.
"""
import base64
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from scopes import SCOPES

HERE = Path(__file__).parent


class GmailAuthError(RuntimeError):
    """Raised when token.json is missing or cannot be refreshed."""


def _load_credentials() -> Credentials:
    token_path = HERE / "token.json"
    if not token_path.exists():
        raise GmailAuthError("token.json missing. Run auth_setup.py first.")

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
        else:
            raise GmailAuthError(
                "Credentials invalid and cannot refresh. Re-run auth_setup.py."
            )
    return creds


def send_email(to: str, subject: str, body: str) -> str:
    """Send a plain-text email. Returns the Gmail message ID."""
    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return sent.get("id", "")

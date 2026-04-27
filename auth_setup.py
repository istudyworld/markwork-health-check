"""One-time OAuth consent flow. Produces token.json."""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/chat.messages.create"]
HERE = Path(__file__).parent


def main() -> None:
    creds_path = HERE / "credentials.json"
    token_path = HERE / "token.json"

    if not creds_path.exists():
        raise SystemExit(
            f"Missing {creds_path}. Download an OAuth desktop client from "
            "Google Cloud Console and save it here as credentials.json."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.write_text(creds.to_json())
    print(f"Authorized. Token saved to {token_path}")


if __name__ == "__main__":
    main()

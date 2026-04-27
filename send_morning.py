"""Posts a randomly chosen morning greeting to the I Studyworld Chat space.

Uses a Google Chat space webhook URL (loaded from .env via MORNING_WEBHOOK_URL),
which avoids the OAuth + Chat-app-config dance entirely. Add the webhook in
Google Chat: open the space → Apps & integrations → Manage webhooks → Add.
"""
import json
import logging
import os
import random
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

WEBHOOK_URL = os.getenv("MORNING_WEBHOOK_URL", "").strip()
MESSAGES = [
    "Good morning team",
    "Good morning everyone",
    "Good morning",
]

LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "morning.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main() -> int:
    if not WEBHOOK_URL:
        logging.error("MORNING_WEBHOOK_URL is not set in .env")
        return 1

    text = random.choice(MESSAGES)
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="replace")[:200]
            logging.info("Sent %r (HTTP %s) %s", text, resp.status, body)
    except urllib.error.HTTPError as e:
        logging.error("HTTP %s posting %r: %s", e.code, text, e.read()[:200])
        return 1
    except Exception:
        logging.exception("Failed to post morning message")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

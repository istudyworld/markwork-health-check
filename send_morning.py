"""Posts 'Good morning team' to the configured Google Chat space."""
import logging
import sys
from pathlib import Path

from chat_client import ChatAuthError, send_message

SPACE = "spaces/AAQAEKYlR3E"
MESSAGE = "Good morning team"
HERE = Path(__file__).parent

LOG_DIR = HERE / "logs"
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "morning.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def main() -> int:
    try:
        name = send_message(SPACE, MESSAGE)
    except ChatAuthError as e:
        logging.error(str(e))
        return 1
    logging.info("Sent message %s", name)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        logging.exception("send_morning failed")
        sys.exit(1)

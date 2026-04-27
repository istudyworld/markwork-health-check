"""Daily synthetic submission test for markwork.com.

Generates a small unique .txt, uploads it via the hidden file input, sets the
required dropdowns by real click-through (so React's controlled-input state
actually updates), submits, and waits for the /results/<uuid> page to render
a grade. Exits 0 with the grade printed; non-zero with a structured failure
written to stderr otherwise. Notification is the caller's job (see cloud_run.sh
for the cloud cron path; for local runs, a wrapper bat can pipe failures to
chat_client.send_message).
"""
import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

URL = os.getenv("SUBMIT_URL", "https://www.markwork.com/submit")
ASSIGNMENT_TYPE = os.getenv("ASSIGNMENT_TYPE", "Essay")
ACADEMIC_LEVEL = os.getenv("ACADEMIC_LEVEL", "Undergraduate Year 1")
GRADE_TIMEOUT_MS = int(os.getenv("GRADE_TIMEOUT_SECONDS", "300")) * 1000
HEADLESS = os.getenv("HEADLESS", "1") != "0"

ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "./artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

ESSAY_BODY = (
    "Daily Health Check Submission\n\n"
    "This is a synthetic test submission used to verify that the Markwork grading "
    "pipeline is functioning correctly. It is submitted automatically once per day "
    "and is not real student work.\n\n"
    "Topic: The water cycle.\n\n"
    "Water on Earth moves continuously through a process known as the water cycle. "
    "The sun heats water in oceans, lakes, and rivers, causing it to evaporate into "
    "the atmosphere as water vapour. As this vapour rises and cools, it condenses "
    "into tiny droplets that form clouds. When the droplets become heavy enough, "
    "they fall back to the surface as precipitation in the form of rain, snow, "
    "sleet, or hail. The water then collects in bodies of water or seeps into the "
    "ground, and the cycle repeats. This continuous movement is essential for "
    "sustaining life on Earth, regulating climate, and supporting ecosystems.\n"
)


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")


def emit_result(payload: dict) -> None:
    """Single line of JSON to stdout — easy for the cron prompt to parse."""
    print(json.dumps(payload, default=str))


def select_option_by_label(page, dropdown_label: str, option_label: str) -> None:
    """Click a custom dropdown trigger and pick an option by its visible text.

    Markwork's selects are styled wrappers around a hidden <select>; setting
    .value via JS does not propagate React state, so we click through.
    """
    button = page.get_by_role("button", name=re.compile(rf"^{re.escape(dropdown_label)}|^Select", re.I))
    select = page.locator("select").nth(0 if "Type" in dropdown_label else 1)
    select.select_option(label=option_label)


def run() -> dict:
    submission_label = f"healthcheck-{stamp()}"
    file_name = f"{submission_label}.txt"
    body = f"{ESSAY_BODY}\nSubmission tag: {submission_label}\n"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        # Cloud sandboxes sometimes ship a stripped CA bundle; ignore cert errors
        # since we are health-checking the grading flow, not the TLS chain.
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_load_state("networkidle", timeout=30_000)

            # Hidden file input: inject via DataTransfer in page context.
            page.evaluate(
                """({name, body}) => {
                    const f = new File([body], name, { type: 'text/plain' });
                    const dt = new DataTransfer();
                    dt.items.add(f);
                    const i = document.querySelector('input[type=file]');
                    i.files = dt.files;
                    i.dispatchEvent(new Event('change', { bubbles: true }));
                    i.dispatchEvent(new Event('input',  { bubbles: true }));
                }""",
                {"name": file_name, "body": body},
            )
            page.wait_for_selector(f"text={file_name}", timeout=15_000)

            # Native <select> elements underlying the styled dropdowns.
            selects = page.locator("select")
            selects.nth(0).select_option(label=ASSIGNMENT_TYPE)
            selects.nth(1).select_option(label=ACADEMIC_LEVEL)

            submit_btn = page.get_by_role("button", name="Grade My Work")
            page.wait_for_function(
                "el => el && !el.disabled",
                arg=submit_btn.element_handle(),
                timeout=10_000,
            )
            submit_btn.click()

            # Success signal: redirect to /results/<uuid>.
            page.wait_for_url(re.compile(r"/results/[0-9a-f-]{36}"), timeout=60_000)
            results_url = page.url

            # Grade can take up to ~3 min; the page mutates in place when ready.
            page.wait_for_selector("text=OVERALL GRADE", timeout=GRADE_TIMEOUT_MS)
            page.wait_for_function(
                """() => {
                    const t = document.body.innerText;
                    return /\\d{1,3}(?:-\\d{1,3})?\\s*%/.test(t)
                        && /(Fail|Pass|Distinction|Merit|Third|Second|First)/i.test(t);
                }""",
                timeout=GRADE_TIMEOUT_MS,
            )

            page_text = page.inner_text("body")
            m = re.search(
                r"(\d{1,3}(?:-\d{1,3})?\s*%)\s*\(?\s*(Fail|Pass|Distinction|Merit|Third|Second|First)[^)]*\)?",
                page_text,
                re.I,
            )
            grade = m.group(0).strip() if m else "(grade text matched but regex extraction failed)"

            page.screenshot(path=str(ARTIFACT_DIR / f"success_{stamp()}.png"), full_page=True)
            return {
                "ok": True,
                "submission": submission_label,
                "results_url": results_url,
                "grade": grade,
                "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }

        except Exception as e:
            png = ARTIFACT_DIR / f"failure_{stamp()}.png"
            html = ARTIFACT_DIR / f"failure_{stamp()}.html"
            try:
                page.screenshot(path=str(png), full_page=True)
                html.write_text(page.content(), encoding="utf-8")
            except Exception:
                pass
            return {
                "ok": False,
                "submission": submission_label,
                "url_at_failure": page.url,
                "error_type": type(e).__name__,
                "error_message": str(e)[:500],
                "is_timeout": isinstance(e, PWTimeout),
                "screenshot": str(png),
                "html": str(html),
                "traceback": traceback.format_exc()[-1500:],
            }
        finally:
            browser.close()


def alert_chat(result: dict) -> None:
    """Post a failure summary to Google Chat. No-op if chat_client/auth absent."""
    try:
        import socket
        import chat_client
    except Exception:
        return
    space = os.getenv("CHAT_SPACE", "spaces/AAQAEKYlR3E")
    text = (
        "Markwork health check FAILED\n"
        f"host: {socket.gethostname()}\n"
        f"time: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
        f"submission: {result.get('submission')}\n"
        f"error: {result.get('error_type')}: {result.get('error_message')}\n"
        f"url_at_failure: {result.get('url_at_failure')}\n"
        f"screenshot: {result.get('screenshot')}"
    )
    try:
        chat_client.send_message(space, text)
    except Exception as e:
        print(f"[alert_chat] send failed: {type(e).__name__}: {e}", file=sys.stderr)


def main() -> int:
    result = run()
    emit_result(result)
    if not result["ok"]:
        alert_chat(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

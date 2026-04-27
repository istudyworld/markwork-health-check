"""One-time reconnaissance for the Markwork submit page.

Opens the page non-headless, optionally submits the configured attachment, then
prints all visible inputs/buttons and saves the post-submit DOM + screenshot.
Use the output to fill GRADE_SELECTOR (and refine the other selectors) in .env.

Usage:
    python inspect_submit_page.py            # inspect only, no submission
    python inspect_submit_page.py --submit   # also try to submit and dump after-state
"""
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
load_dotenv(HERE / ".env")

URL = os.getenv("SUBMIT_URL", "https://www.markwork.com/submit")
ATTACHMENT = HERE / os.getenv("ATTACHMENT_PATH", "test_submission.pdf")
FILE_INPUT = os.getenv("FILE_INPUT_SELECTOR", "input[type=file]")
SUBMIT_BTN = os.getenv("SUBMIT_BUTTON_SELECTOR", 'button:has-text("Submit")')
TIMEOUT_MS = int(os.getenv("SUBMIT_TIMEOUT_SECONDS", "120")) * 1000

OUT_DIR = HERE / "logs" / "inspect"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def dump(page, label: str) -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    png = OUT_DIR / f"{stamp}_{label}.png"
    html = OUT_DIR / f"{stamp}_{label}.html"
    page.screenshot(path=str(png), full_page=True)
    html.write_text(page.content(), encoding="utf-8")
    print(f"  screenshot: {png}")
    print(f"  dom:        {html}")


def list_candidates(page) -> None:
    print("\n-- file inputs --")
    for handle in page.query_selector_all("input[type=file]"):
        print(f"  {handle.evaluate('e => e.outerHTML')}")
    print("\n-- buttons --")
    for handle in page.query_selector_all("button, input[type=submit]"):
        text = (handle.inner_text() or handle.get_attribute("value") or "").strip()
        print(f"  [{text!r}] {handle.evaluate('e => e.outerHTML')[:200]}")


def main() -> int:
    do_submit = "--submit" in sys.argv
    if do_submit and not ATTACHMENT.exists():
        print(f"ERROR: attachment not found at {ATTACHMENT}")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        print(f"navigating to {URL}")
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=30_000)

        print("\n=== BEFORE SUBMIT ===")
        list_candidates(page)
        dump(page, "before")

        if do_submit:
            print(f"\nuploading {ATTACHMENT} via selector {FILE_INPUT!r}")
            page.set_input_files(FILE_INPUT, str(ATTACHMENT))
            print(f"clicking {SUBMIT_BTN!r}")
            page.click(SUBMIT_BTN)
            print(f"waiting up to {TIMEOUT_MS // 1000}s for grading to settle...")
            try:
                page.wait_for_load_state("networkidle", timeout=TIMEOUT_MS)
            except Exception as e:
                print(f"  (networkidle wait ended: {e})")
            print("\n=== AFTER SUBMIT ===")
            print(f"current URL: {page.url}")
            print(f"page text (first 2000 chars):\n{page.inner_text('body')[:2000]}")
            dump(page, "after")

        print("\nBrowser stays open 30s so you can inspect manually.")
        page.wait_for_timeout(30_000)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

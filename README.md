# markwork-health-check

Daily synthetic submission test for [markwork.com](https://www.markwork.com/submit).
Generates a small unique essay, walks the 3-step submit form via Playwright,
waits for the `/results/<uuid>` page, and confirms a grade rendered.

## How it runs

| Path | Trigger | Notification |
|---|---|---|
| **Cloud (primary)** | claude.ai scheduled trigger, 08:00 UTC daily | Trigger prompt posts to Google Chat space `spaces/AAQAEKYlR3E` via google-workspace MCP on non-zero exit |
| **Local (manual)** | `run_markwork_test.bat` (Windows) | `chat_client.py` posts via OAuth `token.json` |

## Files

| File | Purpose |
|---|---|
| `markwork_submit_test.py` | Playwright script. Stdout last line is JSON: `{ok, submission, results_url, grade, ...}` |
| `cloud_run.sh` | Bootstraps a fresh cloud sandbox (pip install, playwright install) and runs the test |
| `chat_client.py` | Local-only Google Chat sender (uses `token.json` from `auth_setup.py`) |
| `auth_setup.py` | One-time OAuth consent for local Chat alerts |
| `send_morning.py` | Unrelated daily good-morning Chat post (separate task in same env) |
| `run_morning.bat` / `run_markwork_test.bat` | Windows Task Scheduler entry points |
| `setup.bat` | Local venv + dependency installer |

## Cloud schedule

Cron: `0 8 * * *` (08:00 UTC = 09:00 BST / 08:00 GMT — see DST note below).

The trigger's prompt:
1. Clones this repo
2. Runs `bash cloud_run.sh`
3. Reads the last stdout line as JSON
4. If `ok: false`, posts a structured failure to Google Chat

### DST note

Cron is fixed in UTC. UK clocks shift in late March / late October.
- Mar–Oct (BST, UTC+1): trigger fires at 09:00 local
- Oct–Mar (GMT, UTC+0): trigger fires at 08:00 local

If 1-hour drift twice a year matters, switch to two triggers (one per season).

## Output contract

Last stdout line is a single-line JSON object:

```json
{"ok": true, "submission": "healthcheck-20260427_172000Z",
 "results_url": "https://www.markwork.com/results/...",
 "grade": "75-85% (Distinction)", "extracted_at": "2026-04-27T17:21:08+00:00"}
```

On failure:

```json
{"ok": false, "submission": "...", "url_at_failure": "...",
 "error_type": "TimeoutError", "error_message": "...",
 "is_timeout": true, "screenshot": "artifacts/failure_...png",
 "html": "artifacts/failure_...html", "traceback": "..."}
```

## Local quickstart

```bat
setup.bat
copy .env.example .env
python markwork_submit_test.py
```

#!/usr/bin/env bash
# Bootstrap + run for a fresh cloud sandbox (claude.ai scheduled trigger).
# Exits 0 on success and prints the JSON result on the last line of stdout.
# Exits non-zero on failure with the JSON failure record on the last line.
set -uo pipefail

cd "$(dirname "$0")"

echo "[$(date -u +%FT%TZ)] installing python deps..."
pip install --quiet --disable-pip-version-check playwright >/dev/null

echo "[$(date -u +%FT%TZ)] installing chromium..."
python -m playwright install --with-deps chromium >/dev/null 2>&1 \
    || python -m playwright install chromium >/dev/null

echo "[$(date -u +%FT%TZ)] running submission test..."
python markwork_submit_test.py
exit_code=$?
echo "[$(date -u +%FT%TZ)] script exited with $exit_code"
exit $exit_code

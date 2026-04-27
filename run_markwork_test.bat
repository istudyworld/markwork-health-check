@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
call .venv\Scripts\activate.bat
python markwork_submit_test.py >> logs\markwork_test_runner.log 2>&1

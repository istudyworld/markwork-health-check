@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
call .venv\Scripts\activate.bat
python send_morning.py >> logs\morning.log 2>&1

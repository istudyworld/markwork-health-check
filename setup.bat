@echo off
cd /d "%~dp0"
set PY="C:\Users\josep\AppData\Local\Python\bin\python.exe"
if not exist %PY% set PY=python
%PY% -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
echo.
echo Setup complete.
echo Next: place credentials.json in this folder, then run: python auth_setup.py
echo Then: copy .env.example to .env and place test_submission.pdf in this folder.

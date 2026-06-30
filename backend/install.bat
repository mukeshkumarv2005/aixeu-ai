@echo off
cd /d C:\Users\HP\aevix\backend
uv venv .venv || echo "venv exists"
call .venv\Scripts\activate.bat
uv pip install -e ".[dev]"
echo "Done: %ERRORLEVEL%"

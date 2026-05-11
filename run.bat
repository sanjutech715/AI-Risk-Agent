@echo off
REM Risk Agent API Launcher for Windows

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Starting Risk Agent API...
python run.py

pause
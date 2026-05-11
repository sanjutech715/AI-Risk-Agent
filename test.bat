@echo off
REM Risk Agent API Test Runner for Windows

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Running tests...
python -m pytest tests/ -v

pause
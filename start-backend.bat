@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0

echo Starting CyberSentinel AI backend...
echo.

uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

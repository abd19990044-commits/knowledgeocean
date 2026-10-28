@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Knowledge Ocean Desktop Launcher
cd /d "%~dp0"

set "IS_LOCAL=1"
set "LOCAL_INSTANCE=1"
set "NO_BROWSER=1"

:: Locate Python
set "PY_CMD="
python --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=python"

if not defined PY_CMD (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)

if not defined PY_CMD (
    if exist "%~dp0venv\Scripts\python.exe" set "PY_CMD=%~dp0venv\Scripts\python.exe"
)

if not defined PY_CMD (
    echo [X] Python was not found. Please run run_local.bat first to set up Python, or use KnowledgeOcean_Setup.exe.
    pause
    exit /b 1
)

:: Launch desktop window
start "" %PY_CMD% "%~dp0desktop_app.py"
exit /b 0

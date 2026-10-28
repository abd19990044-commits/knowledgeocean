@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Knowledge Ocean - Advanced Academic Literature Explorer
color 0B

cd /d "%~dp0"

set "LOCAL_INSTANCE=1"
set "IS_LOCAL=1"

echo ===============================================================================
echo                Knowledge Ocean - Advanced Academic Literature Explorer
echo                          Developed by ABDULSALAM S. HASAN
echo ===============================================================================
echo.

:: 1. Detect Python
echo [*] Checking Python installation...
set "PY_CMD="

python --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=python"

if not defined PY_CMD (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)

if not defined PY_CMD (
    py --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py"
)

if defined PY_CMD (
    for /f "tokens=*" %%i in ('%PY_CMD% --version 2^>^&1') do (
        echo [+] Python detected: %%i
    )
    goto :PYTHON_OK
)

echo [!] Python was not detected on your system PATH.
echo [*] Attempting automated installation via Windows Package Manager...
winget --version >nul 2>&1
if errorlevel 1 goto :NO_WINGET

echo [*] Installing Python 3.11...
winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    echo [+] Python installed successfully.
    goto :PYTHON_OK
)

:NO_WINGET
echo.
echo [X] Could not find Python or winget.
echo Please install Python 3.10+ from https://www.python.org/downloads/
echo Make sure to check "Add python.exe to PATH" during installation.
echo.
pause
exit /b 1

:PYTHON_OK
echo.

:: 2. Check if global Python already has dependencies
echo [*] Checking required libraries...
set "RUNNER=%PY_CMD%"
%RUNNER% -c "import fastapi, uvicorn, requests, fpdf, arabic_reshaper, bidi" >nul 2>&1
if not errorlevel 1 (
    echo [+] All required libraries are already installed and ready.
    goto :CONFIG_CHECK
)

:: 3. Setup Virtual Environment (if needed)
set "VENV_DIR=%~dp0venv"
set "VENV_PY=%~dp0venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [*] Creating virtual environment...
    %PY_CMD% -m venv --system-site-packages "%VENV_DIR%"
    if errorlevel 1 (
        echo [!] Could not create venv. Falling back to global Python...
        set "RUNNER=%PY_CMD%"
    ) else (
        echo [+] Virtual environment created.
        set "RUNNER=%VENV_PY%"
    )
) else (
    echo [+] Virtual environment found.
    set "RUNNER=%VENV_PY%"
)

:: Check dependencies in environment
"%RUNNER%" -c "import fastapi, uvicorn, requests, fpdf, arabic_reshaper, bidi" >nul 2>&1
if not errorlevel 1 (
    echo [+] Dependencies verified in environment.
    goto :CONFIG_CHECK
)

:: Install requirements
echo [*] Installing dependencies from requirements.txt...
set "REQ_MARKER=%~dp0venv\.requirements_installed.txt"
"%RUNNER%" -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo [!] Warning: Some packages had installation issues. Continuing startup...
) else (
    copy /y "%~dp0requirements.txt" "%REQ_MARKER%" >nul 2>&1
    echo [+] Dependencies installed successfully.
)

:CONFIG_CHECK
echo.

:: 4. Ensure config.txt exists
if not exist "%~dp0config.txt" (
    echo [*] Creating default config.txt file...
    (
        echo # Knowledge Ocean Local Configuration
        echo APP_PASSWORD = 123
        echo UNPAYWALL_EMAIL = contact@example.com
        echo ELSEVIER_API_KEY =
    ) > "%~dp0config.txt"
)

:: 4.5. Free port 7860 from ghost processes
echo [*] Freeing port 7860 from any ghost or orphaned processes...
"%RUNNER%" -c "from config_loader import kill_port_occupants; kill_port_occupants(7860)"

:: 5. Display banner
cls
echo ===============================================================================
echo                Knowledge Ocean - Advanced Academic Literature Explorer
echo                          Developed by ABDULSALAM S. HASAN
echo ===============================================================================
echo.
echo   [OK] Server is starting on your local machine!
echo.
echo   =======================================================================
echo     Local URL    : http://localhost:7860/
echo     Access Mode  : Full Open Access (No passcode required / Open)
echo   =======================================================================
echo.
echo   Opening your browser automatically in 2 seconds...
echo   (Press Ctrl+C in this terminal window anytime to stop the server)
echo.
echo ===============================================================================

:: 6. Start Uvicorn Server (opens browser automatically and cleanly once server is ready)
"%RUNNER%" -m uvicorn app:app --host 0.0.0.0 --port 7860

if errorlevel 1 (
    echo.
    echo [X] Server stopped unexpectedly with code %errorlevel%.
    echo Check the error messages above for details.
    echo.
    pause
)
pause

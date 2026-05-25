@echo off
TITLE HCP CRM — One Click Launcher
color 0A
cls

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║        HCP CRM — AI-First Healthcare CRM                ║
echo  ║        Django + LangGraph + Groq  ^|  React + Vite       ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: ── Set base directory to where this bat file lives ──────────────────────────
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

:: ════════════════════════════════════════════════════════════
::  STEP 1 — Check .env file exists
:: ════════════════════════════════════════════════════════════
echo  [1/5] Checking .env file...
IF NOT EXIST "%BACKEND%\.env" (
    echo.
    echo  [ERROR] backend\.env file not found!
    echo  Please create backend\.env with the following content:
    echo.
    echo    DB_NAME=hcp_crm_db
    echo    DB_USER=postgres
    echo    DB_PASSWORD=your_password
    echo    DB_HOST=localhost
    echo    DB_PORT=5432
    echo    GROQ_API_KEY=your_groq_key
    echo.
    pause
    exit /b 1
)
echo  [OK] .env file found.
echo.

:: ════════════════════════════════════════════════════════════
::  STEP 2 — Check Python venv exists
:: ════════════════════════════════════════════════════════════
echo  [2/5] Checking Python virtual environment...
IF NOT EXIST "%BACKEND%\venv\Scripts\activate.bat" (
    echo.
    echo  [SETUP] No venv found. Creating one now...
    cd /d "%BACKEND%"
    python -m venv venv
    call venv\Scripts\activate.bat
    echo  [SETUP] Installing Python dependencies...
    pip install -r requirements.txt
    echo  [OK] venv created and packages installed.
) ELSE (
    echo  [OK] venv found.
)
echo.

:: ════════════════════════════════════════════════════════════
::  STEP 3 — Check frontend node_modules exists
:: ════════════════════════════════════════════════════════════
echo  [3/5] Checking frontend dependencies...
IF NOT EXIST "%FRONTEND%\node_modules" (
    echo  [SETUP] node_modules not found. Running npm install...
    cd /d "%FRONTEND%"
    npm install
    echo  [OK] Frontend packages installed.
) ELSE (
    echo  [OK] node_modules found.
)
echo.

:: ════════════════════════════════════════════════════════════
::  STEP 4 — Start Backend (Django) in new window
:: ════════════════════════════════════════════════════════════
echo  [4/5] Starting Backend server (Django on port 8000)...
start "HCP CRM — Backend" cmd /k "cd /d "%BACKEND%" && call venv\Scripts\activate.bat && python manage.py migrate --run-syncdb && python manage.py seed_data && echo. && echo  Backend running at http://localhost:8000 && echo. && python manage.py runserver"
echo  [OK] Backend window launched.
echo.

:: ════════════════════════════════════════════════════════════
::  STEP 5 — Start Frontend (Vite) in new window
:: ════════════════════════════════════════════════════════════
echo  [5/5] Starting Frontend server (React + Vite on port 5173)...
start "HCP CRM — Frontend" cmd /k "cd /d "%FRONTEND%" && echo. && echo  Frontend running at http://localhost:5173 && echo. && npm run dev"
echo  [OK] Frontend window launched.
echo.

:: ════════════════════════════════════════════════════════════
::  Wait a few seconds then open browser automatically
:: ════════════════════════════════════════════════════════════
echo  Opening browser in 5 seconds...
ping 127.0.0.1 -n 6 > nul
start "" "http://localhost:5173"

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║  Both servers are running!                              ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║  Frontend (App)  →  http://localhost:5173               ║
echo  ║  Backend  (API)  →  http://localhost:8000/api/          ║
echo  ║  Django Admin    →  http://localhost:8000/admin/        ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo  Close this window anytime. Servers run in their own windows.
echo.
pause

@echo off
TITLE HCP CRM — Django Dev Server

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       HCP CRM — AI-First CRM HCP Module             ║
echo  ║       Powered by Django + LangGraph + Groq           ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: ── Activate virtual environment ─────────────────────────────────────────────
IF EXIST "venv\Scripts\activate.bat" (
    echo [1/5] Activating virtual environment...
    call venv\Scripts\activate.bat
) ELSE (
    echo [!] No venv found. Create one with:
    echo     python -m venv venv ^&^& venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

:: ── Load .env ─────────────────────────────────────────────────────────────────
IF EXIST ".env" (
    echo [2/5] Loading .env variables...
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        if not "%%A"=="" if not "%%A:~0,1%"=="#" set "%%A=%%B"
    )
) ELSE (
    echo [!] .env file not found. Copy .env.example to .env and fill in your values.
    pause
    exit /b 1
)

:: ── Run migrations ────────────────────────────────────────────────────────────
echo [3/5] Running migrations...
python manage.py migrate --run-syncdb

:: ── Seed sample data (skip if HCPs already exist) ────────────────────────────
echo [4/5] Seeding sample HCP data...
python manage.py seed_data

:: ── Start server ──────────────────────────────────────────────────────────────
echo [5/5] Starting Django development server...
echo.
echo  ┌─────────────────────────────────────────────────────┐
echo  │  API Endpoints                                      │
echo  ├─────────────────────────────────────────────────────┤
echo  │  Root / Health   → http://127.0.0.1:8000/          │
echo  │  Admin           → http://127.0.0.1:8000/admin/    │
echo  ├─────────────────────────────────────────────────────┤
echo  │  /api/ (Simplified)                                 │
echo  │    POST  /api/chat/                                 │
echo  │    GET   /api/interactions/                         │
echo  │    GET   /api/interactions/{id}/                    │
echo  │    POST  /api/interactions/{id}/followup/           │
echo  │    GET   /api/hcp/                                  │
echo  │    GET   /api/hcp/search/?name=query                │
echo  ├─────────────────────────────────────────────────────┤
echo  │  /api/v1/ (Full DRF + Agent)                        │
echo  │    POST  /api/v1/agent/                             │
echo  │    POST  /api/v1/agent/detect-intent/               │
echo  │    GET   /api/v1/hcps/                              │
echo  │    GET   /api/v1/interactions/                      │
echo  └─────────────────────────────────────────────────────┘
echo.
python manage.py runserver

pause

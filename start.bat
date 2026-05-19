@echo off
TITLE HCP CRM — Startup Sequence

echo =========================================
echo    HCP CRM - AI-First Healthcare CRM
echo =========================================
echo.

echo Starting Backend (Django)...
:: Navigates to backend, activates venv, and starts the Django server
start cmd /k "cd backend && venv\Scripts\activate && python manage.py runserver"

echo Starting Frontend (Vite + React)...
:: Navigates to frontend and starts the Vite dev server
start cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are launching in separate windows!
echo ------------------------------------------------
echo NOTE: If the backend window crashes, please ensure:
echo 1. You have created the PostgreSQL database "hcp_crm".
echo 2. You have configured backend/.env with your DB password and GROQ_API_KEY.
echo.
pause

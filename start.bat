@echo off
REM WhoVoted Quick Start Script for Windows

echo === WhoVoted Modernization Quick Start ===
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    exit /b 1
)

REM Create directories
echo Creating directories...
if not exist "data" mkdir data
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "public\data" mkdir public\data

REM Initialize geocoding cache
echo Initializing geocoding cache...
echo {} > data\geocoding_cache.json

REM Check if virtual environment exists
if not exist "backend\venv" (
    echo Creating virtual environment...
    cd backend
    python -m venv venv
    call venv\Scripts\activate
    
    echo Installing dependencies...
    pip install -r requirements.txt
    
    cd ..
) else (
    echo Virtual environment already exists
)

REM Check if .env exists
if not exist "backend\.env" (
    echo Creating .env file...
    copy backend\.env.example backend\.env
    echo WARNING: Please edit backend\.env and set a secure SECRET_KEY
)

echo.
echo === Setup Complete ===
echo.
echo To start the server:
echo   cd backend
echo   venv\Scripts\activate
echo   python app.py
echo.
echo Then visit:
echo   Public Map: http://localhost:5000/
echo   Admin Panel: http://localhost:5000/admin
echo   Login: admin / admin2026!
echo.
pause

@echo off
setlocal enabledelayedexpansion
title Healthcare Credentialing Agent - Launch All VM Services

echo ============================================================
echo  Healthcare Credentialing Agent - VM Local Launcher
echo ============================================================
echo  Starting FastAPI Web Workbench (Port 8000)...
start "FastAPI Web Workbench (VM)" cmd /c "%~dp0vm_start_api.bat"

echo  Starting Streamlit Committee Portal (Port 8501)...
start "Streamlit Committee Portal (VM)" cmd /c "%~dp0vm_start_ui.bat"

echo.
echo [*] Waiting 3 seconds for services to initialize...
timeout /t 3 /nobreak >nul

echo [*] Opening Host Browser...
start http://localhost:8000/ui
start http://localhost:8501

echo.
echo ============================================================
echo  Both services are running in background VM windows!
echo   - Web Workbench:    http://localhost:8000/ui
echo   - Streamlit Portal: http://localhost:8501
echo   - Swagger API Docs: http://localhost:8000/docs
echo ============================================================
pause

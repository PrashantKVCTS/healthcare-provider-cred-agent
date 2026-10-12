@echo off
setlocal enabledelayedexpansion
title Healthcare Credentialing Agent - FastAPI Web Workbench

echo ============================================================
echo  Starting FastAPI Web Workbench / Appian API (VM Local)
echo ============================================================

set HOST=0.0.0.0
set PORT=8000

:: Detect Python in virtual environment or system
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [*] Using local virtual environment (.venv)
) else (
    set "PYTHON_EXE=python"
    echo [*] Using system Python
)

echo [*] Binding to %HOST%:%PORT% (Accessible from Host and Local VM)
echo [*] Web Workbench URL: http://localhost:%PORT%/ui
echo [*] Swagger API Docs:  http://localhost:%PORT%/docs
echo ============================================================
echo.

%PYTHON_EXE% api/appian_api.py
pause

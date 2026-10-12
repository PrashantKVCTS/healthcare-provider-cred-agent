@echo off
setlocal enabledelayedexpansion
title Healthcare Credentialing Agent - Streamlit Committee Portal

echo ============================================================
echo  Starting Streamlit Operations Portal (VM Local)
echo ============================================================

set HOST=0.0.0.0
set UI_PORT=8501

:: Detect Streamlit in virtual environment or system
if exist ".venv\Scripts\streamlit.exe" (
    set "STREAMLIT_EXE=.venv\Scripts\streamlit.exe"
    echo [*] Using local virtual environment (.venv)
) else (
    set "STREAMLIT_EXE=streamlit"
    echo [*] Using system Streamlit
)

echo [*] Binding to %HOST%:%UI_PORT% (Accessible from Host and Local VM)
echo [*] Streamlit Portal URL: http://localhost:%UI_PORT%
echo ============================================================
echo.

%STREAMLIT_EXE% run ui/app.py --server.port %UI_PORT% --server.address %HOST% --server.headless true
pause

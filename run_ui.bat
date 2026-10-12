@echo off
title Healthcare Provider Credentialing Operations Portal (UI)
echo ===============================================================================
echo  HEALTHCARE PROVIDER CREDENTIALING APPROVAL AGENT - OPERATIONS PORTAL
echo  Standalone Web UI Workflow (Streamlit)
echo ===============================================================================
echo.

cd /d "%~dp0"

where streamlit >nul 2>nul
if %errorlevel% neq 0 (
    echo [*] Streamlit not found in system PATH. Attempting python -m streamlit ...
    python -m streamlit run ui/app.py
) else (
    echo [*] Starting Streamlit Operations Portal...
    streamlit run ui/app.py
)

pause


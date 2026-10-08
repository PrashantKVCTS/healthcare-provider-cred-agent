@echo off
echo ============================================================
echo  Healthcare Provider Credentialing Approval Agentic System 
echo  Local Setup ^& Test Suite Execution Script
echo ============================================================

echo.
echo [1/4] Checking Python environment...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing project dependencies from requirements.txt...
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Error installing dependencies.
    pause
    exit /b 1
)

echo.
echo [3/4] Running automated test suite (pytest)...
python -m pytest tests/test_cred_agent.py -v
if %ERRORLEVEL% NEQ 0 (
    echo Tests failed!
    pause
    exit /b 1
)

echo.
echo [4/4] Executing sample CLI batch roster processing...
python run_agent.py --roster data/sample_provider_roster.csv

echo.
echo ============================================================
echo  Setup ^& Verification Complete!
echo ============================================================
echo To run in VS Code:
echo   1. Start Appian REST API: python api/appian_api.py
echo   2. Start Streamlit UI:    streamlit run ui/app.py
echo   3. Swagger API Docs:      http://localhost:8000/docs
echo   4. Appian OpenAPI JSON:   http://localhost:8000/api/v1/appian/openapi.json
echo ============================================================
pause

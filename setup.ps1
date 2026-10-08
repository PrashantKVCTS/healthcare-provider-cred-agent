Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Healthcare Provider Credentialing Approval Agentic System " -ForegroundColor Cyan
Write-Host " Local Setup & Test Suite Execution Script                 " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Check Python installation
Write-Host "`n[1/4] Checking Python environment..." -ForegroundColor Yellow
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python is not installed or not in PATH." -ForegroundColor Red
    exit 1
}

# Install or upgrade dependencies
Write-Host "`n[2/4] Installing project dependencies from requirements.txt..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error installing dependencies." -ForegroundColor Red
    exit 1
}

# Run pytest automated test suite
Write-Host "`n[3/4] Running automated test suite (pytest)..." -ForegroundColor Yellow
python -m pytest tests/test_cred_agent.py -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed!" -ForegroundColor Red
    exit 1
}

# Run sample CLI batch test
Write-Host "`n[4/4] Executing sample CLI batch roster processing..." -ForegroundColor Yellow
python run_agent.py --roster data/sample_provider_roster.csv

Write-Host "`n============================================================" -ForegroundColor Green
Write-Host " Setup & Verification Complete! " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host "To run in VS Code:" -ForegroundColor White
Write-Host "  1. Start Appian REST API: python api/appian_api.py (or press F5 in VS Code)" -ForegroundColor Cyan
Write-Host "  2. Start Streamlit UI:    streamlit run ui/app.py (or press F5 in VS Code)" -ForegroundColor Cyan
Write-Host "  3. Swagger API Docs:      http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  4. Appian OpenAPI JSON:   http://localhost:8000/api/v1/appian/openapi.json" -ForegroundColor Cyan

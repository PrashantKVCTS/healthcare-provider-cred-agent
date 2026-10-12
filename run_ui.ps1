# Healthcare Provider Credentialing Agent - Standalone UI Launcher
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host " HEALTHCARE PROVIDER CREDENTIALING APPROVAL AGENT - OPERATIONS PORTAL" -ForegroundColor White
Write-Host " Standalone Web UI Workflow (Streamlit)" -ForegroundColor Green
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check if .venv exists and activate if present
if (Test-Path "$ScriptDir\.venv\Scripts\Activate.ps1") {
    Write-Host "[*] Activating local virtual environment (.venv)..." -ForegroundColor Yellow
    & "$ScriptDir\.venv\Scripts\Activate.ps1"
}

Write-Host "[*] Launching Streamlit Operations & Committee Portal..." -ForegroundColor Green
Write-Host "[*] URL: http://localhost:8501" -ForegroundColor Cyan
python -m streamlit run ui/app.py


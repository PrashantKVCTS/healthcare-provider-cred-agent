<#
.SYNOPSIS
    Automated Local VM Creator and Provisioner for Healthcare Provider Credentialing Agent.
.DESCRIPTION
    Creates and configures local virtual environments and virtual machines (Python venv, WSL2, Hyper-V, Vagrant, Docker).
.PARAMETER Mode
    Deployment mode: 'venv' (default), 'wsl', 'hyperv', 'vagrant', 'docker', 'test', 'start'.
#>

param(
    [ValidateSet("venv", "wsl", "hyperv", "vagrant", "docker", "test", "start", "menu")]
    [string]$Mode = "menu"
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Header {
    Clear-Host
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host "  Healthcare Provider Credentialing Approval Agentic Workflow" -ForegroundColor Cyan
    Write-Host "  Automated Local Virtual Machine (VM) Creator & Provisioner" -ForegroundColor Cyan
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Invoke-VenvSetup {
    Show-Header
    Write-Host "[1/5] Checking Python runtime..." -ForegroundColor Green
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Host "[ERROR] Python 3.10+ not found in PATH." -ForegroundColor Red
        return
    }

    $venvDir = Join-Path $ProjectDir ".venv"
    if (-not (Test-Path $venvDir)) {
        Write-Host "[2/5] Creating isolated virtual machine sandbox (.venv)..." -ForegroundColor Green
        python -m venv $venvDir
    } else {
        Write-Host "[2/5] Existing .venv virtual environment detected." -ForegroundColor Green
    }

    $pyExe = Join-Path $venvDir "Scripts\python.exe"
    Write-Host "[3/5] Upgrading pip and core dependencies..." -ForegroundColor Green
    & $pyExe -m pip install --upgrade pip setuptools wheel

    Write-Host "[4/5] Installing project requirements from requirements.txt..." -ForegroundColor Green
    & $pyExe -m pip install -r (Join-Path $ProjectDir "requirements.txt")

    Write-Host "[5/5] Running verification test suite inside VM..." -ForegroundColor Green
    & $pyExe -m pytest (Join-Path $ProjectDir "tests\test_cred_agent.py") -v

    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host "  Local Virtual Environment VM successfully configured!" -ForegroundColor Green
    Write-Host "  Endpoints:" -ForegroundColor Cyan
    Write-Host "    - Web Operations Workbench: http://localhost:8000/ui" -ForegroundColor White
    Write-Host "    - Streamlit Committee:      http://localhost:8501" -ForegroundColor White
    Write-Host "    - Swagger API Docs:         http://localhost:8000/docs" -ForegroundColor White
    Write-Host "==============================================================================" -ForegroundColor Cyan
}

function Invoke-Tests {
    Show-Header
    Write-Host "[*] Executing test suite inside VM..." -ForegroundColor Green
    $venvPy = Join-Path $ProjectDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        & $venvPy -m pytest (Join-Path $ProjectDir "tests\test_cred_agent.py") -v
    } else {
        python -m pytest (Join-Path $ProjectDir "tests\test_cred_agent.py") -v
    }
}

function Invoke-StartAll {
    Show-Header
    Write-Host "[*] Launching all VM services..." -ForegroundColor Green
    $batch = Join-Path $ProjectDir "vm_run_all.bat"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$batch`""
}

# Main routing
switch ($Mode) {
    "venv"    { Invoke-VenvSetup }
    "test"    { Invoke-Tests }
    "start"   { Invoke-StartAll }
    "hyperv"  { & (Join-Path $ProjectDir "scripts\provision_hyperv.ps1") }
    "wsl"     { wsl bash (Join-Path $ProjectDir "scripts\provision_wsl.sh") }
    "vagrant" { vagrant up }
    "docker"  { docker-compose up --build -d }
    "menu"    {
        Show-Header
        Write-Host "  [1] Local Python Virtual Machine Sandbox (.venv)  [Recommended / Instant]" -ForegroundColor Yellow
        Write-Host "  [2] WSL2 Linux Virtual Machine" -ForegroundColor White
        Write-Host "  [3] Windows Hyper-V Virtual Machine" -ForegroundColor White
        Write-Host "  [4] Vagrant / VirtualBox Linux VM" -ForegroundColor White
        Write-Host "  [5] Docker Container VM" -ForegroundColor White
        Write-Host "  [6] Run Automated Pytest Suite inside VM" -ForegroundColor White
        Write-Host "  [7] Launch All VM Services (Web Workbench + Streamlit UI)" -ForegroundColor White
        Write-Host "  [0] Exit" -ForegroundColor Gray
        Write-Host ""
        $choice = Read-Host "Select option [1-7, 0 to exit] (Default: 1)"
        if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }
        switch ($choice) {
            "1" { Invoke-VenvSetup }
            "2" { wsl bash (Join-Path $ProjectDir "scripts\provision_wsl.sh") }
            "3" { & (Join-Path $ProjectDir "scripts\provision_hyperv.ps1") }
            "4" { vagrant up }
            "5" { docker-compose up --build -d }
            "6" { Invoke-Tests }
            "7" { Invoke-StartAll }
            default { exit }
        }
    }
}

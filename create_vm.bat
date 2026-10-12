@echo off
setlocal enabledelayedexpansion
title Healthcare Credentialing Agent - Local VM Creator ^& Provisioner

:: ==============================================================================
:: Healthcare Provider Credentialing Approval Agentic Workflow
:: Automated Local Virtual Machine (VM) Creator & Environment Provisioner
:: ==============================================================================

cd /d "%~dp0"

:: Check for CLI arguments
set "NON_INTERACTIVE=0"
if "%1"=="--venv" set "NON_INTERACTIVE=1" & goto CREATE_VENV
if "%1"=="--hyperv" set "NON_INTERACTIVE=1" & goto PROVISION_HYPERV
if "%1"=="--wsl" set "NON_INTERACTIVE=1" & goto PROVISION_WSL
if "%1"=="--vagrant" set "NON_INTERACTIVE=1" & goto PROVISION_VAGRANT
if "%1"=="--test" set "NON_INTERACTIVE=1" & goto RUN_TESTS
if "%1"=="--start" set "NON_INTERACTIVE=1" & goto START_SERVICES
if "%1"=="--help" goto USAGE

:MENU
cls
echo ==============================================================================
echo   Healthcare Provider Credentialing Approval Agentic Workflow
echo   Automated Local Virtual Machine (VM) Creator ^& Provisioner
echo ==============================================================================
echo.
echo   Detected Virtualization ^& Runtime Options on this Host:
echo.

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('python --version') do set "DETECTED_PY=%%i"
    echo     [x] Python Runtime:          !DETECTED_PY! (Installed)
) else (
    echo     [ ] Python Runtime:          Not found in PATH
)

:: Check WSL
wsl --status >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo     [x] WSL2 Linux Subsystem:    Available
) else (
    echo     [ ] WSL2 Linux Subsystem:    Not installed (Run 'wsl --install')
)

:: Check Vagrant
vagrant --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('vagrant --version') do set "DETECTED_VAG=%%i"
    echo     [x] Vagrant Virtual Machine: !DETECTED_VAG!
) else (
    echo     [ ] Vagrant Virtual Machine: Not found in PATH
)

:: Check Docker
docker --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=*" %%i in ('docker --version') do set "DETECTED_DOC=%%i"
    echo     [x] Docker Container VM:     !DETECTED_DOC!
) else (
    echo     [ ] Docker Container VM:     Not found in PATH
)

echo.
echo ==============================================================================
echo   Please select a Virtual Machine deployment option:
echo ==============================================================================
echo   [1] Local Python Virtual Machine Sandbox (.venv)  [Recommended / Instant]
echo   [2] WSL2 Linux Virtual Machine                    [Native Linux on Windows]
echo   [3] Windows Hyper-V Virtual Machine               [Native Windows Hypervisor]
echo   [4] Vagrant / VirtualBox Linux VM                 [Ubuntu 22.04 LTS Headless]
echo   [5] Docker Containerized VM Environment           [Multi-Stage Containers]
echo   [6] Run Automated Pytest Suite inside VM
echo   [7] Launch All VM Services (Web Workbench + Streamlit Portal)
echo   [0] Exit
echo ==============================================================================
set /p "CHOICE=Enter choice [1-7, or 0 to exit] (Default: 1): "

if "%CHOICE%"=="" set CHOICE=1
if "%CHOICE%"=="1" goto CREATE_VENV
if "%CHOICE%"=="2" goto PROVISION_WSL
if "%CHOICE%"=="3" goto PROVISION_HYPERV
if "%CHOICE%"=="4" goto PROVISION_VAGRANT
if "%CHOICE%"=="5" goto PROVISION_DOCKER
if "%CHOICE%"=="6" goto RUN_TESTS
if "%CHOICE%"=="7" goto START_SERVICES
if "%CHOICE%"=="0" exit /b 0

echo Invalid choice. Please try again.
pause
goto MENU


:: ==============================================================================
:: OPTION 1: Local Virtual Environment VM Sandbox (.venv)
:: ==============================================================================
:CREATE_VENV
cls
echo ==============================================================================
echo  [1/5] Creating Local Python Virtual Machine Sandbox (.venv)...
echo ==============================================================================
echo.

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3 is not installed or not in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    goto MENU
)

if not exist ".venv" (
    echo [*] Initializing virtual environment in .venv ...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        goto MENU
    )
    echo [+] Virtual environment created successfully.
) else (
    echo [+] Existing .venv directory found. Re-verifying environment...
)

echo.
echo ==============================================================================
echo  [2/5] Upgrading pip and core build tools...
echo ==============================================================================
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

echo.
echo ==============================================================================
echo  [3/5] Installing dependencies from requirements.txt...
echo ==============================================================================
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install requirements.
    pause
    goto MENU
)

echo.
echo ==============================================================================
echo  [4/5] Running verification test suite inside VM environment...
echo ==============================================================================
.venv\Scripts\python.exe -m pytest tests/test_cred_agent.py -v
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Some tests did not pass. Review output above.
) else (
    echo [+] All 14 tests PASSED cleanly inside local VM environment!
)

echo.
echo ==============================================================================
echo  [5/5] Configuring Host Networking ^& Service Endpoints...
echo ==============================================================================
set HOST=0.0.0.0
set PORT=8000
set UI_PORT=8501

echo [*] Host network binding configured:
echo     - API / Web Operations Workbench: http://localhost:8000/ui
echo     - Streamlit Committee Portal:    http://localhost:8501
echo     - OpenAPI / Appian Connected:    http://localhost:8000/api/v1/appian/openapi.json
echo.
echo [+] Local Virtual Environment VM is fully configured and ready!
echo.
if "%NON_INTERACTIVE%"=="1" exit /b 0

set /p "START_NOW=Do you want to launch all services now? (Y/N, Default: Y): "
if /i "%START_NOW%"=="N" goto FINISH_VENV

call "%~dp0vm_run_all.bat"
goto FINISH_VENV

:FINISH_VENV
if "%NON_INTERACTIVE%"=="1" exit /b 0
echo.
echo Press any key to return to main menu...
pause >nul
goto MENU


:: ==============================================================================
:: OPTION 2: WSL2 Linux Virtual Machine
:: ==============================================================================
:PROVISION_WSL
cls
echo ==============================================================================
echo  WSL2 Linux Virtual Machine Setup
echo ==============================================================================
echo.
wsl --status >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Windows Subsystem for Linux (WSL) is not yet installed on this PC.
    echo.
    echo To install WSL2 with default Ubuntu Linux, run:
    echo     wsl --install
    echo.
    set /p "INSTALL_WSL=Do you want to attempt installing WSL now? (Y/N): "
    if /i "!INSTALL_WSL!"=="Y" (
        echo [*] Running 'wsl --install'... (Administrator privilege may be required)
        wsl --install
        echo [!] Please reboot your computer after WSL installation completes.
    )
    pause
    goto MENU
)

echo [*] WSL2 is detected. Executing Linux provisioning inside WSL...
wsl bash "%~dp0scripts/provision_wsl.sh"
pause
goto MENU


:: ==============================================================================
:: OPTION 3: Hyper-V Virtual Machine
:: ==============================================================================
:PROVISION_HYPERV
cls
echo ==============================================================================
echo  Windows Hyper-V Virtual Machine Provisioning
echo ==============================================================================
echo.
echo [*] Launching PowerShell Hyper-V Provisioner with Administrator elevation...
powershell.exe -ExecutionPolicy Bypass -File "%~dp0scripts\provision_hyperv.ps1"
pause
goto MENU


:: ==============================================================================
:: OPTION 4: Vagrant / VirtualBox Linux VM
:: ==============================================================================
:PROVISION_VAGRANT
cls
echo ==============================================================================
echo  Vagrant / VirtualBox Linux Virtual Machine Provisioning
echo ==============================================================================
echo.
vagrant --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Vagrant is not installed or not in PATH.
    echo Please install Vagrant from https://www.vagrantup.com/
    echo and VirtualBox from https://www.virtualbox.org/
    pause
    goto MENU
)

echo [*] Initializing and launching Vagrant VM (Ubuntu 22.04 LTS)...
echo [*] Ports 8000 and 8501 will be forwarded to your host browser.
vagrant up
echo.
echo [*] Checking VM status...
vagrant status
echo.
echo Access your VM services on host:
echo   - FastAPI Web Workbench: http://localhost:8000/ui
echo   - Streamlit Portal:      http://localhost:8501
pause
goto MENU


:: ==============================================================================
:: OPTION 5: Docker Container VM
:: ==============================================================================
:PROVISION_DOCKER
cls
echo ==============================================================================
echo  Docker Container Virtual Machine Environment
echo ==============================================================================
echo.
docker --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [!] Docker is not installed or Docker Desktop is not running.
    echo Please start Docker Desktop or install it from https://www.docker.com/
    pause
    goto MENU
)

echo [*] Building and launching containers via docker-compose...
docker-compose up --build -d
echo.
echo [*] Checking container status...
docker-compose ps
echo.
echo [+] Containers are active!
echo     - Web Workbench:    http://localhost:8000/ui
echo     - Streamlit Portal: http://localhost:8501
pause
goto MENU


:: ==============================================================================
:: OPTION 6: Run Pytest Tests in VM
:: ==============================================================================
:RUN_TESTS
cls
echo ==============================================================================
echo  Executing Automated Test Suite inside VM Environment
echo ==============================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
    echo [*] Running via .venv virtual environment...
) else (
    set "PY_CMD=python"
    echo [*] Running via system Python...
)

%PY_CMD% -m pytest tests/test_cred_agent.py -v
set "TEST_EXIT_CODE=%ERRORLEVEL%"
if "%NON_INTERACTIVE%"=="1" exit /b !TEST_EXIT_CODE!
echo.
pause
goto MENU


:: ==============================================================================
:: OPTION 7: Launch All VM Services
:: ==============================================================================
:START_SERVICES
cls
call "%~dp0vm_run_all.bat"
if "%NON_INTERACTIVE%"=="1" exit /b 0
goto MENU


:USAGE
echo.
echo Usage: create_vm.bat [OPTION]
echo.
echo Options:
echo   --venv       Create and provision local Python virtual environment sandbox (.venv)
echo   --hyperv     Provision Hyper-V VM with internal NAT switch and port mapping
echo   --wsl        Provision and run inside WSL2 Linux VM
echo   --vagrant    Provision Ubuntu VM via Vagrant / VirtualBox
echo   --test       Run automated verification tests
echo   --start      Launch all VM services (Web Workbench + Streamlit Portal)
echo   --help       Show this help message
echo.
exit /b 0

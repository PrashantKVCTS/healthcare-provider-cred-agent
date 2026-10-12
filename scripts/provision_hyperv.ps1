<#
.SYNOPSIS
    Automated Hyper-V Virtual Machine Provisioning for Healthcare Credentialing Agent.
.DESCRIPTION
    Creates an isolated Hyper-V VM with internal NAT switch and port mapping for:
    - FastAPI Web Workbench / Appian API (Port 8000)
    - Streamlit Committee & Operations Portal (Port 8501)
#>

param(
    [string]$VmName = "Healthcare-Cred-Agent-VM",
    [int64]$MemoryBytes = 2GB,
    [int]$CpuCount = 2,
    [string]$SwitchName = "CredAgentNatSwitch",
    [string]$NatSubnet = "192.168.120.0/24",
    [string]$NatGateway = "192.168.120.1",
    [string]$VmIpAddress = "192.168.120.10"
)

# 1. Require Administrator Privileges
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[!] Administrator privileges are required to configure Hyper-V virtual switches and VMs." -ForegroundColor Yellow
    Write-Host "[*] Relaunching PowerShell as Administrator..." -ForegroundColor Cyan
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoExit -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Hyper-V VM Provisioning for Credentialing Agent         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 2. Check Hyper-V feature
$hyperv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -ErrorAction SilentlyContinue
if ($null -eq $hyperv -or $hyperv.State -ne "Enabled") {
    Write-Host "[!] Hyper-V is not currently enabled on this machine." -ForegroundColor Red
    Write-Host "    To enable Hyper-V, run: Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All" -ForegroundColor Yellow
    Write-Host "    Note: Requires reboot." -ForegroundColor Yellow
    exit 1
}

# 3. Create or verify Internal Virtual Switch
$vSwitch = Get-VMSwitch -Name $SwitchName -ErrorAction SilentlyContinue
if (-not $vSwitch) {
    Write-Host "[*] Creating Hyper-V internal virtual switch '$SwitchName'..." -ForegroundColor Green
    $vSwitch = New-VMSwitch -Name $SwitchName -SwitchType Internal
} else {
    Write-Host "[+] Virtual switch '$SwitchName' already exists." -ForegroundColor Green
}

# 4. Configure NAT Gateway if not present
$natNetAdapter = Get-NetAdapter | Where-Object { $_.Name -like "*$SwitchName*" -or $_.InterfaceDescription -like "*$SwitchName*" }
if ($natNetAdapter) {
    $existingIp = Get-NetIPAddress -InterfaceIndex $natNetAdapter.ifIndex -IPAddress $NatGateway -ErrorAction SilentlyContinue
    if (-not $existingIp) {
        Write-Host "[*] Configuring NAT Gateway IP ($NatGateway) on switch adapter..." -ForegroundColor Green
        New-NetIPAddress -InterfaceIndex $natNetAdapter.ifIndex -IPAddress $NatGateway -PrefixLength 24 -ErrorAction SilentlyContinue | Out-Null
    }
}

$existingNat = Get-NetNat -Name "CredAgentNat" -ErrorAction SilentlyContinue
if (-not $existingNat) {
    Write-Host "[*] Configuring NAT Network 'CredAgentNat' on $NatSubnet..." -ForegroundColor Green
    New-NetNat -Name "CredAgentNat" -InternalIPInterfaceAddressPrefix $NatSubnet -ErrorAction SilentlyContinue | Out-Null
}

# 5. Configure Port Forwarding Rules for Web Workbench and Streamlit UI
Write-Host "[*] Configuring NAT Port Forwarding Rules..." -ForegroundColor Green
Get-NetNatStaticMapping -NatName "CredAgentNat" -ErrorAction SilentlyContinue | Where-Object { $_.ExternalPort -in 8000, 8501 } | Remove-NetNatStaticMapping -Confirm:$false -ErrorAction SilentlyContinue

Add-NetNatStaticMapping -NatName "CredAgentNat" -Protocol TCP -ExternalIPAddress "0.0.0.0/0" -ExternalPort 8000 -InternalIPAddress $VmIpAddress -InternalPort 8000 | Out-Null
Add-NetNatStaticMapping -NatName "CredAgentNat" -Protocol TCP -ExternalIPAddress "0.0.0.0/0" -ExternalPort 8501 -InternalIPAddress $VmIpAddress -InternalPort 8501 | Out-Null

Write-Host "    • Port 8000 -> VM Port 8000 (FastAPI Web Workbench)" -ForegroundColor DarkCyan
Write-Host "    • Port 8501 -> VM Port 8501 (Streamlit Operations Portal)" -ForegroundColor DarkCyan

# 6. Check if VM exists or create it
$existingVm = Get-VM -Name $VmName -ErrorAction SilentlyContinue
if (-not $existingVm) {
    Write-Host "[*] Creating Hyper-V VM '$VmName'..." -ForegroundColor Green
    $vmDir = Join-Path $env:PUBLIC "Hyper-V\Virtual Machines\$VmName"
    New-Item -ItemType Directory -Path $vmDir -Force | Out-Null
    
    $vhdPath = Join-Path $vmDir "$VmName.vhdx"
    New-VHD -Path $vhdPath -SizeBytes 30GB -Dynamic | Out-Null

    $vm = New-VM -Name $VmName -MemoryStartupBytes $MemoryBytes -SwitchName $SwitchName -VHDPath $vhdPath -Generation 2
    Set-VMProcessor -VMName $VmName -Count $CpuCount
    Set-VMMemory -VMName $VmName -DynamicMemoryEnabled $true -MinimumBytes 1GB -MaximumBytes 4GB

    Write-Host "[+] VM '$VmName' successfully created!" -ForegroundColor Green
} else {
    Write-Host "[+] VM '$VmName' already exists." -ForegroundColor Green
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Hyper-V Provisioning Complete!                           " -ForegroundColor Cyan
Write-Host " Access from host browser once VM OS is running:          " -ForegroundColor Cyan
Write-Host "   - FastAPI Web Workbench: http://localhost:8000/ui      " -ForegroundColor Green
Write-Host "   - Streamlit Portal:      http://localhost:8501         " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# start_vasbot.ps1
# Unified Startup Script for Personal Use

$ErrorActionPreference = "Stop"

# --- Set Working Directory to Script Location ---
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location -Path $scriptDir

# --- Self-Elevation Check ---
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Restarting with Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -NoExit -Command `"cd '$scriptDir'; & '.\start_vasbot.ps1'`"" -Verb RunAs
    exit
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       VASbot3 - Initializing...          " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check Python Dependencies
Write-Host "`n[1/2] Checking Python Environment..." -ForegroundColor Yellow
Push-Location "python"

try {
    # Check if python is accessible
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green

    Write-Host "Installing/Updating requirements..." -ForegroundColor Yellow
    python -m pip install -r requirements.txt --upgrade | Out-Null
    Write-Host "Python dependencies are up to date." -ForegroundColor Green
} catch {
    Write-Host "ERROR: Failed to set up Python environment. Ensure Python 3 is installed and in PATH." -ForegroundColor Red
    Pop-Location
    pause
    exit 1
}

Pop-Location

# 2. Launch .NET GUI
Write-Host "`n[2/2] Launching VASbot3 Studio..." -ForegroundColor Yellow
Push-Location "VASbot.Gui"

try {
    dotnet run
} catch {
    Write-Host "ERROR: Failed to launch the .NET GUI." -ForegroundColor Red
    pause
}

Pop-Location

Write-Host "`nVASbot3 has closed." -ForegroundColor Cyan
pause

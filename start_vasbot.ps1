# start_vasbot.ps1
# Unified Startup Script for Personal Use

$ErrorActionPreference = "Stop"

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
}

Pop-Location

Write-Host "`nVASbot3 has closed." -ForegroundColor Cyan

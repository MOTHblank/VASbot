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

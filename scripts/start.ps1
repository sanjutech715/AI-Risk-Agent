<#
.SYNOPSIS
Bootstrap the Risk Agent PowerShell environment and start the API.

.DESCRIPTION
This script sets a temporary execution policy for the current PowerShell session,
activates the local .venv, installs required dependencies, and launches the API.

Usage:
  powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
#>

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $repoRoot "..")
$venvPath = Join-Path $root ".venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment at $venvPath..."
    python -m venv $venvPath
}

if (-not (Test-Path $activateScript)) {
    Write-Error "Virtual environment activation script not found at $activateScript."
    Exit 1
}

Write-Host "Activating virtual environment..."
. $activateScript

Write-Host "Installing dependencies..."
pip install --upgrade pip
pip install -r (Join-Path $root "requirements.txt")

Write-Host "Starting Risk Agent API..."
Push-Location $root
python app.py
Pop-Location

# Desktop Assistant - Windows Setup Script
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Desktop Assistant - Setup Start" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Prerequisites Check
Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Yellow

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  ERROR: Python is not found. Please install Python 3.10 - 3.12." -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Gray
    exit 1
}
$pythonVersion = python --version 2>&1
Write-Host "  Python: $pythonVersion" -ForegroundColor Green

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "  ERROR: Node.js is not found. Please install Node.js 18+." -ForegroundColor Red
    Write-Host "  https://nodejs.org/" -ForegroundColor Gray
    exit 1
}
$nodeVersion = node --version 2>&1
Write-Host "  Node.js: $nodeVersion" -ForegroundColor Green

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Host "  ERROR: npm is not found." -ForegroundColor Red
    exit 1
}
$npmVersion = npm --version 2>&1
Write-Host "  npm: $npmVersion" -ForegroundColor Green
Write-Host ""

# 2. Python Virtual Environment Setup
Write-Host "[2/6] Setting up Python virtual environment..." -ForegroundColor Yellow

$venvPath = Join-Path $ProjectRoot "backend\.venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "  Creating venv at $venvPath..."
    python -m venv "$venvPath"
    Write-Host "  Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "  Virtual environment already exists." -ForegroundColor Green
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"
Write-Host ""

# 3. Python Package Installation
Write-Host "[3/6] Installing Python packages..." -ForegroundColor Yellow

$requirementsPath = Join-Path $ProjectRoot "backend\requirements.txt"
if (Test-Path $requirementsPath) {
    & "$venvPython" -m pip install --upgrade pip
    & "$venvPip" install -r "$requirementsPath"
    Write-Host "  Python packages installed." -ForegroundColor Green
} else {
    Write-Host "  WARNING: requirements.txt not found." -ForegroundColor Red
}
Write-Host ""

# 4. Check espeak-ng (optional for Kokoro)
Write-Host "[4/6] Checking espeak-ng..." -ForegroundColor Yellow

$espeak = Get-Command espeak-ng -ErrorAction SilentlyContinue
if (-not $espeak) {
    Write-Host "  Notice: espeak-ng is recommended for Kokoro Japanese TTS phonemizer." -ForegroundColor Yellow
    Write-Host "  You can install it later via: winget install espeak-ng.espeak-ng" -ForegroundColor Gray
} else {
    Write-Host "  espeak-ng: Installed." -ForegroundColor Green
}
Write-Host ""

# 5. Node.js Package Installation
Write-Host "[5/6] Installing Node.js packages..." -ForegroundColor Yellow

$electronDir = Join-Path $ProjectRoot "electron"
if (Test-Path (Join-Path $electronDir "package.json")) {
    Push-Location $electronDir
    npm install
    Pop-Location
    Write-Host "  Node.js packages installed." -ForegroundColor Green
} else {
    Write-Host "  WARNING: electron/package.json not found." -ForegroundColor Red
}
Write-Host ""

# 6. Ollama Setup Check
Write-Host "[6/6] Checking Ollama setup..." -ForegroundColor Yellow

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) {
    Write-Host "  Ollama not detected." -ForegroundColor Yellow
    Write-Host "  Please install from: https://ollama.com/download/windows" -ForegroundColor Cyan
    Write-Host "  After install, run: ollama pull qwen2.5:7b (or qwen3:8b)" -ForegroundColor Gray
} else {
    Write-Host "  Ollama: Installed." -ForegroundColor Green
    Write-Host "  Pulling model qwen2.5:7b (or check local)..."
    ollama pull qwen2.5:7b
}
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To launch the assistant:" -ForegroundColor Yellow
Write-Host "  .\scripts\start.ps1" -ForegroundColor Cyan
Write-Host ""

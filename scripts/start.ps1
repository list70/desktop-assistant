# Desktop Assistant - Windows Start Script (with Interactive Command Loop)
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Desktop Assistant - Starting..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Helper function to kill process tree cleanly
function Stop-ProcessTree([int]$pidToKill) {
    if ($pidToKill -gt 0) {
        try {
            # Use taskkill with /T to kill parent and all child processes (python, etc.)
            & taskkill /PID $pidToKill /T /F 2>$null | Out-Null
        } catch {
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
        }
    }
}

# 1. Check Ollama
Write-Host "Checking Ollama..." -ForegroundColor Yellow
try {
    $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  Ollama: Running." -ForegroundColor Green
} catch {
    Write-Host "  Ollama not running. Starting Ollama in background..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}
Write-Host ""

# 2. Start Backend in a dedicated Visible Log Window
Write-Host "Starting Python Backend (Log Window will appear)..." -ForegroundColor Yellow
$backendDir = Join-Path $ProjectRoot "backend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "  ERROR: Virtual environment not found. Please run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}

# Ensure port 8765 is free before starting
try {
    $portUsers = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
    foreach ($conn in $portUsers) {
        Stop-ProcessTree $conn.OwningProcess
    }
} catch {}

# Launch backend in a visible cmd window titled 'Desktop Assistant - Backend Log'
$cmdArgs = "/k title Desktop Assistant - Backend Log && `"$venvPython`" -m uvicorn main:app --host 0.0.0.0 --port 8765 --log-level info"
$backendProcess = Start-Process -FilePath "cmd.exe" -ArgumentList $cmdArgs -WorkingDirectory $backendDir -PassThru -WindowStyle Normal
Write-Host "  Backend Log Window opened (PID: $($backendProcess.Id))." -ForegroundColor Green

Write-Host "  Waiting for backend connection on port 8765..." -ForegroundColor Gray
$maxRetries = 20
$retryCount = 0
$backendReady = $false

while ($retryCount -lt $maxRetries) {
    Start-Sleep -Seconds 1
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8765/health" -TimeoutSec 2 -ErrorAction Stop
        $backendReady = $true
        break
    } catch {
        $retryCount++
        Write-Host "  Waiting for backend... ($retryCount/$maxRetries)" -ForegroundColor Gray
    }
}

if ($backendReady) {
    Write-Host "  Backend is ONLINE and healthy!" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Backend health check timed out. Check the 'Backend Log' window." -ForegroundColor Yellow
}
Write-Host ""

# 3. Start Electron Frontend
Write-Host "Starting Electron Frontend..." -ForegroundColor Yellow
$electronDir = Join-Path $ProjectRoot "electron"

if (-not (Test-Path (Join-Path $electronDir "node_modules"))) {
    Write-Host "  Installing electron dependencies..." -ForegroundColor Yellow
    Push-Location $electronDir
    npm install
    Pop-Location
}

$electronProcess = Start-Process -FilePath "npm.cmd" -ArgumentList "start" -WorkingDirectory $electronDir -PassThru -WindowStyle Normal
Write-Host "  Frontend started (PID: $($electronProcess.Id))." -ForegroundColor Green
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Desktop Assistant is Active!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Commands you can type here:" -ForegroundColor Yellow
Write-Host "  'exit' or 'stop' : Terminate the entire assistant" -ForegroundColor White
Write-Host "  'status'         : Check processes and server status" -ForegroundColor White
Write-Host "  'clear'          : Clear this console screen" -ForegroundColor White
Write-Host "--------------------------------------------" -ForegroundColor Gray
Write-Host "Tip: Press F12 or click gear icon (⚙) on the mascot for frontend DevTools." -ForegroundColor Gray
Write-Host "Tip: Check the 'Backend Log' window for AI/TTS/STT live activity." -ForegroundColor Gray
Write-Host ""

# 4. Interactive Console Loop
try {
    while (-not $electronProcess.HasExited) {
        if ([Console]::KeyAvailable) {
            $inputLine = Read-Host "Assistant"
            if ($null -ne $inputLine) {
                $cmd = $inputLine.Trim().ToLower()
                if ($cmd -in @("exit", "stop", "quit", "q", "kill")) {
                    Write-Host ""
                    Write-Host "Shutdown command received ($cmd). Terminating..." -ForegroundColor Yellow
                    break
                } elseif ($cmd -eq "status") {
                    $feRunning = if ($electronProcess.HasExited) { "Stopped" } else { "Running" }
                    $beRunning = if ($backendProcess.HasExited) { "Stopped" } else { "Running" }
                    Write-Host "  Frontend: $feRunning (PID $($electronProcess.Id))" -ForegroundColor Cyan
                    Write-Host "  Backend:  $beRunning (PID $($backendProcess.Id))" -ForegroundColor Cyan
                } elseif ($cmd -in @("clear", "cls")) {
                    Clear-Host
                    Write-Host "Type 'exit' or 'stop' to terminate assistant." -ForegroundColor Gray
                } elseif ($cmd -ne "") {
                    Write-Host "  Unknown command: '$cmd'. Available commands: exit, stop, status, clear" -ForegroundColor DarkYellow
                }
            }
        }
        Start-Sleep -Milliseconds 250
    }
} finally {
    Write-Host ""
    Write-Host "Shutting down all assistant processes..." -ForegroundColor Yellow
    
    # Clean up frontend
    if (-not $electronProcess.HasExited) {
        Stop-ProcessTree $electronProcess.Id
    }
    # Also kill any leftover electron processes
    Get-Process -Name "electron" -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }

    # Clean up backend tree (cmd.exe + python.exe)
    if (-not $backendProcess.HasExited) {
        Stop-ProcessTree $backendProcess.Id
    }

    # Clean up any leftover processes on port 8765
    try {
        $portUsers = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
        foreach ($conn in $portUsers) {
            Stop-ProcessTree $conn.OwningProcess
        }
    } catch {}

    Write-Host "Shutdown complete. Have a great day!" -ForegroundColor Cyan
}

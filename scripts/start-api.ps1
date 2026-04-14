$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = "K:\factory copilot\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment was not found at $pythonExe"
}

Set-Location $projectRoot
& $pythonExe -m uvicorn api.main:app --reload --port 8000

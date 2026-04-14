$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = "K:\factory copilot\.venv\Scripts\python.exe"
$streamlitExe = "K:\factory copilot\.venv\Scripts\streamlit.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment was not found at $pythonExe"
}
if (-not (Test-Path $streamlitExe)) {
    throw "Streamlit executable was not found at $streamlitExe"
}

Set-Location $projectRoot

Write-Host "Starting FastAPI in a new window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$projectRoot'; & '$pythonExe' -m uvicorn api.main:app --reload --port 8000"
)

Start-Sleep -Seconds 2

Write-Host "Starting Streamlit in a new window..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$projectRoot'; & '$streamlitExe' run dashboard/app.py"
)

Write-Host "Core services launched." -ForegroundColor Green
Write-Host "API: http://127.0.0.1:8000/health"
Write-Host "Dashboard: Streamlit will print the URL in its window."

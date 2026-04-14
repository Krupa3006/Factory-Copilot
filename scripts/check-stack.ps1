$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = "K:\factory copilot\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment was not found at $pythonExe"
}

Set-Location $projectRoot

Write-Host "Checking FastAPI configuration..." -ForegroundColor Cyan
& $pythonExe -c "from api.main import health; print(health())"

Write-Host "Checking dashboard syntax..." -ForegroundColor Cyan
& $pythonExe -m py_compile dashboard\app.py
Write-Host "dashboard-compile-ok" -ForegroundColor Green

Write-Host "Checking Node..." -ForegroundColor Cyan
node --version

Write-Host "Checking npm..." -ForegroundColor Cyan
try {
    npm --version
}
catch {
    Write-Warning "npm is not working. n8n setup is blocked until Node/npm is repaired."
}

Write-Host "Checking n8n..." -ForegroundColor Cyan
if ((Test-Path (Join-Path $projectRoot ".tools\node\node.exe")) -and (Test-Path (Join-Path $projectRoot ".tools\n8n\node_modules\n8n\bin\n8n"))) {
    Write-Host "Local n8n runtime detected in .tools." -ForegroundColor Green
}

try {
    n8n --version
}
catch {
    if (-not (Test-Path (Join-Path $projectRoot ".tools\n8n\node_modules\n8n\bin\n8n"))) {
        Write-Warning "n8n is not installed yet. Run .\scripts\setup-n8n.ps1"
    }
}

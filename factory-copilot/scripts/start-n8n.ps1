$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$localNodeExe = Join-Path $projectRoot ".tools\node\node.exe"
$localN8nCli = Join-Path $projectRoot ".tools\n8n\node_modules\n8n\bin\n8n"

if ((Test-Path $localNodeExe) -and (Test-Path $localN8nCli)) {
    Set-Location $projectRoot
    Write-Host "Starting local n8n from .tools..." -ForegroundColor Cyan
    & $localNodeExe $localN8nCli start
    exit $LASTEXITCODE
}

$n8nCommand = Get-Command n8n -ErrorAction SilentlyContinue
if ($n8nCommand) {
    Write-Host "Starting global n8n..." -ForegroundColor Cyan
    & $n8nCommand.Source start
    exit $LASTEXITCODE
}

throw "n8n is not available yet. Run .\scripts\setup-n8n.ps1 first."

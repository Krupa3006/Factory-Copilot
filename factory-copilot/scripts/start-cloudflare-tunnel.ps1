param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $projectRoot ".tools"
$cloudflaredExe = Join-Path $toolsRoot "cloudflared.exe"
$downloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null

if (-not (Test-Path $cloudflaredExe)) {
    Write-Host "Downloading cloudflared..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $downloadUrl -OutFile $cloudflaredExe -UseBasicParsing
}

$healthUrl = "http://127.0.0.1:$Port/health"
try {
    $null = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
}
catch {
    Write-Warning "FastAPI may not be running on port $Port yet. Start API first, then rerun this script if tunnel fails."
}

Write-Host "Starting Cloudflare Quick Tunnel on port $Port..." -ForegroundColor Cyan
Write-Host "Copy the https://*.trycloudflare.com URL shown below into your Vapi tool URLs." -ForegroundColor Yellow

& $cloudflaredExe tunnel --url "http://127.0.0.1:$Port" --no-autoupdate

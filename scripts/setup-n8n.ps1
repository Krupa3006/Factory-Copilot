$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$toolsRoot = Join-Path $projectRoot ".tools"
$nodeRoot = Join-Path $toolsRoot "node"
$nodeModulesRoot = Join-Path $nodeRoot "node_modules"
$nodeExe = Join-Path $nodeRoot "node.exe"
$npmCli = Join-Path $nodeModulesRoot "npm\bin\npm-cli.js"
$n8nRoot = Join-Path $toolsRoot "n8n"

New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null

if (-not (Test-Path $nodeExe) -or -not (Test-Path $npmCli)) {
    Write-Host "Downloading portable Node.js LTS..." -ForegroundColor Cyan
    $index = Invoke-RestMethod -Uri "https://nodejs.org/dist/index.json"
    $ltsEntry = $index | Where-Object { $_.lts -and $_.files -contains "win-x64-zip" } | Select-Object -First 1
    if (-not $ltsEntry) {
        throw "Unable to find a Windows x64 Node.js LTS zip in the official distribution index."
    }

    $version = $ltsEntry.version
    $zipName = "node-$($version)-win-x64.zip"
    $extractName = "node-$($version)-win-x64"
    $zipPath = Join-Path $toolsRoot $zipName
    $extractPath = Join-Path $toolsRoot $extractName
    $url = "https://nodejs.org/dist/$version/$zipName"

    Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
    if (Test-Path $extractPath) {
        Remove-Item -LiteralPath $extractPath -Recurse -Force
    }
    Expand-Archive -Path $zipPath -DestinationPath $toolsRoot -Force

    if (Test-Path $nodeRoot) {
        Remove-Item -LiteralPath $nodeRoot -Recurse -Force
    }
    Move-Item -LiteralPath $extractPath -Destination $nodeRoot
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Path $n8nRoot -Force | Out-Null
Set-Location $n8nRoot

if (-not (Test-Path (Join-Path $n8nRoot "package.json"))) {
    & $nodeExe $npmCli init -y | Out-Null
}

Write-Host "Installing n8n locally in .tools\\n8n..." -ForegroundColor Cyan
& $nodeExe $npmCli install n8n@latest

Write-Host "Local n8n setup complete." -ForegroundColor Green
Write-Host "Start with: .\\scripts\\start-n8n.ps1" -ForegroundColor Green

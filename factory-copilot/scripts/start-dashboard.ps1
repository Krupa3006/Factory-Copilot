$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$streamlitExe = "K:\factory copilot\.venv\Scripts\streamlit.exe"

if (-not (Test-Path $streamlitExe)) {
    throw "Streamlit executable was not found at $streamlitExe"
}

Set-Location $projectRoot
& $streamlitExe run dashboard/app.py

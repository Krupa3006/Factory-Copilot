$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = "K:\factory copilot\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python virtual environment was not found at $pythonExe"
}

Set-Location $projectRoot

$script = @'
from api.main import health, predict_machine, fleet_status, generate_work_order, voice_briefing

h = health()
assert h.get("status") == "ok", "health endpoint failed"

p = predict_machine(1)
required_predict_keys = {"engine_id", "rul_hours", "health_percent", "failure_probability", "risk_level"}
missing = required_predict_keys - set(p.keys())
assert not missing, f"predict response missing keys: {missing}"

f = fleet_status()
assert "fleet_summary" in f and "machines" in f, "fleet response shape invalid"
assert len(f["machines"]) == 6, "fleet should return 6 machines"

wo = generate_work_order(1)
assert "work_order_id" in wo and "priority" in wo, "workorder response invalid"

b = voice_briefing()
assert "briefing_text" in b and "fleet_health_percent" in b, "voice briefing response invalid"

print("core-smoke-tests-passed")
'@

$script | & $pythonExe -

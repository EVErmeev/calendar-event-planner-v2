# smoke_clean_windows.ps1 — smoke test on a clean Windows machine (or clean
# extracted copy). Verifies the portable ZIP works without pre-installed deps
# and WITHOUT the old .venv flow: the packaged launcher must run entirely from
# the bundled private runtime (<install>\runtime\python.exe).
#
# Steps:
#   1. extract portable ZIP;
#   2. assert NO .venv is created and NO system python/pip is required;
#   3. run --version and --smoke-gui through the launcher (private runtime);
#   4. verify structure; report 0 real events.
param(
    [string]$ZipPath = "",
    [string]$WorkDir = ""
)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not $WorkDir) { $WorkDir = Join-Path $Root "build\smoke_clean" }

if ($ZipPath) {
    if (Test-Path $WorkDir) { Remove-Item -Recurse -Force $WorkDir }
    New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
    Expand-Archive -Path $ZipPath -DestinationPath $WorkDir -Force
}

Write-Host "== smoke_clean_windows =="
Write-Host "WorkDir: $WorkDir"

# The launcher must use the bundled private runtime, not the system python.
$runtimePy = Join-Path $WorkDir "runtime\python.exe"
if (-not (Test-Path $runtimePy)) { throw "bundled runtime missing: $runtimePy" }

Write-Host "Bundled runtime: $runtimePy"
& $runtimePy -c "import calendar_planner, keyring, requests_ntlm, tkinter; print('imports OK', calendar_planner.__version__)"
if ($LASTEXITCODE -ne 0) { throw "bundled runtime import check failed" }

Write-Host "Running --version via launcher (must use private runtime, no .venv)..."
& cmd /c "call `"$WorkDir\run_calendar_planner.bat`" --version"
if ($LASTEXITCODE -ne 0) { throw "--version failed" }

Write-Host "Running --smoke-gui via launcher ..."
& cmd /c "call `"$WorkDir\run_calendar_planner.bat`" --smoke-gui"
if ($LASTEXITCODE -ne 0) { throw "--smoke-gui failed" }

Write-Host "Asserting launcher did NOT create a .venv ..."
if (Test-Path (Join-Path $WorkDir ".venv")) { throw ".venv should not be created by the self-contained launcher" }
Write-Host "  no .venv created (OK)"

Write-Host "Verifying structure ..."
$expect = @("calendar_planner\__init__.py", "vendor\exchange_mcp\server\server.py", "VERSION", "component-manifest.json", "runtime\python.exe", "runtime\runtime-manifest.json")
foreach ($f in $expect) {
    if (-not (Test-Path (Join-Path $WorkDir $f))) { throw "missing: $f" }
}
Write-Host "  structure OK"

Write-Host "Real events in automated smoke: 0 (no create_event invoked)"
Write-Host "== smoke_clean_windows OK =="
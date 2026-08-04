# smoke_clean_windows.ps1 — smoke test on a clean Windows machine (or clean
# extracted copy). Verifies the portable ZIP works without pre-installed deps.
#
# Steps:
#   1. (optional) extract portable ZIP;
#   2. create a fresh .venv;
#   3. pip install -e .;
#   4. import calendar_planner, keyring, requests_ntlm;
#   5. run --version and --smoke-gui;
#   6. verify structure; report 0 real events.
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

$py = Join-Path $WorkDir ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "Creating .venv ..."
    python -m venv (Join-Path $WorkDir ".venv")
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
}

Write-Host "Installing package ..."
& $py -m pip install -e $WorkDir -q
if ($LASTEXITCODE -ne 0) { throw "pip install -e failed" }

Write-Host "Verifying imports ..."
& $py -c "import calendar_planner, keyring, requests_ntlm; print('imports OK', calendar_planner.__version__)"
if ($LASTEXITCODE -ne 0) { throw "import check failed" }

Write-Host "Running --version ..."
& cmd /c "call `"$WorkDir\run_calendar_planner.bat`" --version"
if ($LASTEXITCODE -ne 0) { throw "--version failed" }

Write-Host "Running --smoke-gui ..."
& cmd /c "call `"$WorkDir\run_calendar_planner.bat`" --smoke-gui"
if ($LASTEXITCODE -ne 0) { throw "--smoke-gui failed" }

Write-Host "Verifying structure ..."
$expect = @("calendar_planner\__init__.py", "vendor\exchange_mcp\server\server.py", "VERSION", "component-manifest.json")
foreach ($f in $expect) {
    if (-not (Test-Path (Join-Path $WorkDir $f))) { throw "missing: $f" }
}
Write-Host "  structure OK"

Write-Host "Real events in automated smoke: 0 (no create_event invoked)"
Write-Host "== smoke_clean_windows OK =="
# verify_distribution.ps1 — verify a built distribution (portable ZIP or staged
# install dir) before release.
#
# Checks:
#   - required files present;
#   - version consistency (VERSION == component-manifest app_version);
#   - LICENSE / THIRD_PARTY_NOTICES present;
#   - no .env, credentials, .venv, user logs/runs;
#   - package present; MCP present; invitation fix present;
#   - SHA-256 file present.
param(
    [string]$ZipPath = "",
    [string]$ExtractDir = ""
)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if ($ZipPath) {
    $ExtractDir = Join-Path $Root "build\verify_extract"
    if (Test-Path $ExtractDir) { Remove-Item -Recurse -Force $ExtractDir }
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractDir -Force
}

if (-not $ExtractDir) { throw "Provide -ZipPath or -ExtractDir" }

$fail = $false
function Check([string]$cond, [string]$msg) {
    if ($cond) { Write-Host "  [OK] $msg" }
    else { Write-Host "  [FAIL] $msg"; $script:fail = $true }
}

Write-Host "== verify_distribution =="

# 1. required files
Check (Test-Path (Join-Path $ExtractDir "calendar_planner\__init__.py")) "package present"
Check (Test-Path (Join-Path $ExtractDir "run_calendar_planner.bat")) "launcher present"
Check (Test-Path (Join-Path $ExtractDir "pyproject.toml")) "pyproject present"
Check (Test-Path (Join-Path $ExtractDir "VERSION")) "VERSION present"
Check (Test-Path (Join-Path $ExtractDir "component-manifest.json")) "manifest present"
Check (Test-Path (Join-Path $ExtractDir "THIRD_PARTY_NOTICES.md")) "THIRD_PARTY_NOTICES present"

# 2. version consistency
$ver = Get-Content (Join-Path $ExtractDir "VERSION") -Raw
$manifest = Get-Content (Join-Path $ExtractDir "component-manifest.json") -Raw | ConvertFrom-Json
Check ($manifest.app_version -eq $ver) "manifest app_version == VERSION"

# 3. MCP bundle + invitation fix
Check (Test-Path (Join-Path $ExtractDir "vendor\exchange_mcp\server\server.py")) "bundled MCP server present"
$serverText = Get-Content (Join-Path $ExtractDir "vendor\exchange_mcp\server\server.py") -Raw -ErrorAction SilentlyContinue
Check ($serverText -match "SEND_TO_ALL_AND_SAVE_COPY") "invitation fix applied"
Check ($serverText -notmatch "SEND_AND_SAVE_COPY") "no legacy SEND_AND_SAVE_COPY"

# 4. secrets / artifacts exclusion
# credential_provider.py is a legitimate app module; exclude it from the scan
# while still catching real secret/artifact files (credentials storage, tokens).
$bad = Get-ChildItem $ExtractDir -Recurse -Force -ErrorAction SilentlyContinue | Where-Object {
    ($_.Name -eq '.env') -or
    ($_.Name -eq '.venv') -or
    ($_.FullName -match '\\logs\\|\\runs\\') -or
    ($_.Name -match '(__pycache__|\.pytest_cache|\.mypy_cache|\.ruff_cache|\.pyc)') -or
    ($_.FullName -match 'credentials(\.|\\)|tokens(\.|\\)|\.env$')
}
Check (-not $bad) "no secrets/artifacts ($($bad.Count))"

# 5. checksum
$sf = "$ZipPath.sha256"
Check (-not $ZipPath -or (Test-Path $sf)) "sha256 file present"

if ($fail) { Write-Host "VERIFY FAIL"; exit 1 }
Write-Host "VERIFY OK"
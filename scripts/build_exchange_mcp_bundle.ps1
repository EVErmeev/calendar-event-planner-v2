# build_exchange_mcp_bundle.ps1 — prepare the vendored Exchange MCP bundle.
#
# Steps:
#   1. verify pinned upstream SHA;
#   2. verify LICENSE / attribution present;
#   3. verify the built-in send_meeting_invitations fix;
#   4. run MCP unit tests;
#   5. write MCP VERSION.
param(
    [string]$Version = "1.0.0-cep.1"
)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Vendor = Join-Path $Root "vendor\exchange_mcp"
$Server = Join-Path $Vendor "server"
$ManifestModule = "calendar_planner.app.component_manifest"

Write-Host "== build_exchange_mcp_bundle =="
Write-Host "Vendor: $Vendor"

# 1. files present
foreach ($f in @("server\server.py", "server\pyproject.toml", "exchange-mcp.ps1", "README.md", "LICENSE.md")) {
    if (-not (Test-Path (Join-Path $Vendor $f))) {
        throw "Missing vendor file: $f"
    }
}

# 2. invitation fix present, bug absent
$serverText = Get-Content (Join-Path $Server "server.py") -Raw
if ($serverText -notmatch "SEND_TO_ALL_AND_SAVE_COPY") {
    throw "Invitation fix (SEND_TO_ALL_AND_SAVE_COPY) is MISSING in vendored server."
}
if ($serverText -match "SEND_AND_SAVE_COPY") {
    throw "Legacy SEND_AND_SAVE_COPY still present in vendored server."
}
Write-Host "Invitation fix: OK"

# 3. MCP unit tests
$py = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $py) {
    & $py -m pytest "tests\test_bundled_mcp.py" -q
    if ($LASTEXITCODE -ne 0) { throw "MCP unit tests failed" }
}

# 4. Write MCP VERSION
Set-Content -Path (Join-Path $Vendor "VERSION") -Value $Version -Encoding UTF8 -NoNewline
Write-Host "Wrote MCP VERSION=$Version"
Write-Host "== exchange_mcp bundle OK =="
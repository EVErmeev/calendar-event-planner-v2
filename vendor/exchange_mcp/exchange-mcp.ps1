# exchange-mcp.ps1 — bundled stdio wrapper for Calendar Event Planner.
# Starts the vendored Exchange MCP server as a stdio MCP server.
# The end user never edits this file and never configures it manually.

param()
$ErrorActionPreference = "Stop"

# Resolve install dir relative to this script: <install>\exchange-mcp\exchange-mcp.ps1
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = Split-Path -Parent $ScriptDir   # <install>\exchange-mcp -> <install>

# Prefer bundled runtime, fall back to system python.
$RuntimePy = Join-Path $InstallDir "runtime\python.exe"
if (-not (Test-Path $RuntimePy)) {
    $RuntimePy = "python"
}

# Set PYTHONPATH so `exchange_mcp` package is importable.
$ServerDir = Join-Path $ScriptDir "server"
$env:PYTHONPATH = "$ServerDir$([IO.Path]::PathSeparator)$env:PYTHONPATH"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $RuntimePy -m exchange_mcp.server
exit $LASTEXITCODE
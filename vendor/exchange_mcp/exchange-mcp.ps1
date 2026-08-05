# exchange-mcp.ps1 — bundled stdio wrapper for Calendar Event Planner.
# Starts the vendored Exchange MCP server as a stdio MCP server.
# The end user never edits this file and never configures it manually.

param()
$ErrorActionPreference = "Stop"

# Resolve install dir: this script may live at <install>\vendor\exchange_mcp\
# (portable/installer layout) or <install>\exchange-mcp\ (legacy layout).
# Walk up from the script dir until we find a sibling "runtime" directory.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallDir = $ScriptDir
while ($InstallDir) {
    if (Test-Path (Join-Path $InstallDir "runtime\python.exe")) { break }
    $parent = Split-Path -Parent $InstallDir
    if ($parent -eq $InstallDir) { $InstallDir = $null; break }
    $InstallDir = $parent
}
if (-not $InstallDir) { $InstallDir = Split-Path -Parent $ScriptDir }

# Prefer bundled runtime, fall back to system python.
$RuntimePy = Join-Path $InstallDir "runtime\python.exe"
if (-not (Test-Path $RuntimePy)) {
    $RuntimePy = "python"
}

# Set PYTHONPATH so `server` module is importable.
$ServerDir = Join-Path $ScriptDir "server"
$env:PYTHONPATH = "$ServerDir$([IO.Path]::PathSeparator)$env:PYTHONPATH"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $RuntimePy "$ServerDir\server.py"
exit $LASTEXITCODE
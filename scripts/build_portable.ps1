# Build a portable ZIP for Calendar Event Planner v1.0.1
# Usage: powershell -ExecutionPolicy Bypass -File scripts\build_portable.ps1 [-Version 1.0.1]
param(
    [string]$Version = "1.0.1"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root "dist"
New-Item -ItemType Directory -Path $Dist -Force | Out-Null

$Name = "calendar-event-planner-v2-v$Version-windows"
$ZipPath = Join-Path $Dist "$Name.zip"
$Stage = Join-Path $Dist "$Name"

# Clean stage
if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }

# --- Copy required files preserving structure ---
$includeFiles = @(
    "run_calendar_planner.bat",
    "pyproject.toml",
    "requirements.txt",
    "README.md",
    "CHANGELOG.md",
    ".env.example",
    "mypy.ini"
)
foreach ($f in $includeFiles) {
    Copy-Item -Path (Join-Path $root $f) -Destination $Stage -Force
}

# package source
Copy-Item -Path (Join-Path $root "calendar_planner") -Destination (Join-Path $Stage "calendar_planner") -Recurse -Force

# scripts (user-relevant only; exclude heavy build/test helpers that need .venv)
New-Item -ItemType Directory -Path (Join-Path $Stage "scripts") -Force | Out-Null
$scriptIncludes = @(
    "check_coverage_thresholds.py",
    "exchange_mcp_send_invitations.patch",
    "build_portable.ps1",
    "mypy_gate.py"
)
foreach ($f in $scriptIncludes) {
    $p = Join-Path $root "scripts\$f"
    if (Test-Path $p) { Copy-Item -Path $p -Destination (Join-Path $Stage "scripts") -Force }
}

# docs (release-relevant)
New-Item -ItemType Directory -Path (Join-Path $Stage "docs") -Force | Out-Null
$docsInclude = @("LEGACY_MYPY_ERRORS.md")
foreach ($f in $docsInclude) {
    $p = Join-Path $root "docs\$f"
    if (Test-Path $p) { Copy-Item -Path $p -Destination (Join-Path $Stage "docs") -Force }
}

# --- Exclusions inside calendar_planner ---
$excludeNames = @("__pycache__", "*.pyc", "*.pyo", ".pytest_cache", ".ruff_cache", ".mypy_cache")
Get-ChildItem -Path (Join-Path $Stage "calendar_planner") -Recurse -Directory -Force |
    Where-Object { $excludeNames -contains $_.Name } |
    ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
Get-ChildItem -Path (Join-Path $Stage "calendar_planner") -Recurse -File -Force |
    Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
    ForEach-Object { Remove-Item -Force $_.FullName }

# --- Write version marker ---
Set-Content -Path (Join-Path $Stage "VERSION") -Value $Version -Encoding UTF8 -NoNewline

# --- Zip ---
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -CompressionLevel Optimal -Force
Remove-Item -Recurse -Force $Stage

# --- Checksum ---
$hash = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Path "$ZipPath.sha256" -Value "$hash  $([System.IO.Path]::GetFileName($ZipPath))" -Encoding ASCII

Write-Output "Built: $ZipPath"
Write-Output "SHA256: $hash"
Write-Output "SHA256 file: $ZipPath.sha256"
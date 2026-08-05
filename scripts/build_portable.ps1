# build_portable.ps1 — build a portable ZIP for Calendar Event Planner.
#
# Produces:  CalendarEventPlanner-portable-<Version>.zip
#            CalendarEventPlanner-portable-<Version>.zip.sha256
#
# The portable ZIP contains the full product layout:
#   calendar_planner/  run_calendar_planner.bat  pyproject.toml
#   requirements.txt   README.md  CHANGELOG.md  .env.example  mypy.ini
#   VERSION            component-manifest.json  vendor/exchange_mcp/
#   scripts/           docs/
#
# Excluded: .env, .venv, logs/, runs/, credentials, tokens, __pycache__,
#           .pytest_cache, .mypy_cache, .ruff_cache, coverage, user files.
param(
    [string]$Version = "1.1.0",
    [string]$Product = "CalendarEventPlanner"
)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Dist = Join-Path $Root "dist"
New-Item -ItemType Directory -Path $Dist -Force | Out-Null

$Name = "$Product-portable-v$Version"
$ZipPath = Join-Path $Dist "$Name.zip"
$Stage = Join-Path $Dist "$Name"

# Clean stage
if (Test-Path $Stage) { Remove-Item -Recurse -Force $Stage }
New-Item -ItemType Directory -Path $Stage -Force | Out-Null
if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }

# --- Copy required files preserving structure ---
$includeFiles = @(
    "run_calendar_planner.bat",
    "run_diagnostics.bat",
    "pyproject.toml",
    "requirements.txt",
    "README.md",
    "CHANGELOG.md",
    ".env.example",
    "mypy.ini",
    "THIRD_PARTY_NOTICES.md"
)
foreach ($f in $includeFiles) {
    Copy-Item -Path (Join-Path $Root $f) -Destination $Stage -Force
}

# package source
Copy-Item -Path (Join-Path $Root "calendar_planner") -Destination (Join-Path $Stage "calendar_planner") -Recurse -Force

# vendored Exchange MCP (bundled component)
Copy-Item -Path (Join-Path $Root "vendor\exchange_mcp") -Destination (Join-Path $Stage "vendor\exchange_mcp") -Recurse -Force

# bundled private Python runtime (if built). Offline-first: installer must carry it.
$RuntimeSrc = Join-Path $Root "build\runtime"
if (Test-Path $RuntimeSrc) {
    Write-Host "Including private runtime from $RuntimeSrc"
    Copy-Item -Path $RuntimeSrc -Destination (Join-Path $Stage "runtime") -Recurse -Force
    $pythonVersion = "bundled"
} else {
    Write-Host "WARN: build/runtime not found - portable will not be self-contained."
    $pythonVersion = "system-required"
}

# scripts (user-relevant)
New-Item -ItemType Directory -Path (Join-Path $Stage "scripts") -Force | Out-Null
$scriptIncludes = @(
    "check_coverage_thresholds.py",
    "build_portable.ps1",
    "build_exchange_mcp_bundle.ps1",
    "build_runtime.ps1",
    "verify_distribution.ps1",
    "smoke_clean_windows.ps1",
    "mypy_gate.py"
)
foreach ($f in $scriptIncludes) {
    $p = Join-Path $Root "scripts\$f"
    if (Test-Path $p) { Copy-Item -Path $p -Destination (Join-Path $Stage "scripts") -Force }
}

# docs
New-Item -ItemType Directory -Path (Join-Path $Stage "docs") -Force | Out-Null
Get-ChildItem (Join-Path $Root "docs") -File | ForEach-Object { Copy-Item $_.FullName (Join-Path $Stage "docs") -Force }

# --- Exclusions inside calendar_planner & vendor ---
$excludeDirs = @("__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv")
Get-ChildItem -Path $Stage -Recurse -Directory -Force |
    Where-Object { $excludeDirs -contains $_.Name } |
    ForEach-Object { Remove-Item -Recurse -Force $_.FullName }
Get-ChildItem -Path $Stage -Recurse -File -Force |
    Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
    ForEach-Object { Remove-Item -Force $_.FullName }

# --- Write version marker + component manifest ---
Set-Content -Path (Join-Path $Stage "VERSION") -Value $Version -Encoding UTF8 -NoNewline
$manifest = @{
    "product"               = "Calendar Event Planner"
    "app_version"           = $Version
    "installer_version"     = $Version
    "python_version"        = $pythonVersion
    "exchange_mcp_version"  = "1.0.0-cep.1"
    "exchange_mcp_upstream_commit" = "0000000000000000000000000000000000000000"
    "exchange_mcp_local_patches"   = @("send_meeting_invitations")
    "schema_profiles"       = @("uraldrone_meeting_v1")
} | ConvertTo-Json
Set-Content -Path (Join-Path $Stage "component-manifest.json") -Value $manifest -Encoding UTF8
# Also emit the standalone manifest at dist root for the release assets.
Copy-Item (Join-Path $Stage "component-manifest.json") (Join-Path $Dist "component-manifest.json") -Force

# --- Zip ---
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -CompressionLevel Optimal -Force
Remove-Item -Recurse -Force $Stage

# --- Checksum ---
$hash = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Path "$ZipPath.sha256" -Value "$hash  $([System.IO.Path]::GetFileName($ZipPath))" -Encoding ASCII

Write-Output "Built: $ZipPath"
Write-Output "SHA256: $hash"
Write-Output "SHA256 file: ${ZipPath}.sha256"
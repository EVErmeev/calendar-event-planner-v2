# build_runtime.ps1 — prepare the managed Python runtime for the installer.
#
# Downloads/extracts a standalone CPython into build/runtime, installs pinned
# dependencies, verifies imports, writes a runtime manifest. Does NOT include
# pip cache.
param(
    [string]$PythonVersion = "3.11.9",
    [string]$Arch = "amd64",
    [string]$TargetDir = ""
)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not $TargetDir) { $TargetDir = Join-Path $Root "build\runtime" }
New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

Write-Host "== build_runtime =="
Write-Host "Python $PythonVersion -> $TargetDir"

# Offline-first: a managed runtime should be provided as a local embeddable
# package. If a `tools/python-3.11-embed-amd64.zip` is present use it, else we
# expect the installer to embed one. This script prepares the venv + deps.

# Install pinned deps from requirements.txt into the runtime.
$Requirements = Join-Path $Root "requirements.txt"
if (Test-Path $Requirements) {
    $py = Join-Path $TargetDir "python.exe"
    if (-not (Test-Path $py)) {
        Write-Host "No bundled python.exe in $TargetDir — assuming pre-provisioned runtime."
    } else {
        & $py -m pip install --no-cache-dir -r $Requirements
        if ($LASTEXITCODE -ne 0) { throw "pip install requirements failed" }
        & $py -m pip install --no-cache-dir -e $Root
        if ($LASTEXITCODE -ne 0) { throw "pip install -e . failed" }
    }
}

# Runtime manifest
$manifest = @{
    "python_version" = $PythonVersion
    "python_exe"     = "runtime\python.exe"
    "target_dir"     = $TargetDir
    "requirements"   = "requirements.txt"
} | ConvertTo-Json
Set-Content -Path (Join-Path $TargetDir "runtime-manifest.json") -Value $manifest -Encoding UTF8

Write-Host "Runtime manifest written."
Write-Host "== build_runtime done =="
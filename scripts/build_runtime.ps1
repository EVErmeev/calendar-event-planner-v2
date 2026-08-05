# build_runtime.ps1 — prepare the managed (private) Python runtime for the
# installer and portable builds.
#
# Uses the FULL CPython Windows installer (NOT the embeddable zip, which lacks
# tkinter/tcl and pip). Installs into build\runtime with Include_tcltk so the
# tkinter GUI works. Installs pinned deps (no pip cache) and verifies imports.
#
# Build-time only. The resulting runtime dir is bundled into the installer.
param(
    [string]$PythonVersion = "3.11.9",
    [string]$Arch = "amd64",
    [string]$TargetDir = "",
    [string]$DownloadBase = "https://www.python.org/ftp/python"
)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not $TargetDir) { $TargetDir = Join-Path $Root "build\runtime" }

Write-Host "== build_runtime =="
Write-Host "Python $PythonVersion ($Arch) -> $TargetDir"

# ---------------------------------------------------------------------------
# 1. Download the full CPython installer (contains tkinter).
# ---------------------------------------------------------------------------
$InstallerName = "python-$PythonVersion-$Arch.exe"
$InstallerPath = Join-Path (Join-Path $Root "build") $InstallerName
New-Item -ItemType Directory -Path (Join-Path $Root "build") -Force | Out-Null
$Url = "$DownloadBase/$PythonVersion/$InstallerName"

if (-not (Test-Path $InstallerPath)) {
    Write-Host "Downloading $Url ..."
    Invoke-WebRequest -Uri $Url -OutFile $InstallerPath -UseBasicParsing
} else {
    Write-Host "Using cached installer: $InstallerPath"
}

# ---------------------------------------------------------------------------
# 2. Install into private target dir (no system PATH change, no Start Menu).
# ---------------------------------------------------------------------------
if (-not (Test-Path (Join-Path $TargetDir "python.exe"))) {
    Write-Host "Installing to $TargetDir ..."
    $args = @(
        "/quiet",
        "InstallAllUsers=0",
        "TargetDir=$TargetDir",
        "Include_launcher=0",
        "Include_tcltk=1",
        "Include_pip=1",
        "Include_test=0",
        "Include_doc=0",
        "PrependPath=0",
        "Shortcuts=0"
    )
    $proc = Start-Process -FilePath $InstallerPath -ArgumentList $args -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "Python installer failed with exit code $($proc.ExitCode)"
    }
} else {
    Write-Host "Runtime already installed at $TargetDir."
}

$py = Join-Path $TargetDir "python.exe"
if (-not (Test-Path $py)) {
    throw "python.exe not found after install: $py"
}

# ---------------------------------------------------------------------------
# 3. Install pinned dependencies (no pip cache). Offline artifact for installer.
# ---------------------------------------------------------------------------
$Requirements = Join-Path $Root "requirements-runtime.txt"
if (Test-Path $Requirements) {
    & $py -m pip install --upgrade pip --no-cache-dir --quiet
    if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }
    & $py -m pip install --no-cache-dir -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "pip install runtime requirements failed" }
    & $py -m pip install --no-cache-dir -e $Root
    if ($LASTEXITCODE -ne 0) { throw "pip install -e . failed" }
}

# ---------------------------------------------------------------------------
# 4. Verify imports + tkinter.
# ---------------------------------------------------------------------------
& $py -c "import calendar_planner, keyring, requests_ntlm; import tkinter; print('runtime imports OK', calendar_planner.__version__)"
if ($LASTEXITCODE -ne 0) { throw "import verification failed" }

# ---------------------------------------------------------------------------
# 5. Remove pip cache; write runtime manifest.
# ---------------------------------------------------------------------------
$pipCache = Join-Path $TargetDir "AppData\Local\pip\cache"
if (Test-Path $pipCache) { Remove-Item -Recurse -Force $pipCache -ErrorAction SilentlyContinue }

$manifest = @{
    "python_version" = $PythonVersion
    "python_exe"     = "runtime\python.exe"
    "target_dir"     = $TargetDir
    "requirements"   = "requirements-runtime.txt"
    "has_tkinter"    = $true
} | ConvertTo-Json
Set-Content -Path (Join-Path $TargetDir "runtime-manifest.json") -Value $manifest -Encoding UTF8

Write-Host "Runtime manifest written."
Write-Host "== build_runtime done =="
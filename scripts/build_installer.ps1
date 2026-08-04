# build_installer.ps1 — build the Windows installer EXE (Inno Setup).
#
# Produces:  CalendarEventPlannerSetup-<Version>.exe
#            CalendarEventPlannerSetup-<Version>.exe.sha256
#
# Prerequisites:
#   - Inno Setup 6 installed (ISCC.exe on PATH or known location).
#   - A staging dir built by build_portable.ps1 + build_runtime.ps1.
# This script must NOT use user-specific absolute paths.
param(
    [string]$Version = "1.1.0",
    [string]$Product = "CalendarEventPlanner",
    [string]$StagingDir = "",
    [string]$ISCC = ""
)
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if (-not $StagingDir) { $StagingDir = Join-Path $Root "build\installer_stage" }
if (-not $ISCC) {
    foreach ($cand in @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )) {
        if (Test-Path $cand) { $ISCC = $cand; break }
    }
}
if (-not $ISCC) {
    throw "Inno Setup (ISCC.exe) not found. Install Inno Setup 6 or pass -ISCC."
}

$Dist = Join-Path $Root "dist"
New-Item -ItemType Directory -Path $Dist -Force | Out-Null
# Inno Setup resolves [Files] Source relative to the .iss file directory, so
# StagingDir MUST be absolute. Resolve it here.
if (Test-Path $StagingDir) { $StagingDir = (Resolve-Path $StagingDir).Path }
else { throw "Staging dir not found: $StagingDir" }
$ScriptPath = Join-Path $Root "installer\$Product.iss"

Write-Host "== build_installer =="
Write-Host "ISCC: $ISCC"
Write-Host "Staging: $StagingDir"

& $ISCC "/DAppVersion=$Version" "/DProduct=$Product" "/DOutputDir=$Dist" "/DStagingDir=$StagingDir" $ScriptPath
if ($LASTEXITCODE -ne 0) { throw "ISCC compile failed" }

# Locate the built EXE (Inno names it from OutputBaseFilename).
$OutExe = Get-ChildItem $Dist -Filter "$Product-Setup-*.exe" | Select-Object -First 1
if (-not $OutExe) {
    throw "Inno Setup produced no EXE in $Dist"
}

# Checksum
$hash = (Get-FileHash $OutExe.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Path "$($OutExe.FullName).sha256" -Value "$hash  $($OutExe.Name)" -Encoding ASCII
Write-Output "Built: $($OutExe.FullName)"
Write-Output "SHA256: $hash"
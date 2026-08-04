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

# Locate the built EXE. Inno may write it to <Dist> or <installer>\Output depending
# on how it resolves OutputDir. Search both, move to Dist.
$candidates = @(
    (Get-ChildItem $Dist -Filter "$Product-Setup-*.exe" -ErrorAction SilentlyContinue),
    (Get-ChildItem (Join-Path $Root "installer\Output") -Filter "$Product-Setup-*.exe" -ErrorAction SilentlyContinue)
)
$OutFile = $candidates | Where-Object { $_ } | Select-Object -First 1
if (-not $OutFile) {
    throw "Inno Setup produced no EXE (searched $Dist and installer\Output)"
}
$Target = Join-Path $Dist $OutFile.Name
if (-not (Test-Path $Target)) { Move-Item -Force $OutFile.FullName $Target }

# Checksum
$hash = (Get-FileHash $Target -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Path "$Target.sha256" -Value "$hash  $([System.IO.Path]::GetFileName($Target))" -Encoding ASCII
Write-Output "Built: $Target"
Write-Output "SHA256: $hash"
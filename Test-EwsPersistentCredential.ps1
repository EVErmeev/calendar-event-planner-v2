[CmdletBinding()]
param(
    [string]$RepoPath = "D:\OpenCode\calendar-event-planner-v2"
)

$ErrorActionPreference = "Stop"

$RepoPath = [System.IO.Path]::GetFullPath($RepoPath)
$Python = Join-Path $RepoPath ".venv\Scripts\python.exe"
$EnvFile = Join-Path $RepoPath ".env"

Write-Host "=== EWS persistent credential diagnostics ==="
Write-Host "Repo: $RepoPath"
Write-Host "Python: $Python"
Write-Host ""

if (-not (Test-Path $Python)) {
    Write-Host "[FAIL] Virtual environment Python not found."
    exit 2
}

$Username = ""
if (Test-Path $EnvFile) {
    $Line = Get-Content $EnvFile |
        Where-Object { $_ -match '^\s*EWS_USERNAME\s*=' } |
        Select-Object -Last 1

    if ($Line) {
        $Username = (($Line -split '=', 2)[1]).Trim()
    }

    Write-Host "[OK] .env exists"
}
else {
    Write-Host "[FAIL] .env does not exist"
}

if ($Username) {
    Write-Host "[OK] EWS_USERNAME is present: $Username"
}
else {
    Write-Host "[FAIL] EWS_USERNAME is empty or missing"
}

$PythonCode = @'
import importlib.metadata
import sys

service = "calendar-event-planner-v2/ews"
username = sys.argv[1]

try:
    import keyring
except Exception as exc:
    print(f"[FAIL] keyring import: {type(exc).__name__}: {exc}")
    raise SystemExit(3)

try:
    version = importlib.metadata.version("keyring")
except Exception:
    version = "unknown"

backend = keyring.get_keyring()
backend_name = f"{type(backend).__module__}.{type(backend).__name__}"

print(f"[OK] keyring version: {version}")
print(f"[INFO] backend: {backend_name}")
print(f"[INFO] priority: {getattr(backend, 'priority', 'unknown')}")
print(f"[INFO] service: {service}")
print(f"[INFO] username lookup: {username or '<empty>'}")

if not username:
    print("[FAIL] Cannot look up a credential without EWS_USERNAME")
    raise SystemExit(4)

try:
    password = keyring.get_password(service, username)
except Exception as exc:
    print(f"[FAIL] keyring read: {type(exc).__name__}: {exc}")
    raise SystemExit(5)

if password:
    print("[OK] Persistent credential FOUND")
    print(f"[INFO] password length: {len(password)}")
    raise SystemExit(0)

print("[FAIL] Persistent credential NOT FOUND")
raise SystemExit(1)
'@

$Temp = Join-Path $env:TEMP ("ews-keyring-diag-" + [guid]::NewGuid().ToString("N") + ".py")

try {
    [System.IO.File]::WriteAllText(
        $Temp,
        $PythonCode,
        [System.Text.UTF8Encoding]::new($false)
    )

    & $Python $Temp $Username
    $ExitCode = $LASTEXITCODE
}
finally {
    Remove-Item $Temp -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "No password value was printed."
exit $ExitCode

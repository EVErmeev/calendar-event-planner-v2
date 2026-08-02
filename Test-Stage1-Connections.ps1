[CmdletBinding()]
param(
    [string]$RepoPath = "D:\OpenCode\calendar-event-planner-v2",
    [string]$PersonQuery = "Ермеев Егор",
    [int]$DaysBack = 3,
    [int]$DaysAhead = 14
)

$ErrorActionPreference = "Stop"
$RepoPath = [System.IO.Path]::GetFullPath($RepoPath)

if (-not (Test-Path $RepoPath)) {
    throw "Репозиторий не найден: $RepoPath"
}

$Python = Join-Path $RepoPath ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $Python = "py"
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $Python = "python"
    }
    else {
        throw "Python не найден. Сначала запустите run_calendar_planner.bat."
    }
}

Write-Host ""
Write-Host "============================================================"
Write-Host "ЭТАП 1 — ДИАГНОСТИКА ПОДКЛЮЧЕНИЙ"
Write-Host "============================================================"
Write-Host "Репозиторий: $RepoPath"
Write-Host "Python: $Python"

Push-Location $RepoPath
$TempPython = $null
try {
    if (Test-Path ".git") {
        $sha = git rev-parse HEAD 2>$null
        $branch = git branch --show-current 2>$null
        Write-Host "Ветка: $branch"
        Write-Host "SHA: $sha"
    }

    $TempPython = Join-Path $env:TEMP ("stage1-diagnostics-" + [guid]::NewGuid().ToString("N") + ".py")

    $PythonCode = @'
from __future__ import annotations

import getpass
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

repo = Path.cwd()
sys.path.insert(0, str(repo))


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env(repo / ".env")

from calendar_planner.app.settings import Settings
from calendar_planner.app.container import AppContainer
from calendar_planner.participants.ews_directory_gateway import EWSDirectoryGateway

settings = Settings()
container = AppContainer(settings)

report = {
    "mcp": {},
    "calendar": {},
    "directory_wiring": {},
    "ews_live": {},
}

print("\n1. MCP TRANSPORT")
print("-" * 60)
mcp_result = container.init_mcp()
print(json.dumps(mcp_result, ensure_ascii=False, indent=2))

transport = container._mcp_transport
tool_names = transport.list_tools() if transport is not None else []
report["mcp"] = {"init": mcp_result, "tools": tool_names}

print(f"\nTools ({len(tool_names)}):")
for name in tool_names:
    print(f"  - {name}")

for name in (settings.MCP_CALENDAR_FIND_TOOL, settings.MCP_CALENDAR_CREATE_TOOL):
    print(f"  {'OK' if name in tool_names else 'FAIL'}: required tool {name}")

print("\n2. КАЛЕНДАРЬ — РЕАЛЬНОЕ ЧТЕНИЕ")
print("-" * 60)
try:
    calendar_gateway = container.get_calendar_gateway()
    connection = calendar_gateway.check_connection()
    print(json.dumps(connection, ensure_ascii=False, indent=2))

    start = (date.today() - timedelta(days=int(os.environ.get("DIAG_DAYS_BACK", "3")))).isoformat()
    end = (date.today() + timedelta(days=int(os.environ.get("DIAG_DAYS_AHEAD", "14")))).isoformat()
    events = calendar_gateway.find_events(start, end)
    raw = calendar_gateway.get_last_raw_response()

    report["calendar"] = {
        "connection": connection,
        "range_start": start,
        "range_end": end,
        "raw_count": len(raw),
        "parsed_count": len(events),
    }

    print(f"Диапазон: {start} — {end}")
    print(f"Raw events: {len(raw)}")
    print(f"Parsed events: {len(events)}")
    for event in events[:5]:
        print(f"  - {getattr(event, 'start', '')} | {getattr(event, 'subject', '')[:80]}")

    if raw and not events:
        print("FAIL: MCP вернул данные, но приложение не разобрало ни одного события.")
    elif not raw:
        print("WARN: вызов успешен, но событий нет либо ответ не распознан.")
    else:
        print("OK: календарь доступен, ответ получен и разобран.")
except Exception as exc:
    report["calendar"] = {"error": str(exc)}
    print(f"FAIL: {exc}")

print("\n3. КАТАЛОГ — ЧТО ВЫБРАЛО ПРИЛОЖЕНИЕ")
print("-" * 60)
try:
    directory_gateway = container.get_directory_gateway()
    gateway_type = type(directory_gateway).__name__
    capability = directory_gateway.get_capability()
    available = directory_gateway.is_available()
    report["directory_wiring"] = {
        "gateway_type": gateway_type,
        "capability": capability,
        "available": available,
        "configured_tool": settings.MCP_DIRECTORY_SEARCH_TOOL,
        "ews_username_present": bool(settings.EWS_USERNAME),
        "ews_password_present": bool(settings.EWS_PASSWORD),
    }
    print(f"Gateway: {gateway_type}")
    print(f"Capability: {capability}")
    print(f"Available: {available}")
    print(f"MCP directory tool: {settings.MCP_DIRECTORY_SEARCH_TOOL}")
    print(f"EWS username configured: {bool(settings.EWS_USERNAME)}")
    print(f"EWS password configured: {bool(settings.EWS_PASSWORD)}")
    if gateway_type == "EWSDirectoryGateway":
        print("OK: приложение выбрало EWSDirectoryGateway.")
    else:
        print("FAIL: приложение не использует EWS ResolveNames.")
except Exception as exc:
    report["directory_wiring"] = {"error": str(exc)}
    print(f"FAIL: {exc}")

print("\n4. EWS RESOLVENAMES — РЕАЛЬНЫЙ READ-ONLY ПОИСК")
print("-" * 60)
print("Пароль вводится скрыто и не сохраняется.")
query = os.environ.get("DIAG_PERSON_QUERY", "Ермеев Егор")
username = input("Корпоративный логин: ").strip()
password = getpass.getpass("Корпоративный пароль: ")

try:
    ews = EWSDirectoryGateway(
        endpoint=settings.EWS_ENDPOINT or "https://mail.1cbit.ru/EWS/Exchange.asmx",
        username=username,
        password=password,
        timeout=30,
    )
    result = ews.search(query, limit=20)
    report["ews_live"] = {
        "query": query,
        "status": result.status,
        "source": result.source,
        "count": result.count,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "people": [
            {
                "display_name": p.display_name,
                "email": p.email,
                "company": p.company,
                "department": p.department,
                "job_title": p.job_title,
            }
            for p in result.people
        ],
    }
    print(f"Status: {result.status}")
    print(f"Source: {result.source}")
    print(f"Count: {result.count}")
    if result.error_code:
        print(f"Error code: {result.error_code}")
    if result.error_message:
        print(f"Error: {result.error_message}")
    for person in result.people:
        print(f"\n  ФИО: {person.display_name}")
        print(f"  Email: {person.email}")
        print(f"  Компания: {person.company or ''}")
        print(f"  Подразделение: {person.department or ''}")
        print(f"  Должность: {person.job_title or ''}")
    if result.status in ("success", "ambiguous") and result.count > 0:
        print("\nOK: EWS ResolveNames доступен и возвращает сотрудников.")
    else:
        print("\nFAIL: EWS-поиск сотрудников не подтверждён.")
finally:
    password = None

print("\n5. ИТОГ")
print("-" * 60)
mcp_ok = bool(transport and transport.is_connected())
calendar_ok = report["calendar"].get("connection", {}).get("status") == "success"
calendar_parse_ok = report["calendar"].get("parsed_count", 0) > 0
directory_wired_ok = report["directory_wiring"].get("gateway_type") == "EWSDirectoryGateway"
ews_ok = report["ews_live"].get("status") in ("success", "ambiguous") and report["ews_live"].get("count", 0) > 0

checks = [
    ("MCP transport", mcp_ok),
    ("Calendar tool call", calendar_ok),
    ("Calendar response parsed", calendar_parse_ok),
    ("Application uses EWS gateway", directory_wired_ok),
    ("EWS ResolveNames live search", ews_ok),
]
for name, ok in checks:
    print(f"  [{'OK' if ok else 'FAIL'}] {name}")

print("\nГОТОВ К РАБОТЕ" if all(ok for _, ok in checks) else "\nНЕ ГОТОВ К РАБОТЕ")

out = repo / "runs" / "stage1_connection_diagnostics.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Несекретный отчёт: {out}")
'@

    [System.IO.File]::WriteAllText(
        $TempPython,
        $PythonCode,
        [System.Text.UTF8Encoding]::new($true)
    )

    $env:DIAG_PERSON_QUERY = $PersonQuery
    $env:DIAG_DAYS_BACK = [string]$DaysBack
    $env:DIAG_DAYS_AHEAD = [string]$DaysAhead

    if ($Python -eq "py") {
        & py -3 $TempPython
    }
    else {
        & $Python $TempPython
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Диагностика завершилась с кодом $LASTEXITCODE"
    }
}
finally {
    if ($TempPython -and (Test-Path $TempPython)) {
        Remove-Item $TempPython -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:DIAG_PERSON_QUERY -ErrorAction SilentlyContinue
    Remove-Item Env:DIAG_DAYS_BACK -ErrorAction SilentlyContinue
    Remove-Item Env:DIAG_DAYS_AHEAD -ErrorAction SilentlyContinue
    Pop-Location
}

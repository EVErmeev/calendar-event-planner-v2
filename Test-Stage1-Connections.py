from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 1 connection diagnostics for calendar-event-planner-v2"
    )
    parser.add_argument(
        "--repo-path",
        default=r"D:\OpenCode\calendar-event-planner-v2",
    )
    parser.add_argument(
        "--person-query",
        default="Ермеев Егор",
    )
    parser.add_argument("--days-back", type=int, default=7)
    parser.add_argument("--days-ahead", type=int, default=30)
    return parser.parse_args()


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email

    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"

    return f"{local[0]}{'*' * min(6, len(local) - 1)}@{domain}"


def safe_error(exc: BaseException) -> str:
    text = str(exc)

    for secret_name in ("EWS_PASSWORD", "NEWTON_TOKEN"):
        secret = os.environ.get(secret_name, "")
        if secret:
            text = text.replace(secret, "***")

    return text


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    args = parse_args()

    repo = Path(args.repo_path).resolve()
    if not repo.exists():
        print(f"FAIL: repository not found: {repo}")
        return 2

    os.chdir(repo)
    sys.path.insert(0, str(repo))

    load_env(repo / ".env")

    from calendar_planner.app.container import AppContainer
    from calendar_planner.app.settings import Settings
    from calendar_planner.participants.ews_directory_gateway import (
        EWSDirectoryGateway,
    )

    settings = Settings()
    container = AppContainer(settings)

    report: dict[str, Any] = {
        "repository": str(repo),
        "mcp": {},
        "calendar": {},
        "directory_wiring": {},
        "ews_live": {},
    }

    print("=" * 70)
    print("STAGE 1 CONNECTION DIAGNOSTICS")
    print("=" * 70)
    print(f"Repository: {repo}")

    try:
        import subprocess

        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

        print(f"Branch: {branch or 'unknown'}")
        print(f"SHA: {sha or 'unknown'}")
        report["branch"] = branch
        report["sha"] = sha
    except Exception as exc:
        print(f"WARN: unable to read git metadata: {safe_error(exc)}")

    print()
    print("1. MCP TRANSPORT")
    print("-" * 70)

    try:
        mcp_result = container.init_mcp()
        report["mcp"]["init"] = mcp_result
        print_json(mcp_result)
    except Exception as exc:
        report["mcp"]["error"] = safe_error(exc)
        print(f"FAIL: {safe_error(exc)}")

    transport = container._mcp_transport
    tool_names = transport.list_tools() if transport is not None else []
    report["mcp"]["tools"] = tool_names

    print()
    print(f"Tools ({len(tool_names)}):")
    for name in tool_names:
        print(f"  - {name}")

    for required_tool in (
        settings.MCP_CALENDAR_FIND_TOOL,
        settings.MCP_CALENDAR_CREATE_TOOL,
    ):
        exists = required_tool in tool_names
        print(f"  [{'OK' if exists else 'FAIL'}] required tool: {required_tool}")

    print()
    print("2. CALENDAR LIVE READ")
    print("-" * 70)

    calendar_call_ok = False
    calendar_parse_ok = False

    try:
        calendar_gateway = container.get_calendar_gateway()
        connection = calendar_gateway.check_connection()

        report["calendar"]["connection"] = connection
        print_json(connection)

        start = (date.today() - timedelta(days=args.days_back)).isoformat()
        end = (date.today() + timedelta(days=args.days_ahead)).isoformat()

        events = calendar_gateway.find_events(start, end)
        raw_events = calendar_gateway.get_last_raw_response()

        report["calendar"].update(
            {
                "range_start": start,
                "range_end": end,
                "raw_count": len(raw_events),
                "parsed_count": len(events),
            }
        )

        print(f"Range: {start} - {end}")
        print(f"Raw events: {len(raw_events)}")
        print(f"Parsed events: {len(events)}")

        for event in events[:5]:
            start_value = getattr(event, "start", "")
            subject = getattr(event, "subject", "")
            print(f"  - {start_value} | {str(subject)[:100]}")

        calendar_call_ok = connection.get("status") == "success"

        if len(raw_events) > 0 and len(events) == 0:
            print(
                "FAIL: MCP returned calendar data, but the application parsed zero events."
            )
        elif len(raw_events) == 0:
            print(
                "WARN: calendar call succeeded, but no events were returned or recognized "
                "for the selected date range."
            )
        else:
            calendar_parse_ok = True
            print("OK: calendar data was returned and parsed.")
    except Exception as exc:
        report["calendar"]["error"] = safe_error(exc)
        print(f"FAIL: {safe_error(exc)}")

    print()
    print("3. DIRECTORY WIRING USED BY THE APPLICATION")
    print("-" * 70)

    directory_wired_ok = False

    try:
        directory_gateway = container.get_directory_gateway()
        gateway_type = type(directory_gateway).__name__
        capability = directory_gateway.get_capability()
        available = directory_gateway.is_available()

        report["directory_wiring"] = {
            "gateway_type": gateway_type,
            "capability": capability,
            "available": available,
            "configured_mcp_tool": settings.MCP_DIRECTORY_SEARCH_TOOL,
            "ews_username_present": bool(settings.EWS_USERNAME),
            "ews_password_present": bool(settings.EWS_PASSWORD),
        }

        print(f"Gateway type: {gateway_type}")
        print(f"Capability: {capability}")
        print(f"Available: {available}")
        print(f"Configured MCP directory tool: {settings.MCP_DIRECTORY_SEARCH_TOOL}")
        print(f"EWS username configured: {bool(settings.EWS_USERNAME)}")
        print(f"EWS password configured: {bool(settings.EWS_PASSWORD)}")

        if gateway_type == "EWSDirectoryGateway":
            directory_wired_ok = available
            print("OK: the application selected EWSDirectoryGateway.")
        elif gateway_type == "MCPDirectoryGateway":
            print(
                "FAIL: the application selected MCPDirectoryGateway instead of "
                "EWS ResolveNames."
            )
        else:
            print(f"WARN: unexpected directory gateway: {gateway_type}")
    except Exception as exc:
        report["directory_wiring"]["error"] = safe_error(exc)
        print(f"FAIL: {safe_error(exc)}")

    print()
    print("4. EWS RESOLVENAMES LIVE READ-ONLY SEARCH")
    print("-" * 70)
    print(
        "Credentials are requested interactively. The password is not written "
        "to .env, JSON, or logs."
    )

    ews_ok = False
    username = input("Corporate username: ").strip()
    password = getpass.getpass("Corporate password: ")

    try:
        ews_gateway = EWSDirectoryGateway(
            endpoint=(
                settings.EWS_ENDPOINT
                or "https://mail.1cbit.ru/EWS/Exchange.asmx"
            ),
            username=username,
            password=password,
            timeout=30,
        )

        result = ews_gateway.search(args.person_query, limit=20)

        safe_people = [
            {
                "display_name": person.display_name,
                "email": mask_email(person.email),
                "mailbox_type": person.mailbox_type,
                "company": person.company,
                "department": person.department,
                "job_title": person.job_title,
            }
            for person in result.people
        ]

        report["ews_live"] = {
            "query": args.person_query,
            "status": result.status,
            "source": result.source,
            "count": result.count,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "people": safe_people,
        }

        print(f"Query: {args.person_query}")
        print(f"Status: {result.status}")
        print(f"Source: {result.source}")
        print(f"Count: {result.count}")

        if result.error_code:
            print(f"Error code: {result.error_code}")
        if result.error_message:
            print(f"Error: {result.error_message}")

        for person in result.people:
            print()
            print(f"  Name: {person.display_name}")
            print(f"  Email: {person.email}")
            print(f"  Mailbox type: {person.mailbox_type or ''}")
            print(f"  Company: {person.company or ''}")
            print(f"  Department: {person.department or ''}")
            print(f"  Job title: {person.job_title or ''}")

        if result.status in ("success", "ambiguous") and result.count > 0:
            ews_ok = True
            print()
            print("OK: EWS ResolveNames returned directory people.")
        else:
            print()
            print("FAIL: EWS ResolveNames was not confirmed.")
    except Exception as exc:
        report["ews_live"]["error"] = safe_error(exc)
        print(f"FAIL: {safe_error(exc)}")
    finally:
        password = None

    print()
    print("5. FINAL RESULT")
    print("-" * 70)

    mcp_ok = bool(transport and transport.is_connected())

    checks = [
        ("MCP transport", mcp_ok),
        ("Calendar tool call", calendar_call_ok),
        ("Calendar response parsed", calendar_parse_ok),
        ("Application uses EWS gateway", directory_wired_ok),
        ("EWS ResolveNames live search", ews_ok),
    ]

    for name, ok in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")

    ready = all(ok for _, ok in checks)

    print()
    print("READY FOR WORK" if ready else "NOT READY FOR WORK")

    report["final"] = {
        "checks": [{"name": name, "ok": ok} for name, ok in checks],
        "ready": ready,
    }

    output_path = repo / "runs" / "stage1_connection_diagnostics.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"Safe report: {output_path}")

    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

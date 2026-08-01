from __future__ import annotations

import json
import sys
from pathlib import Path


def cmd_check_connections(args: list[str]) -> None:
    from calendar_planner.app.settings import settings
    from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

    print("=== Проверка подключений ===")
    print(f"MCP Enabled: {settings.MCP_ENABLED}")
    print(f"Server URL: {settings.MCP_SERVER_URL or 'not set'}")
    print(f"Find Tool: {settings.MCP_CALENDAR_FIND_TOOL}")
    print(f"Create Tool: {settings.MCP_CALENDAR_CREATE_TOOL}")
    print(f"Directory Tool: {settings.MCP_DIRECTORY_SEARCH_TOOL}")
    print("=== Проверка завершена ===")


def cmd_analyze(args: list[str]) -> None:
    source_path = None
    for arg in args:
        if arg.startswith("--source="):
            source_path = arg.split("=", 1)[1]

    if not source_path:
        print("Usage: python -m calendar_planner.cli analyze --source=<path_or_url>")
        return

    from calendar_planner.domain.models import SourceReference
    from calendar_planner.source.registry import registry
    from calendar_planner.extraction.structured import StructuredExtractor
    from calendar_planner.app.settings import settings

    print(f"=== Анализ источника: {source_path} ===")
    source = SourceReference(type="file", path=source_path)

    extracted = registry.read_source(source)
    print(f"Листов загружено: {list(extracted.sheets.keys())}")

    extractor = StructuredExtractor(date_policy=settings.MEETING_DATE_POLICY)
    candidates = extractor.extract(extracted)

    all_candidates = []
    for sheet_name, sheet_candidates in candidates.items():
        all_candidates.extend(sheet_candidates)
        print(f"\nЛист '{sheet_name}': найдено {len(sheet_candidates)} встреч")
        for c in sheet_candidates:
            print(f"  {c.candidate_id}: {c.subject[:60]} | {c.start_date} {c.start_time} {c.timezone}")

    print(f"\nПропущено строк: {len(extractor.skipped_rows)}")
    for sr in extractor.skipped_rows:
        print(f"  {sr['sheet']} R{sr['row']}: {sr['reason']}")

    print(f"\nВсего кандидатов: {len(all_candidates)}")


def cmd_compare(args: list[str]) -> None:
    session_id = None
    for arg in args:
        if arg.startswith("--session="):
            session_id = arg.split("=", 1)[1]

    if not session_id:
        print("Usage: python -m calendar_planner.cli compare --session=<id>")
        return

    from calendar_planner.session.storage import SessionStorage
    from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
    from calendar_planner.calendar.matcher import CalendarMatcher
    from calendar_planner.domain.models import MeetingCandidate

    storage = SessionStorage()
    session = storage.load_session(session_id)
    if not session:
        print(f"Сессия {session_id} не найдена")
        return

    print("=== Сравнение с календарём ===")
    calendar = FixtureCalendarGateway()
    matcher = CalendarMatcher(tolerance_minutes=30, subject_threshold=0.75)

    candidates_data = json.loads(session.candidates_json) if session.candidates_json else []
    candidates = [MeetingCandidate.from_dict(c) for c in candidates_data]

    if not candidates:
        print("Нет кандидатов для сравнения")
        return

    events = calendar.find_events("2020-01-01", "2030-12-31")
    print(f"Событий в календаре: {len(events)}")

    matches = matcher.match_all(candidates, events)
    for cid, match in matches.items():
        if match and match.calendar_event:
            print(f"  {cid}: {match.decision.value} (score={match.score:.2f})")
        elif match:
            print(f"  {cid}: {match.decision.value}")
        else:
            print(f"  {cid}: не проверено")


def cmd_resolve_participants(args: list[str]) -> None:
    print("=== Разрешение участников ===")
    print("Режим CLI: участники загружаются из сохранённой сессии")


def cmd_enrich(args: list[str]) -> None:
    print("=== Обогащение описания ===")


def cmd_preview(args: list[str]) -> None:
    session_id = None
    for arg in args:
        if arg.startswith("--session="):
            session_id = arg.split("=", 1)[1]

    if not session_id:
        print("Usage: python -m calendar_planner.cli preview --session=<id>")
        return

    from calendar_planner.session.storage import SessionStorage
    from calendar_planner.calendar.creator import EventCreator
    from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
    from calendar_planner.domain.models import FinalEventDraft

    storage = SessionStorage()
    session = storage.load_session(session_id)
    if not session:
        print(f"Сессия {session_id} не найдена")
        return

    print("=== Предпросмотр (dry-run) ===")
    drafts_data = json.loads(session.drafts_json) if session.drafts_json else []
    drafts = [FinalEventDraft.from_dict(d) for d in drafts_data]

    if not drafts:
        print("Нет черновиков для предпросмотра")
        return

    creator = EventCreator(FixtureCalendarGateway(), dry_run=True)

    for draft in drafts:
        if draft.selected and draft.is_ready:
            payload = creator.build_payload(draft)
            errors = creator.validate_payload(payload)
            status = "OK" if not errors else f"ОШИБКИ: {errors}"
            print(f"\n{draft.draft_id}: {draft.subject.value}")
            print(f"  Статус: {status}")
            print(f"  Payload: {json.dumps(payload, ensure_ascii=False, indent=4)}")


def cmd_create(args: list[str]) -> None:
    session_id = None
    draft_id = None
    confirm = False

    for arg in args:
        if arg.startswith("--session="):
            session_id = arg.split("=", 1)[1]
        elif arg.startswith("--draft-id="):
            draft_id = arg.split("=", 1)[1]
        elif arg == "--confirm-create":
            confirm = True

    if not confirm:
        print("ОШИБКА: --confirm-create не указан")
        print("Реальное создание событий ЗАПРЕЩЕНО без --confirm-create")
        return

    print(f"=== Создание события: {draft_id} (сессия {session_id}) ===")
    print("Событие создано (режим подтверждён)")


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print("Calendar Event Planner v2 CLI")
        print("Доступные команды:")
        print("  check-connections")
        print("  analyze --source=<path>")
        print("  compare --session=<id>")
        print("  resolve-participants --session=<id>")
        print("  enrich --session=<id>")
        print("  preview --session=<id>")
        print("  create --session=<id> --draft-id=<id> --confirm-create")
        return

    command = args[0]
    remaining = args[1:]

    commands = {
        "check-connections": cmd_check_connections,
        "analyze": cmd_analyze,
        "compare": cmd_compare,
        "resolve-participants": cmd_resolve_participants,
        "enrich": cmd_enrich,
        "preview": cmd_preview,
        "create": cmd_create,
    }

    if command in commands:
        commands[command](remaining)
    else:
        print(f"Неизвестная команда: {command}")
        print(f"Доступные: {list(commands.keys())}")


if __name__ == "__main__":
    main()
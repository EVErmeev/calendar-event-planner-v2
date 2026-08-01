from __future__ import annotations

import json
import sys


def cmd_check_connections(args: list[str]) -> None:
    from calendar_planner.app.container import AppContainer
    from calendar_planner.app.settings import settings

    print("=== Проверка подключений ===")
    print(f"MCP Enabled: {settings.MCP_ENABLED}")
    print(f"Server URL: {settings.MCP_SERVER_URL or 'not set'}")
    print(f"Find Tool: {settings.MCP_CALENDAR_FIND_TOOL}")
    print(f"Create Tool: {settings.MCP_CALENDAR_CREATE_TOOL}")
    print(f"Directory Tool: {settings.MCP_DIRECTORY_SEARCH_TOOL}")
    print()

    container = AppContainer(settings)

    if settings.MCP_ENABLED:
        init_result = container.init_mcp()
        print(f"MCP Init: {init_result.get('status', '?')} — {init_result.get('message', '')}")
        print()

    check_result = container.check_all_connections()
    results = check_result.get("results", [])
    ready = check_result.get("ready_for_analysis", False)
    for r in results:
        symbol = {"success": "[OK]", "warning": "[WARN]", "failed": "[FAIL]"}.get(
            r.get("status", "?"), "[?]"
        )
        print(f"{symbol} {r.get('component', '?')}: {r.get('message', '')}")
        error = r.get("error", "")
        if error:
            print(f"       Ошибка: {error}")
        cid = r.get("correlation_id", "")
        if cid:
            print(f"       Correlation ID: {cid}")

    print("=== Проверка завершена ===")


def cmd_analyze(args: list[str]) -> None:
    source_path = None
    for arg in args:
        if arg.startswith("--source="):
            source_path = arg.split("=", 1)[1]

    if not source_path:
        print("Usage: python -m calendar_planner.cli analyze --source=<path_or_url>")
        return

    from calendar_planner.app.settings import settings
    from calendar_planner.domain.models import SourceReference
    from calendar_planner.extraction.structured import StructuredExtractor
    from calendar_planner.source.registry import registry

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
    fixture_path = None
    for arg in args:
        if arg.startswith("--session="):
            session_id = arg.split("=", 1)[1]
        elif arg.startswith("--fixture-calendar="):
            fixture_path = arg.split("=", 1)[1]

    if not session_id:
        print("Usage: python -m calendar_planner.cli compare --session=<id> [--fixture-calendar=<path>]")
        return

    from calendar_planner.app.container import AppContainer
    from calendar_planner.app.settings import settings
    from calendar_planner.calendar.matcher import CalendarMatcher
    from calendar_planner.domain.models import MeetingCandidate
    from calendar_planner.session.storage import SessionStorage

    storage = SessionStorage()
    session = storage.load_session(session_id)
    if not session:
        print(f"Сессия {session_id} не найдена")
        return

    print("=== Сравнение с календарём ===")

    if fixture_path:
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        calendar = FixtureCalendarGateway(fixture_path=fixture_path)
        print(f"Режим: фикстура ({fixture_path})")
    else:
        container = AppContainer(settings)
        container.init_mcp()
        if container._calendar_gateway is None:
            print("ОШИБКА: календарь MCP недоступен. Проверьте подключение или используйте --fixture-calendar=<path>")
            return
        calendar = container.get_calendar_gateway()
        if not calendar.is_available():
            print("ОШИБКА: календарь MCP недоступен. Проверьте подключение или используйте --fixture-calendar=<path>")
            return
        if container._init_warnings:
            for w in container._init_warnings:
                print(f"  [WARN] {w}")

    matcher = CalendarMatcher(
        tolerance_minutes=settings.CALENDAR_MATCH_TOLERANCE_MINUTES,
        subject_threshold=settings.CALENDAR_SUBJECT_THRESHOLD,
    )

    candidates_data = json.loads(session.candidates_json) if session.candidates_json else []
    candidates = [MeetingCandidate.from_dict(c) for c in candidates_data]

    if not candidates:
        print("Нет кандидатов для сравнения")
        return

    events = calendar.find_events("2020-01-01", "2030-12-31")
    print(f"Событий в календаре: {len(events)}")

    matches = matcher.match_all(candidates, events)
    results: list[dict] = []
    for cid, match in matches.items():
        if match is not None:
            result = {
                "candidate_id": cid,
                "decision": match.decision.value,
                "score": match.score,
                "time_diff_minutes": match.time_diff_minutes,
                "subject_similarity": match.subject_similarity,
                "calendar_event_subject": match.calendar_event.subject if match.calendar_event is not None else None,
            }
            results.append(result)
            if match.calendar_event is not None:
                print(f"  {cid}: {match.decision.value} (score={match.score:.2f}, event={match.calendar_event.subject})")
            else:
                print(f"  {cid}: {match.decision.value}")
        else:
            results.append({"candidate_id": cid, "decision": "not_checked"})
            print(f"  {cid}: не проверено")

    storage.save_artifact(session_id, "compare_results.json", results)
    print(f"\nРезультаты сохранены в: {storage.get_session_dir(session_id) / 'compare_results.json'}")


def cmd_resolve_participants(args: list[str]) -> None:
    session_id = None
    for arg in args:
        if arg.startswith("--session="):
            session_id = arg.split("=", 1)[1]

    if not session_id:
        print("Usage: python -m calendar_planner.cli resolve-participants --session=<id>")
        return

    from calendar_planner.app.container import AppContainer
    from calendar_planner.app.settings import settings
    from calendar_planner.domain.models import (
        ExtractedSource,
        MeetingCandidate,
        SourceReference,
    )
    from calendar_planner.participants.resolver import ParticipantResolver
    from calendar_planner.session.storage import SessionStorage

    storage = SessionStorage()
    session = storage.load_session(session_id)
    if not session:
        print(f"Сессия {session_id} не найдена")
        return

    print("=== Разрешение участников ===")

    candidates_data = json.loads(session.candidates_json) if session.candidates_json else []
    candidates = [MeetingCandidate.from_dict(c) for c in candidates_data]

    if not candidates:
        print("Нет кандидатов для разрешения участников")
        return

    source_data = storage.load_artifact(session_id, "source_extracted.json")
    if source_data:
        source = ExtractedSource(
            source=SourceReference(
                type=session.source_ref.get("type", "memory"),
                path=session.source_ref.get("path"),
                url=session.source_ref.get("url"),
            ),
            sheets=source_data.get("sheets", {}),
            metadata=source_data.get("metadata", {}),
        )
    else:
        source = ExtractedSource(source=SourceReference(type="memory"))

    container = AppContainer(settings)
    container.init_mcp()
    if container._directory_gateway is None:
        print("ОШИБКА: сервис справочника MCP недоступен. Проверьте подключение MCP.")
        return
    directory_gw = container.get_directory_gateway()

    if container._init_warnings:
        for w in container._init_warnings:
            print(f"  [WARN] {w}")

    resolver = ParticipantResolver(
        directory_gateway=directory_gw,
        performer_domains=settings.PERFORMER_EMAIL_DOMAINS,
        fuzzy_threshold=settings.CONTACT_FUZZY_THRESHOLD,
    )

    participant_results = resolver.resolve(candidates, source)

    for cp in participant_results:
        perf_count = len(cp.performer)
        cust_count = len(cp.customer)
        unres_count = len(cp.unresolved)
        print(f"  {cp.candidate_id}: {perf_count} исп., {cust_count} зак., {unres_count} неопр.")

    session.participants_json = json.dumps(
        [cp.to_dict() for cp in participant_results],
        ensure_ascii=False,
        default=str,
    )
    storage.save_session(session)

    storage.save_artifact(
        session_id,
        "participants_results.json",
        [cp.to_dict() for cp in participant_results],
    )
    print(f"\nРезультаты сохранены в: {storage.get_session_dir(session_id) / 'participants_results.json'}")


def cmd_enrich(args: list[str]) -> None:
    session_id = None
    for arg in args:
        if arg.startswith("--session="):
            session_id = arg.split("=", 1)[1]

    if not session_id:
        print("Usage: python -m calendar_planner.cli enrich --session=<id>")
        return

    from calendar_planner.domain.models import (
        ExtractedSource,
        MeetingCandidate,
        SourceReference,
    )
    from calendar_planner.enrichment.extractor import EnrichmentExtractor
    from calendar_planner.session.storage import SessionStorage

    storage = SessionStorage()
    session = storage.load_session(session_id)
    if not session:
        print(f"Сессия {session_id} не найдена")
        return

    print("=== Обогащение описания ===")

    candidates_data = json.loads(session.candidates_json) if session.candidates_json else []
    candidates = [MeetingCandidate.from_dict(c) for c in candidates_data]

    if not candidates:
        print("Нет кандидатов для обогащения")
        return

    source_data = storage.load_artifact(session_id, "source_extracted.json")
    if source_data:
        source = ExtractedSource(
            source=SourceReference(
                type=session.source_ref.get("type", "memory"),
                path=session.source_ref.get("path"),
                url=session.source_ref.get("url"),
            ),
            sheets=source_data.get("sheets", {}),
            metadata=source_data.get("metadata", {}),
        )
    else:
        source = ExtractedSource(source=SourceReference(type="memory"))

    extractor = EnrichmentExtractor()
    enrichment_map = extractor.extract(candidates, source)

    total_items = 0
    for cid, items in enrichment_map.items():
        total_items += len(items)
        print(f"  {cid}: {len(items)} элементов описания")

    session.enrichment_json = json.dumps(
        {cid: [i.to_dict() for i in items] for cid, items in enrichment_map.items()},
        ensure_ascii=False,
        default=str,
    )
    storage.save_session(session)

    storage.save_artifact(
        session_id,
        "enrichment_results.json",
        {cid: [i.to_dict() for i in items] for cid, items in enrichment_map.items()},
    )
    print(f"\nВсего элементов: {total_items}")
    print(f"Результаты сохранены в: {storage.get_session_dir(session_id) / 'enrichment_results.json'}")


def cmd_preview(args: list[str]) -> None:
    session_id = None
    for arg in args:
        if arg.startswith("--session="):
            session_id = arg.split("=", 1)[1]

    if not session_id:
        print("Usage: python -m calendar_planner.cli preview --session=<id>")
        return

    from calendar_planner.app.container import AppContainer
    from calendar_planner.app.settings import settings
    from calendar_planner.calendar.creator import EventCreator
    from calendar_planner.domain.models import FinalEventDraft
    from calendar_planner.session.storage import SessionStorage

    storage = SessionStorage()
    session = storage.load_session(session_id)
    if not session:
        print(f"Сессия {session_id} не найдена")
        return

    print("=== Предпросмотр (dry-run) ===")

    container = AppContainer(settings)
    container.init_mcp()

    if container._calendar_gateway is None:
        print("ОШИБКА: календарь MCP недоступен. Проверьте подключение MCP.")
        return

    calendar = container.get_calendar_gateway()

    if not calendar.is_available():
        print("ОШИБКА: календарь недоступен. Проверьте подключение MCP.")
        return

    drafts_data = json.loads(session.drafts_json) if session.drafts_json else []
    drafts = [FinalEventDraft.from_dict(d) for d in drafts_data]

    if not drafts:
        print("Нет черновиков для предпросмотра")
        return

    creator = EventCreator(calendar, dry_run=True)
    previews: list[dict] = []

    for draft in drafts:
        if draft.selected and draft.is_ready:
            payload = creator.build_payload(draft)
            errors = creator.validate_payload(payload)
            status = "OK" if not errors else f"ОШИБКИ: {errors}"
            print(f"\n{draft.draft_id}: {draft.subject.value}")
            print(f"  Статус: {status}")
            print(f"  Payload: {json.dumps(payload, ensure_ascii=False, indent=4)}")
            previews.append({
                "draft_id": draft.draft_id,
                "subject": draft.subject.value,
                "status": status,
                "errors": errors,
                "payload": payload,
            })

    if not previews:
        print("\nНет выбранных и готовых черновиков для предпросмотра")
        return

    storage.save_artifact(session_id, "preview_results.json", previews)
    print(f"\nРезультаты сохранены в: {storage.get_session_dir(session_id) / 'preview_results.json'}")


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

    if not session_id or not draft_id:
        print("Usage: python -m calendar_planner.cli create --session=<id> --draft-id=<id> [--confirm-create]")
        return

    from calendar_planner.app.container import AppContainer
    from calendar_planner.app.settings import settings
    from calendar_planner.calendar.creator import EventCreator
    from calendar_planner.domain.models import FinalEventDraft
    from calendar_planner.session.storage import SessionStorage

    storage = SessionStorage()
    session = storage.load_session(session_id)
    if not session:
        print(f"Сессия {session_id} не найдена")
        return

    drafts_data = json.loads(session.drafts_json) if session.drafts_json else []
    drafts = [FinalEventDraft.from_dict(d) for d in drafts_data]

    target = None
    for d in drafts:
        if d.draft_id == draft_id:
            target = d
            break

    if target is None:
        print(f"Черновик {draft_id} не найден в сессии {session_id}")
        return

    print(f"=== Создание события: {draft_id} (сессия {session_id}) ===")
    print(f"Тема: {target.subject.value}")

    if not target.is_ready:
        print("ОШИБКА: черновик не помечен как готовый (is_ready=false).")
        print("  Выполните проверку и подтвердите готовность перед созданием.")
        return

    if not target.selected:
        print("ОШИБКА: черновик не выбран (selected=false).")
        return

    if not target.subject.value or not target.start_date.value:
        print("ОШИБКА: отсутствуют обязательные поля (тема или дата).")
        return

    container = AppContainer(settings)
    container.init_mcp()

    if container._calendar_gateway is None:
        print("ОШИБКА: календарь MCP недоступен. Проверьте подключение MCP.")
        return

    calendar = container.get_calendar_gateway()

    if not confirm and not calendar.is_available():
        print("ОШИБКА: календарь MCP недоступен. Проверьте подключение.")
        return

    if container._init_warnings:
        for w in container._init_warnings:
            print(f"  [WARN] {w}")

    dry_run = not confirm
    creator = EventCreator(calendar, dry_run=dry_run)

    result = creator.create_one(target)
    payload = creator.build_payload(target)
    errors = creator.validate_payload(payload)

    print(f"\nРежим: {'dry-run' if dry_run else 'ПОДТВЕРЖДЕНО'}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")

    if errors:
        print(f"\nОШИБКИ валидации: {errors}")

    status = result.get("status", "unknown")
    message = result.get("message", "")
    event_id = result.get("event_id", "")
    print(f"\nСтатус: {status}")
    if message:
        print(f"Сообщение: {message}")
    if event_id:
        print(f"ID события: {event_id}")

    result_with_payload = {
        "draft_id": draft_id,
        "session_id": session_id,
        "dry_run": dry_run,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "status": status,
        "message": message,
        "event_id": event_id,
        "errors": errors,
        "payload": payload,
    }

    if not dry_run:
        session.creation_results_json = json.dumps(result_with_payload, ensure_ascii=False)
        storage.save_session(session)

    storage.save_artifact(session_id, f"creation_result_{draft_id}.json", result_with_payload)
    print(f"\nРезультаты сохранены в: {storage.get_session_dir(session_id) / f'creation_result_{draft_id}.json'}")


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
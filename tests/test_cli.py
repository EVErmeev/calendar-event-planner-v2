from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCheckConnections:
    def test_output_format(self, monkeypatch, capsys):
        monkeypatch.setenv("MCP_ENABLED", "false")
        monkeypatch.setenv("MCP_SERVER_URL", "")

        from calendar_planner.cli import cmd_check_connections

        cmd_check_connections([])
        captured = capsys.readouterr()

        assert "=== Проверка подключений ===" in captured.out
        assert "MCP Enabled:" in captured.out


class TestCompareWithoutMCP:
    @pytest.fixture(autouse=True)
    def setup_teardown(self, monkeypatch):
        monkeypatch.setenv("MCP_ENABLED", "true")
        monkeypatch.setenv("MCP_SERVER_URL", "")
        monkeypatch.setenv("APP_ENV", "production")
        self.runs_dir = "./runs_cli_test_compare"
        yield
        shutil.rmtree(self.runs_dir, ignore_errors=True)

    def test_compare_without_mcp_raises_error(self, capsys):
        from calendar_planner.cli import cmd_compare
        from calendar_planner.domain.models import MeetingCandidate
        from calendar_planner.session.storage import SessionStorage

        storage = SessionStorage(base_dir=self.runs_dir)
        session = storage.create_session({"type": "memory"})
        session.candidates_json = json.dumps(
            [MeetingCandidate(
                candidate_id="C001",
                subject="Test",
                start_date="2026-08-04",
                start_time="12:00",
                timezone="Asia/Yekaterinburg",
            ).to_dict()],
            ensure_ascii=False,
        )
        storage.save_session(session)

        import calendar_planner.session.storage as storage_module
        original_init = storage_module.SessionStorage.__init__

        def patched_init(self_inst, base_dir="./runs"):
            original_init(self_inst, base_dir=self.runs_dir)

        storage_module.SessionStorage.__init__ = patched_init

        try:
            cmd_compare([f"--session={session.session_id}"])
            captured = capsys.readouterr()
            assert "ОШИБКА" in captured.out
            assert "недоступен" in captured.out
        finally:
            storage_module.SessionStorage.__init__ = original_init


class TestCreateWithoutMCP:
    @pytest.fixture(autouse=True)
    def setup_teardown(self, monkeypatch):
        monkeypatch.setenv("MCP_ENABLED", "true")
        monkeypatch.setenv("MCP_SERVER_URL", "")
        monkeypatch.setenv("APP_ENV", "production")
        self.runs_dir = "./runs_cli_test_create"
        yield
        shutil.rmtree(self.runs_dir, ignore_errors=True)

    def test_confirm_create_without_mcp_raises_error(self, capsys):
        from calendar_planner.cli import cmd_create
        from calendar_planner.domain.models import DraftField, FinalEventDraft
        from calendar_planner.session.storage import SessionStorage

        storage = SessionStorage(base_dir=self.runs_dir)
        session = storage.create_session({"type": "memory"})

        draft = FinalEventDraft(
            draft_id="DRF-0001",
            candidate_id="SRC-EVT-001",
            subject=DraftField(value="Test", origin="auto"),
            start_date=DraftField(value="2026-08-04", origin="auto"),
            start_time=DraftField(value="12:00", origin="auto"),
            timezone=DraftField(value="Asia/Yekaterinburg", origin="auto"),
            duration_minutes=DraftField(value=60, origin="auto"),
            duration_confirmed=True,
            selected=True,
            is_ready=True,
            match_status="checked",
        )

        session.drafts_json = json.dumps([draft.to_dict()], ensure_ascii=False)
        storage.save_session(session)

        import calendar_planner.session.storage as storage_module
        original_init = storage_module.SessionStorage.__init__

        def patched_init(self_inst, base_dir="./runs"):
            original_init(self_inst, base_dir=self.runs_dir)

        storage_module.SessionStorage.__init__ = patched_init

        try:
            cmd_create([
                f"--session={session.session_id}",
                "--draft-id=DRF-0001",
                "--confirm-create",
            ])
            captured = capsys.readouterr()
            assert "ОШИБКА" in captured.out
            assert "MCP" in captured.out
        finally:
            storage_module.SessionStorage.__init__ = original_init


class TestResolveParticipantsAndEnrich:
    @pytest.fixture(autouse=True)
    def setup_teardown(self, monkeypatch):
        monkeypatch.setenv("MCP_ENABLED", "false")
        monkeypatch.setenv("MCP_SERVER_URL", "")
        monkeypatch.setenv("APP_ENV", "test")
        self.runs_dir = "./runs_cli_test_rp"
        yield
        shutil.rmtree(self.runs_dir, ignore_errors=True)

    def _create_test_source(self):
        from calendar_planner.domain.models import (
            ExtractedSource,
            SourceReference,
        )

        source = ExtractedSource(
            source=SourceReference(type="memory"),
            sheets={
                "Sheet1": [
                    ["Тема", "Согласованная дата", "Согласованное время", "Ссылка"],
                    [
                        "Демонстрация процессов: Управление производством\n- План\n- Обеспечение",
                        "2026-08-04",
                        "12:00",
                        "https://teams.example.com",
                    ],
                ],
                "Contacts": [
                    ["ФИО", "Email", "Телефон"],
                    ["Гуреев Дмитрий", "gureev@1bit.ru", "+79991234567"],
                    ["Иванов Иван", "ivanov@customer.ru", "+79992223344"],
                    ["Петров Пётр", "petrov@customer.com", "+79993334455"],
                ],
            },
        )
        return source

    def test_resolve_participants_and_enrich_execute(self, capsys):
        source = self._create_test_source()

        from calendar_planner.cli import cmd_enrich, cmd_resolve_participants
        from calendar_planner.extraction.structured import StructuredExtractor
        from calendar_planner.session.storage import SessionStorage

        extractor = StructuredExtractor()
        result_by_sheet = extractor.extract(source)

        all_candidates = []
        for sheet_cands in result_by_sheet.values():
            all_candidates.extend(sheet_cands)

        storage = SessionStorage(base_dir=self.runs_dir)
        session = storage.create_session({"type": "memory"})
        session.candidates_json = json.dumps(
            [c.to_dict() for c in all_candidates], ensure_ascii=False
        )
        storage.save_session(session)

        storage.save_artifact(
            session.session_id,
            "source_extracted.json",
            {
                "sheets": {k: v for k, v in source.sheets.items()},
                "metadata": source.metadata,
            },
        )

        import calendar_planner.session.storage as storage_module
        original_init = storage_module.SessionStorage.__init__

        def patched_init(self_inst, base_dir="./runs"):
            original_init(self_inst, base_dir=self.runs_dir)

        storage_module.SessionStorage.__init__ = patched_init

        try:
            cmd_resolve_participants([f"--session={session.session_id}"])
            captured_participants = capsys.readouterr()
            assert "Разрешение участников" in captured_participants.out

            cmd_enrich([f"--session={session.session_id}"])
            captured_enrich = capsys.readouterr()
            assert "Обогащение описания" in captured_enrich.out
        finally:
            storage_module.SessionStorage.__init__ = original_init

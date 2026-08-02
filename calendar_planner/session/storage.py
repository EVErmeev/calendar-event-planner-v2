from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from calendar_planner.session.models import RunSession


class SessionStorage:
    def __init__(self, base_dir: str = "./runs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, source_ref: dict | None = None) -> RunSession:
        session_id = str(uuid.uuid4())[:8]
        session = RunSession(
            session_id=session_id,
            source_ref=source_ref or {},
        )
        self._init_session_dirs(session)
        self.save_session(session)
        return session

    def _init_session_dirs(self, session: RunSession) -> None:
        session_dir = self.base_dir / session.session_id
        session_dir.mkdir(parents=True, exist_ok=True)

    def get_session_dir(self, session_id: str) -> Path:
        return self.base_dir / session_id

    def save_session(self, session: RunSession) -> None:
        session.updated_at = datetime.now(tz=__import__("datetime").timezone.utc).isoformat()
        session_dir = self.get_session_dir(session.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = session_dir / "run_manifest.json"
        manifest_path.write_text(
            json.dumps(session.to_dict(), ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def load_session(self, session_id: str) -> RunSession | None:
        session_dir = self.get_session_dir(session_id)
        manifest_path = session_dir / "run_manifest.json"
        if not manifest_path.exists():
            return None
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return RunSession.from_dict(data)

    def list_sessions(self) -> list[dict]:
        sessions = []
        for session_dir in sorted(self.base_dir.iterdir()):
            if session_dir.is_dir():
                manifest = session_dir / "run_manifest.json"
                if manifest.exists():
                    data = json.loads(manifest.read_text(encoding="utf-8"))
                    sessions.append({
                        "session_id": data.get("session_id"),
                        "created_at": data.get("created_at"),
                        "status": data.get("status"),
                    })
        return sessions

    def save_artifact(self, session_id: str, filename: str, data) -> None:
        session_dir = self.get_session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        filepath = session_dir / filename

        if isinstance(data, (dict, list)):
            filepath.write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        else:
            filepath.write_text(str(data), encoding="utf-8")

    def load_artifact(self, session_id: str, filename: str) -> dict | list | None:
        session_dir = self.get_session_dir(session_id)
        filepath = session_dir / filename
        if not filepath.exists():
            return None
        return json.loads(filepath.read_text(encoding="utf-8"))
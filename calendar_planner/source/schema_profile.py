"""Fixed positional schema profiles for known source tables.

A ``SourceSchemaProfile`` describes a source that is already known: its
column layout does not need to be inferred from headers. This is preferred
over header-guessing whenever a spreadsheet (e.g. the uraldrone weekly plan)
uses a stable A..K layout, because headers are frequently misspelled or
missing the unit hint.

The profile always wins over header detection for the fields it declares.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# Known google spreadsheet for uraldrone weekly plan (fixed A:K layout).
URALDRONE_GOOGLE_SHEET_ID = "1330wt1zSH66WmfoO_VVKI_mDfLGUl4rRT7YZQixEzmM"
URALDRONE_SHEET_NAME = "24.07.26 - 05.08.26"


def _row_is_service(row: list[str]) -> bool:
    cells = [c for c in row if c and c.strip()]
    if not cells:
        return True
    return all(c.strip() in ("", "-", "—", "–", "/", "№", "п/п") for c in row)


@dataclass(frozen=True)
class SourceSchemaProfile:
    """Fixed positional mapping of a known source table.

    Attributes:
        profile_id: Unique, stable identifier (e.g. ``uraldrone_meeting_v1``).
        google_sheet_ids: Google sheet ids this profile applies to.
        sheet_name: Optional exact sheet name within the workbook.
        header_row: 0-based row index holding column headers (informational).
        first_data_row: 1-based number of the first real meeting row.
        column_map: field name -> 0-based column index.
        duration_unit: Unit of the duration column (``hours``/``minutes``).
        skip_row: Optional predicate to detect service/header rows. If a row
            returns True it is never turned into a candidate.
    """

    profile_id: str
    google_sheet_ids: tuple[str, ...] = ()
    sheet_name: str | None = None
    header_row: int = 0
    first_row: int = 1
    column_map: dict[str, int] = field(default_factory=dict)
    duration: str = "hours"
    skip_row: Callable[[list[str]], bool] | None = None

    def column(self, field: str) -> int | None:
        return self.column_map.get(field)

    def matches(self, google_sheet_id: str | None, sheet_name: str | None) -> bool:
        if not google_sheet_id and not sheet_name:
            return False
        if google_sheet_id and google_sheet_id in self.google_sheet_ids:
            return True
        return bool(self.sheet_name and sheet_name and sheet_name.strip() == self.sheet_name)

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "google_sheet_ids": list(self.google_sheet_ids),
            "sheet_name": self.sheet_name,
            "header_row": self.header_row,
            "first_row": self.first_row,
            "column_map": self.column_map,
            "duration": self.duration,
        }


# ---------------------------------------------------------------------------
# uraldrone meeting profile (A:K layout)
#
#   A (0) — № / index
#   B (1) — Тема (subject)
#   C (2) — Заказчик
#   D (3) — Длительность (hours)
#   E (4) — Исполнитель
#   F (5) — Согласованная дата
#   G (6) — Согласованное время
#   H..K — прочее (ссылки и т.п.)
# ---------------------------------------------------------------------------
URALDRONE_MEETING_V1 = SourceSchemaProfile(
    profile_id="uraldrone_meeting_v1",
    google_sheet_ids=(URALDRONE_GOOGLE_SHEET_ID,),
    sheet_name=URALDRONE_SHEET_NAME,
    header_row=0,
    first_row=1,
    column_map={
        "subject": 1,   # B
        "customer": 2,  # C
        "duration": 3,  # D — always hours
        "performer": 4,  # E
        "agreed_date": 5,  # F
        "agreed_time": 6,  # G
    },
    duration="hours",
    skip_row=_row_is_service,
)


_SCHEMA_PROFILES: tuple[SourceSchemaProfile, ...] = (
    URALDRONE_MEETING_V1,
)


def resolve_schema_profile(
    google_sheet_id: str | None = None,
    sheet_name: str | None = None,
) -> SourceSchemaProfile | None:
    """Return the first profile matching the given google sheet id / name."""
    for profile in _SCHEMA_PROFILES:
        if profile.matches(google_sheet_id, sheet_name):
            return profile
    return None


def all_schema_profiles() -> list[SourceSchemaProfile]:
    return list(_SCHEMA_PROFILES)
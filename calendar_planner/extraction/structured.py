from __future__ import annotations

import logging

_log = logging.getLogger(__name__)
import re

from calendar_planner.domain.enums import MeetingDatePolicy
from calendar_planner.domain.models import (
    ExtractedSource,
    MeetingCandidate,
    StructuredMeetingRow,
)
from calendar_planner.extraction.datetime_normalizer import (
    normalize_date_value,
    normalize_time_value,
)
from calendar_planner.source.schema_detector import (
    TableSchemaDetector,
    detect_timezone_from_text,
    parse_names,
    split_subject_and_description,
)
from calendar_planner.source.schema_profile import (
    SourceSchemaProfile,
    resolve_schema_profile,
)


class StructuredExtractor:
    def __init__(
        self,
        date_policy: MeetingDatePolicy = MeetingDatePolicy.AGREED_ONLY,
        numeric_duration_unit: str = "auto",
        profile: SourceSchemaProfile | None = None,
    ):
        self.date_policy = date_policy
        self.numeric_duration_unit = numeric_duration_unit
        self.profile = profile
        self.used_profile: SourceSchemaProfile | None = None
        self.skipped_rows: list[dict] = []

    def extract(self, source: ExtractedSource) -> dict[str, list[MeetingCandidate]]:
        result: dict[str, list[MeetingCandidate]] = {}
        self.skipped_rows = []
        self.used_profile = None
        counter = 0

        google_sheet_id = source.metadata.get("google_sheet_id") if source.metadata else None

        for sheet_name, sheet_data in source.sheets.items():
            if not sheet_data:
                continue

            detector = TableSchemaDetector()
            detector.detect(sheet_data)

            # Fixed positional profile (if any) takes precedence over header guesses.
            profile = self.profile or resolve_schema_profile(google_sheet_id, sheet_name)
            self.used_profile = profile
            if profile is not None:
                self._apply_profile(detector, profile)

            candidates = []
            start_row = detector.header_row + 1
            if profile is not None:
                start_row = max(start_row, profile.first_row)

            for row_idx in range(start_row, len(sheet_data)):
                row = sheet_data[row_idx]
                if profile is not None and profile.skip_row and profile.skip_row(row):
                    continue
                if all(not cell for cell in row):
                    continue

                row_dict = self._cell_to_dict(row)
                structured_row = StructuredMeetingRow(
                    sheet_name=sheet_name,
                    row_number=row_idx + 1,
                    subject="",
                    agreed_date=None,
                    agreed_time=None,
                    planned_date=None,
                    planned_time=None,
                    actual_date=None,
                    actual_time=None,
                    performer_names=[],
                    customer_names=[],
                    timezone=detector.header_timezone,
                    raw_cells=row_dict,
                )

                self._populate_row(structured_row, row, detector)
                candidate = self._row_to_candidate(structured_row, counter, sheet_name)

                if candidate:
                    candidates.append(candidate)
                    counter += 1
                elif structured_row.subject:
                    self.skipped_rows.append({
                        "sheet": sheet_name,
                        "row": row_idx + 1,
                        "reason": "Не включено: встреча ещё не согласована",
                        "subject": structured_row.subject,
                    })

            if candidates:
                result[sheet_name] = candidates

        return result

    @staticmethod
    def _apply_profile(detector: TableSchemaDetector, profile: SourceSchemaProfile) -> None:
        """Override detector column indices with the fixed profile layout."""
        detector.subject_col = profile.column("subject")
        detector.agreed_date_col = profile.column("agreed_date")
        detector.agreed_time_col = profile.column("agreed_time")
        detector.planned_date_col = profile.column("planned_date")
        detector.planned_time_col = profile.column("planned_time")
        detector.actual_date_col = profile.column("actual_date")
        detector.actual_time_col = profile.column("actual_time")
        detector.duration_col = profile.column("duration")
        detector.duration_unit = profile.duration
        detector.performer_col = profile.column("performer")
        detector.customer_col = profile.column("customer")
        detector.header_row = profile.header_row

    def _populate_row(self, sr: StructuredMeetingRow, row: list[str], detector: TableSchemaDetector) -> None:
        if detector.subject_col is not None and detector.subject_col < len(row):
            raw_subject = row[detector.subject_col]
            subject, desc_lines = split_subject_and_description(raw_subject)
            sr.subject = subject
            sr.description_lines = desc_lines

        if detector.agreed_date_col is not None and detector.agreed_date_col < len(row):
            sr.agreed_date = normalize_date_value(row[detector.agreed_date_col])
        if detector.agreed_time_col is not None and detector.agreed_time_col < len(row):
            sr.agreed_time = normalize_time_value(row[detector.agreed_time_col])

        if detector.planned_date_col is not None and detector.planned_date_col < len(row):
            sr.planned_date = normalize_date_value(row[detector.planned_date_col])
        if detector.planned_time_col is not None and detector.planned_time_col < len(row):
            sr.planned_time = normalize_time_value(row[detector.planned_time_col])

        if detector.actual_date_col is not None and detector.actual_date_col < len(row):
            sr.actual_date = normalize_date_value(row[detector.actual_date_col])
        if detector.actual_time_col is not None and detector.actual_time_col < len(row):
            sr.actual_time = normalize_time_value(row[detector.actual_time_col])

        if detector.duration_col is not None and detector.duration_col < len(row):
            dur_cell = row[detector.duration_col]
            unit = self.numeric_duration_unit
            if unit == "auto" and detector.duration_unit:
                unit = detector.duration_unit
            parsed = self._parse_duration_cell(dur_cell, unit=unit)
            sr.duration_minutes = parsed
            sr.duration_source = "source_column"
            sr.duration_confirmed = parsed is not None
            sr.raw_cells["_duration_diagnostic"] = {
                "raw": dur_cell,
                "unit": unit,
                "unit_source": "profile" if self.used_profile else ("header" if detector.duration_unit else self.numeric_duration_unit),
                "minutes": parsed,
            }

        if detector.performer_col is not None and detector.performer_col < len(row):
            sr.performer_names = parse_names(row[detector.performer_col])
        if detector.customer_col is not None and detector.customer_col < len(row):
            sr.customer_names = parse_names(row[detector.customer_col])

        for col in detector.link_cols:
            if col < len(row) and row[col]:
                sr.links.append(row[col])

        tz_from_col = False
        if detector.agreed_time_col is not None and detector.agreed_time_col in detector.column_timezones:
            sr.timezone = detector.column_timezones[detector.agreed_time_col]
            sr.timezone_source = "source_column"
            sr.timezone_confirmed = True
            tz_from_col = True
        elif detector.header_timezone:
            sr.timezone = detector.header_timezone
            sr.timezone_source = "source_column"
            sr.timezone_confirmed = True
            tz_from_col = True

        for col_idx, cell in enumerate(row):
            tz = detect_timezone_from_text(cell)
            if tz:
                sr.timezone = tz
                sr.timezone_source = "source_column"
                sr.timezone_confirmed = True
                tz_from_col = True
                break

        if not tz_from_col:
            import os
            fallback_tz = os.environ.get("DEFAULT_TIMEZONE", "Asia/Yekaterinburg")
            sr.timezone = fallback_tz
            sr.timezone_source = "default_value"
            sr.timezone_confirmed = False

    def _parse_duration_cell(self, value: str, unit: str = "auto") -> int | None:
        if not value or not value.strip():
            return None
        cleaned = value.strip().replace("\u00a0", " ")
        m = re.match(r"^(\d+)\s*мин(?:ут)?$", cleaned, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.match(r"^(\d+)\s*час(?:а|ов)?$", cleaned, re.IGNORECASE)
        if m:
            return int(m.group(1)) * 60
        m = re.match(r"^(\d+):(\d{2}):(\d{2})$", cleaned)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
        m = re.match(r"^(\d+):(\d{2})$", cleaned)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
        m = re.match(r"^(\d+)[,.](\d+)\s*час(?:а|ов)?$", cleaned, re.IGNORECASE)
        if m:
            hours = int(m.group(1))
            frac_str = m.group(2)
            minutes = int(float(f"0.{frac_str}") * 60)
            return hours * 60 + minutes

        # bare decimal number, e.g. "1,5" -> 1.5 hours (only when unit is hours)
        m = re.match(r"^(\d+)[,.](\d+)$", cleaned)
        if m and unit == "hours":
            hours = int(m.group(1))
            frac_minutes = int(float(f"0.{m.group(2)}") * 60)
            return hours * 60 + frac_minutes

        try:
            bare = int(cleaned)
        except ValueError:
            return None

        if unit == "hours":
            return bare * 60
        elif unit == "minutes":
            return bare
        else:
            _log.warning(
                "Duration value '%s' was parsed as a bare number (%d) with numeric_duration_unit='auto' — "
                "interpreting as minutes. Set DURATION_NUMERIC_UNIT=hours in Stage 1 if values represent hours.",
                value, bare,
            )
            return bare

    def _row_to_candidate(
        self, sr: StructuredMeetingRow, counter: int, sheet_name: str
    ) -> MeetingCandidate | None:

        if self.date_policy == MeetingDatePolicy.AGREED_ONLY:
            if not sr.agreed_date or not sr.agreed_time:
                return None
            start_date = sr.agreed_date
            start_time = sr.agreed_time
            evidence = [
                {"field": "date", "method": "agreed_date", "source": f"{sr.sheet_name}:R{sr.row_number}C{self._col_str_from_row(sr)}"},
                {"field": "time", "method": "agreed_time", "source": f"{sr.sheet_name}:R{sr.row_number}C{self._col_str_from_row(sr)}"},
            ]
        elif self.date_policy == MeetingDatePolicy.PLANNED_ONLY:
            if not sr.planned_date or not sr.planned_time:
                return None
            start_date = sr.planned_date
            start_time = sr.planned_time
            evidence = [
                {"field": "date", "method": "planned_date", "source": f"{sr.sheet_name}:R{sr.row_number}"},
                {"field": "time", "method": "planned_time", "source": f"{sr.sheet_name}:R{sr.row_number}"},
            ]
        elif self.date_policy == MeetingDatePolicy.AGREED_THEN_PLANNED:
            if sr.agreed_date and sr.agreed_time:
                start_date = sr.agreed_date
                start_time = sr.agreed_time
                evidence = [{"field": "date", "method": "agreed_date"}]
            elif sr.planned_date and sr.planned_time:
                start_date = sr.planned_date
                start_time = sr.planned_time
                evidence = [{"field": "date", "method": "planned_date (agreed missing)"}]
            else:
                return None
        else:
            return None

        candidate_id = f"SRC-EVT-{counter + 1:03d}"

        if sr.duration_minutes is not None and "_duration_diagnostic" in sr.raw_cells:
            diag = sr.raw_cells.pop("_duration_diagnostic")
            evidence.append({
                "field": "duration",
                "method": "source_column",
                "source": f"{sr.sheet_name}:R{sr.row_number}",
                "raw": diag["raw"],
                "unit": diag["unit"],
                "unit_source": diag["unit_source"],
                "minutes": diag["minutes"],
            })

        return MeetingCandidate(
            candidate_id=candidate_id,
            subject=sr.subject,
            description_base="\n".join(sr.description_lines),
            start_date=start_date,
            start_time=start_time,
            timezone=sr.timezone,
            timezone_source=sr.timezone_source,
            timezone_confirmed=sr.timezone_confirmed,
            duration_minutes=sr.duration_minutes,
            duration_source=sr.duration_source,
            duration_confirmed=sr.duration_confirmed,
            performer_names=sr.performer_names,
            customer_names=sr.customer_names,
            location=sr.location,
            online_meeting_url=sr.links[0] if sr.links else None,
            confidence=0.9 if sr.agreed_date and sr.agreed_time else 0.7,
            evidence=evidence,
            reasoning=[f"Извлечено из структурированной таблицы, лист '{sr.sheet_name}', строка {sr.row_number}"],
            warnings=[],
            links=sr.links,
            sheet_name=sr.sheet_name,
            row_number=sr.row_number,
        )

    @staticmethod
    def _col_str_from_row(sr: StructuredMeetingRow) -> str:
        return ""

    @staticmethod
    def _cell_to_dict(row: list[str]) -> dict[str, str]:
        return {str(i): cell for i, cell in enumerate(row)}
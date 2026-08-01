from __future__ import annotations

from calendar_planner.domain.models import MeetingCandidate, StructuredMeetingRow, ExtractedSource
from calendar_planner.domain.enums import MeetingDatePolicy
from calendar_planner.source.schema_detector import (
    TableSchemaDetector,
    parse_names,
    split_subject_and_description,
    detect_timezone_from_text,
)
from calendar_planner.extraction.datetime_normalizer import normalize_date_value, normalize_time_value


class StructuredExtractor:
    def __init__(self, date_policy: MeetingDatePolicy = MeetingDatePolicy.AGREED_ONLY):
        self.date_policy = date_policy
        self.skipped_rows: list[dict] = []

    def extract(self, source: ExtractedSource) -> dict[str, list[MeetingCandidate]]:
        result: dict[str, list[MeetingCandidate]] = {}
        self.skipped_rows = []
        counter = 0

        for sheet_name, sheet_data in source.sheets.items():
            if not sheet_data:
                continue

            detector = TableSchemaDetector()
            detector.detect(sheet_data)

            candidates = []
            start_row = detector.header_row + 1

            for row_idx in range(start_row, len(sheet_data)):
                row = sheet_data[row_idx]
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

        if detector.performer_col is not None and detector.performer_col < len(row):
            sr.performer_names = parse_names(row[detector.performer_col])
        if detector.customer_col is not None and detector.customer_col < len(row):
            sr.customer_names = parse_names(row[detector.customer_col])

        for col in detector.link_cols:
            if col < len(row) and row[col]:
                sr.links.append(row[col])

        if detector.agreed_time_col is not None and detector.agreed_time_col in detector.column_timezones:
            sr.timezone = detector.column_timezones[detector.agreed_time_col]
        elif detector.header_timezone:
            sr.timezone = detector.header_timezone

        for col_idx, cell in enumerate(row):
            tz = detect_timezone_from_text(cell)
            if tz:
                sr.timezone = tz
                break

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

        return MeetingCandidate(
            candidate_id=candidate_id,
            subject=sr.subject,
            description_base="\n".join(sr.description_lines),
            start_date=start_date,
            start_time=start_time,
            timezone=sr.timezone,
            duration_minutes=None,
            duration_source="missing",
            duration_confirmed=False,
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
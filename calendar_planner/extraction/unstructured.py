from __future__ import annotations

import re
from datetime import date, datetime

from calendar_planner.domain.models import MeetingCandidate, ExtractedSource
from calendar_planner.extraction.datetime_normalizer import normalize_date_value, normalize_time_value

MEETING_KEYWORDS = [
    "встреча", "созвон", "демонстрация", "совещание", "рабочая сессия",
    "интервью", "комитет", "защита", "презентация", "review", "demo",
    "meeting", "call", "kickoff", "вебинар",
]

NOT_MEETING_KEYWORDS = [
    "срок задачи", "дата оплаты", "срок отправки", "отменен", "отменена",
    "перенесен на неопределенный срок", "deadline",
]

DATE_PATTERN = re.compile(
    r"(\d{1,2}[./]\d{1,2}[./]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})",
)
TIME_PATTERN = re.compile(
    r"(\d{1,2}:\d{2})",
)


class UnstructuredExtractor:
    def extract(self, source: ExtractedSource) -> list[MeetingCandidate]:
        candidates: list[MeetingCandidate] = []
        counter = 0

        full_text = source.raw_text
        if not full_text:
            for sheet_data in source.sheets.values():
                for row in sheet_data:
                    full_text += " ".join(row) + "\n"

        blocks = self._split_into_blocks(full_text)

        for block in blocks:
            if not self._is_likely_meeting(block):
                continue
            if self._is_not_meeting(block):
                continue

            candidate = self._parse_block(block, counter)
            if candidate:
                candidates.append(candidate)
                counter += 1

        return candidates

    def _split_into_blocks(self, text: str) -> list[str]:
        blocks = re.split(r"\n\s*\n|\n[-–•*]\s", text)
        return [b.strip() for b in blocks if len(b.strip()) > 10]

    def _is_likely_meeting(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in MEETING_KEYWORDS)

    def _is_not_meeting(self, text: str) -> bool:
        text_lower = text.lower()
        return any(kw in text_lower for kw in NOT_MEETING_KEYWORDS)

    def _parse_block(self, text: str, counter: int) -> MeetingCandidate | None:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return None

        subject = lines[0][:200]
        description_base = "\n".join(lines[1:]) if len(lines) > 1 else ""

        date_match = DATE_PATTERN.search(text)
        time_match = TIME_PATTERN.search(text)

        start_date = normalize_date_value(date_match.group(1)) if date_match else None
        start_time = normalize_time_value(time_match.group(1)) if time_match else None

        candidate_id = f"UNS-EVT-{counter + 1:03d}"

        return MeetingCandidate(
            candidate_id=candidate_id,
            subject=subject,
            description_base=description_base,
            start_date=start_date,
            start_time=start_time,
            timezone=None,
            duration_minutes=None,
            duration_source="missing",
            duration_confirmed=False,
            confidence=0.6,
            evidence=[{"source": "unstructured_text", "fragment": text[:500]}],
            reasoning=["Извлечено из неструктурированного текста"],
            warnings=[] if start_date and start_time else ["Дата/время не определены однозначно"],
            included=bool(start_date and start_time),
            inclusion_reason="" if start_date and start_time else "Неструктурированный источник: требуется проверка даты и времени",
        )
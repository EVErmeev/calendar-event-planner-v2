from __future__ import annotations

import re
from difflib import SequenceMatcher

TIMEZONE_ALIASES: dict[str, str] = {
    "екб": "Asia/Yekaterinburg",
    "ekb": "Asia/Yekaterinburg",
    "екатеринбург": "Asia/Yekaterinburg",
    "yekaterinburg": "Asia/Yekaterinburg",
    "мск": "Europe/Moscow",
    "msk": "Europe/Moscow",
    "москва": "Europe/Moscow",
    "moscow": "Europe/Moscow",
    "спб": "Europe/Moscow",
    "spb": "Europe/Moscow",
    "санкт-петербург": "Europe/Moscow",
    "saint petersburg": "Europe/Moscow",
    "нск": "Asia/Novosibirsk",
    "nsk": "Asia/Novosibirsk",
    "новосибирск": "Asia/Novosibirsk",
    "novosibirsk": "Asia/Novosibirsk",
    "крд": "Europe/Moscow",
    "krd": "Europe/Moscow",
    "краснодар": "Europe/Moscow",
    "krasnodar": "Europe/Moscow",
}

SUBJECT_PATTERNS = [
    re.compile(r"тема|блок|название|встреча|созвон|демонстрация|совещание|subject|topic", re.IGNORECASE),
]

AGREED_DATE_PATTERNS = [
    re.compile(r"согласованн(ая|ое).*(дат|числ)", re.IGNORECASE),
    re.compile(r"утвержденн(ая|ое).*(дат|числ)", re.IGNORECASE),
    re.compile(r"подтвержденн(ая|ое).*(дат|числ)", re.IGNORECASE),
    re.compile(r"согл\.?\s*дат", re.IGNORECASE),
]

AGREED_TIME_PATTERNS = [
    re.compile(r"согласованн(ая|ое).*врем", re.IGNORECASE),
    re.compile(r"утвержденн(ая|ое).*врем", re.IGNORECASE),
    re.compile(r"подтвержденн(ая|ое).*врем", re.IGNORECASE),
    re.compile(r"согл\.?\s*врем", re.IGNORECASE),
]

PLANNED_DATE_PATTERNS = [
    re.compile(r"план(овая|овое).*(дат|числ)", re.IGNORECASE),
    re.compile(r"планируем(ая|ое).*(дат|числ)", re.IGNORECASE),
    re.compile(r"план\.?\s*дат", re.IGNORECASE),
]

PLANNED_TIME_PATTERNS = [
    re.compile(r"план(овая|овое).*врем", re.IGNORECASE),
    re.compile(r"планируем(ая|ое).*врем", re.IGNORECASE),
    re.compile(r"план\.?\s*врем", re.IGNORECASE),
]

ACTUAL_DATE_PATTERNS = [
    re.compile(r"фактическ(ая|ое).*(дат|числ)", re.IGNORECASE),
    re.compile(r"факт\.?\s*дат", re.IGNORECASE),
]

ACTUAL_TIME_PATTERNS = [
    re.compile(r"фактическ(ая|ое).*врем", re.IGNORECASE),
    re.compile(r"факт\.?\s*врем", re.IGNORECASE),
]

PERFORMER_PATTERNS = [
    re.compile(r"исполнител|performer|состав\s+команды\s+исполнител", re.IGNORECASE),
]

CUSTOMER_PATTERNS = [
    re.compile(r"заказчик|customer|состав\s+команды\s+заказчик", re.IGNORECASE),
]

DURATION_PATTERNS = [
    re.compile(r"длительн", re.IGNORECASE),  # covers "длительность", "Длительнось" (typo)
    re.compile(r"продолжительность", re.IGNORECASE),
    re.compile(r"duration", re.IGNORECASE),
    re.compile(r"минут", re.IGNORECASE),
]

TIMEZONE_PATTERNS = [
    re.compile(r"(?:мск|msk|екб|ekb|екатеринбург|yekaterinburg|нск|nsk|крд|krd)", re.IGNORECASE),
    re.compile(r"(?:часовой\s*пояс|timezone|tz)", re.IGNORECASE),
]


def normalize_header(text: str) -> str:
    text = text.replace("ё", "е").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\r\n]+", " ", text)
    return text


def header_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_header(a), normalize_header(b)).ratio()


def detect_timezone_from_text(text: str) -> str | None:
    text_lower = text.lower()
    for alias, tz in TIMEZONE_ALIASES.items():
        if alias in text_lower:
            return tz
    return None


class TableSchemaDetector:
    def __init__(self):
        self.subject_col: int | None = None
        self.agreed_date_col: int | None = None
        self.agreed_time_col: int | None = None
        self.planned_date_col: int | None = None
        self.planned_time_col: int | None = None
        self.actual_date_col: int | None = None
        self.actual_time_col: int | None = None
        self.duration_col: int | None = None
        self.duration_unit: str | None = None
        self.performer_col: int | None = None
        self.customer_col: int | None = None
        self.link_cols: list[int] = []
        self.description_cols: list[int] = []
        self.header_timezone: str | None = None
        self.column_timezones: dict[int, str] = {}
        self.header_row: int = 0

    def detect(self, sheet_data: list[list[str]]) -> None:
        if len(sheet_data) < 2:
            return

        for row_idx, row in enumerate(sheet_data):
            for col_idx, cell in enumerate(row):
                normalized = normalize_header(cell)
                if not normalized:
                    continue

                tz = detect_timezone_from_text(cell)
                if tz:
                    self._update_timezone_for_col(tz, col_idx, normalized)

                if self.subject_col is None and any(p.search(normalized) for p in SUBJECT_PATTERNS) and not any(
                    p.search(normalized) for p in AGREED_DATE_PATTERNS + AGREED_TIME_PATTERNS
                ):
                    self.subject_col = col_idx

                if self.agreed_date_col is None and any(p.search(normalized) for p in AGREED_DATE_PATTERNS):
                    self.agreed_date_col = col_idx
                    tz_date = detect_timezone_from_text(cell)
                    if tz_date:
                        self.header_timezone = tz_date

                if self.agreed_time_col is None and any(p.search(normalized) for p in AGREED_TIME_PATTERNS):
                    self.agreed_time_col = col_idx
                    tz_time = detect_timezone_from_text(cell)
                    if tz_time and not self.header_timezone:
                        self.header_timezone = tz_time

                if self.planned_date_col is None and any(p.search(normalized) for p in PLANNED_DATE_PATTERNS):
                    self.planned_date_col = col_idx

                if self.planned_time_col is None and any(p.search(normalized) for p in PLANNED_TIME_PATTERNS):
                    self.planned_time_col = col_idx

                if self.actual_date_col is None and any(p.search(normalized) for p in ACTUAL_DATE_PATTERNS):
                    self.actual_date_col = col_idx

                if self.actual_time_col is None and any(p.search(normalized) for p in ACTUAL_TIME_PATTERNS):
                    self.actual_time_col = col_idx

                if self.duration_col is None and any(p.search(normalized) for p in DURATION_PATTERNS) and not any(
                    p.search(normalized) for p in AGREED_TIME_PATTERNS + PLANNED_TIME_PATTERNS + ACTUAL_TIME_PATTERNS
                ):
                    self.duration_col = col_idx
                    if self.duration_unit is None:
                        if re.search(r"час|\bч\b|hour", normalized):
                            self.duration_unit = "hours"
                        elif "мин" in normalized:
                            self.duration_unit = "minutes"

                if self.performer_col is None and any(p.search(normalized) for p in PERFORMER_PATTERNS):
                    self.performer_col = col_idx

                if self.customer_col is None and any(p.search(normalized) for p in CUSTOMER_PATTERNS):
                    self.customer_col = col_idx

                link_keywords = ["ссылка", "линк", "link", "url", "подключение", "connect"]
                if any(kw in normalized for kw in link_keywords) and col_idx not in self.link_cols:
                    self.link_cols.append(col_idx)

                desc_keywords = ["описание", "примечание", "коммент", "description", "note", "comment"]
                if any(kw in normalized for kw in desc_keywords) and col_idx not in self.description_cols:
                    self.description_cols.append(col_idx)

            if self.subject_col is not None or self._has_enough_columns():
                self.header_row = row_idx
                break

    def _update_timezone_for_col(self, tz: str, col_idx: int, normalized_header: str) -> None:
        self.column_timezones[col_idx] = tz

    def _has_enough_columns(self) -> bool:
        found = sum(1 for x in [
            self.subject_col, self.agreed_date_col, self.agreed_time_col,
            self.planned_date_col, self.planned_time_col,
            self.performer_col, self.customer_col,
        ] if x is not None)
        return found >= 3

    def to_dict(self) -> dict:
        return {
            "subject_col": self.subject_col,
            "agreed_date_col": self.agreed_date_col,
            "agreed_time_col": self.agreed_time_col,
            "planned_date_col": self.planned_date_col,
            "planned_time_col": self.planned_time_col,
            "actual_date_col": self.actual_date_col,
            "actual_time_col": self.actual_time_col,
            "duration_col": self.duration_col,
            "duration_unit": self.duration_unit,
            "performer_col": self.performer_col,
            "customer_col": self.customer_col,
            "link_cols": self.link_cols,
            "description_cols": self.description_cols,
            "header_timezone": self.header_timezone,
            "column_timezones": self.column_timezones,
            "header_row": self.header_row,
        }


def parse_names(cell_value: str) -> list[str]:
    if not cell_value:
        return []
    names = re.split(r"[,;/]\s*", cell_value)
    return [n.strip() for n in names if n.strip()]


def split_subject_and_description(subject_text: str) -> tuple[str, list[str]]:
    lines = [l.strip() for l in subject_text.split("\n") if l.strip()]
    if not lines:
        return "", []
    if len(lines) == 1:
        return lines[0], []
    return lines[0], lines[1:]
from __future__ import annotations

import re
from difflib import SequenceMatcher

from calendar_planner.domain.models import (
    ContactRecord,
    ExtractedSource,
    ParticipantSide,
)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


class ContactIndex:
    def __init__(self):
        self.contacts: list[ContactRecord] = []

    def build_from_source(self, source: ExtractedSource, performer_domain: str = "1bit.ru") -> None:
        self.contacts = []
        full_text = source.raw_text

        if not full_text:
            parts = []
            for sheet_data in source.sheets.values():
                for row in sheet_data:
                    parts.append(" ".join(row))
            full_text = "\n".join(parts)

        emails = EMAIL_RE.findall(full_text)
        for email in emails:
            self.contacts.append(ContactRecord(
                full_name="",
                surname="",
                email=email,
                organization=performer_domain if performer_domain in email else "",
                source_location="extracted_from_text",
            ))

        for sheet_name, sheet_data in source.sheets.items():
            schema = self._detect_contact_schema(sheet_data)
            has_contact_headers = schema["full_name"] >= 0 or schema["email"] >= 0

            for row_idx, row in enumerate(sheet_data):
                if has_contact_headers and row_idx == 0:
                    continue

                row_text = " ".join(row)
                for email in EMAIL_RE.findall(row_text):
                    full_name = ""
                    if schema["full_name"] >= 0 and schema["full_name"] < len(row):
                        candidate = row[schema["full_name"]]
                        if candidate and "@" not in candidate:
                            full_name = candidate

                    if not full_name:
                        full_name = row[0] if row and row[0] and "@" not in row[0] else ""

                    phone = ""
                    if schema["phone"] >= 0 and schema["phone"] < len(row):
                        phone = row[schema["phone"]] if row[schema["phone"]] else ""

                    organization = ""
                    if schema["organization"] >= 0 and schema["organization"] < len(row):
                        organization = row[schema["organization"]] if row[schema["organization"]] else ""

                    self.contacts.append(ContactRecord(
                        full_name=full_name,
                        surname=self._extract_surname(row),
                        email=email,
                        phone=phone,
                        organization=organization,
                        source_location=f"{sheet_name}:R{row_idx + 1}",
                    ))

        for key, url in source.hyperlinks.items():
            if url.startswith("mailto:"):
                email = url[7:].split("?")[0]
                self.contacts.append(ContactRecord(
                    full_name="",
                    surname="",
                    email=email,
                    source_location=f"hyperlink:{key}",
                ))

    def _extract_surname(self, row: list[str]) -> str:
        for cell in row:
            if cell and " " in cell and "@" not in cell:
                parts = cell.split()
                if len(parts) >= 1:
                    return parts[0]
        return ""

    @staticmethod
    def _detect_contact_schema(sheet_data: list[list[str]]) -> dict[str, int]:
        mapping = {"full_name": -1, "email": -1, "phone": -1, "organization": -1}

        name_keywords = ["фио", "ф.и.о.", "fio", "full name", "имя", "name"]
        email_keywords = ["email", "e-mail", "почта", "mail"]
        phone_keywords = ["телефон", "phone", "tel", "мобильный"]
        org_keywords = ["организация", "organization", "компания", "company", "орг"]

        for row in sheet_data[:5]:
            for col_idx, cell in enumerate(row):
                if not cell:
                    continue
                cell_lower = str(cell).lower().strip()
                if mapping["full_name"] == -1 and any(kw in cell_lower for kw in name_keywords):
                    mapping["full_name"] = col_idx
                if mapping["email"] == -1 and any(kw in cell_lower for kw in email_keywords):
                    mapping["email"] = col_idx
                if mapping["phone"] == -1 and any(kw in cell_lower for kw in phone_keywords):
                    mapping["phone"] = col_idx
                if mapping["organization"] == -1 and any(kw in cell_lower for kw in org_keywords):
                    mapping["organization"] = col_idx

        return mapping

    def find_by_name(self, name: str, organization: str | None = None) -> list[ContactRecord]:
        results = []
        name_lower = name.lower()
        for contact in self.contacts:
            if (name_lower in contact.full_name.lower() or name_lower in contact.surname.lower()) and (
                organization is None or (contact.organization and organization in contact.organization)
            ):
                results.append(contact)
        return results

    def find_by_email(self, email: str) -> list[ContactRecord]:
        return [c for c in self.contacts if c.email and c.email.lower() == email.lower()]

    def find_all_for_side(self, side: ParticipantSide) -> list[ContactRecord]:
        return [c for c in self.contacts if c.side == side]

    def to_dict_list(self) -> list[dict]:
        return [c.to_dict() for c in self.contacts]


def fuzzy_match_surname(surname: str, full_name: str, threshold: float = 0.85) -> float:
    surname_lower = surname.lower()
    name_lower = full_name.lower()
    score = SequenceMatcher(None, surname_lower, name_lower).ratio()
    if score < threshold:
        words = name_lower.split()
        for word in words:
            word_score = SequenceMatcher(None, surname_lower, word).ratio()
            score = max(score, word_score)
    return score
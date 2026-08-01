from __future__ import annotations

from calendar_planner.domain.models import (
    ParticipantRole,
    ParticipantSide,
    ResolvedParticipant,
)


class NameMatcher:
    def __init__(self, directory_gateway, fuzzy_threshold: float = 0.85):
        self.directory = directory_gateway
        self.fuzzy_threshold = fuzzy_threshold

    def match_performer(self, name: str, default_role: ParticipantRole = ParticipantRole.REQUIRED) -> ResolvedParticipant | None:
        if not self.directory.is_available():
            return None

        results = self.directory.search(name)

        if len(results) == 1:
            emp = results[0]
            return ResolvedParticipant(
                full_name=emp["full_name"],
                email=emp.get("email"),
                side=ParticipantSide.PERFORMER,
                role=default_role,
                source_name=name,
                match_source="directory_exact",
                organization=emp.get("organization", "Первый БИТ"),
            )

        if len(results) == 0:
            results = self.directory.search_by_surname(name) if hasattr(self.directory, "search_by_surname") else []
            if len(results) == 1:
                emp = results[0]
                return ResolvedParticipant(
                    full_name=emp["full_name"],
                    email=emp.get("email"),
                    side=ParticipantSide.PERFORMER,
                    role=default_role,
                    source_name=name,
                    match_source="directory_surname",
                    organization=emp.get("organization", "Первый БИТ"),
                )
            if len(results) >= 2:
                scored = [(emp, self._score_match(name, emp)) for emp in results]
                scored.sort(key=lambda x: x[1], reverse=True)
                best_match = scored[0]
                return ResolvedParticipant(
                    full_name=best_match[0].get("full_name", ""),
                    email=best_match[0].get("email"),
                    side=ParticipantSide.PERFORMER,
                    role=default_role,
                    source_name=name,
                    match_source="directory_surname_best",
                    confidence=best_match[1],
                    organization=best_match[0].get("organization", "Первый БИТ"),
                    is_fuzzy_match=True,
                    fuzzy_score=best_match[1],
                )

        if len(results) >= 2:
            return None

        return None

    def match_performer_with_options(
        self, name: str, default_role: ParticipantRole = ParticipantRole.REQUIRED
    ) -> tuple[ResolvedParticipant | None, list[dict]]:
        if not self.directory.is_available():
            return None, []

        results = self.directory.search(name)

        if len(results) == 1:
            emp = results[0]
            return ResolvedParticipant(
                full_name=emp["full_name"],
                email=emp.get("email"),
                side=ParticipantSide.PERFORMER,
                role=default_role,
                source_name=name,
                match_source="directory_exact",
                organization=emp.get("organization", "Первый БИТ"),
            ), []

        if len(results) == 0:
            if hasattr(self.directory, "search_by_surname"):
                surname_results = self.directory.search_by_surname(name)
            else:
                surname_results = []
            if len(surname_results) == 1:
                emp = surname_results[0]
                return ResolvedParticipant(
                    full_name=emp["full_name"],
                    email=emp.get("email"),
                    side=ParticipantSide.PERFORMER,
                    role=default_role,
                    source_name=name,
                    match_source="directory_surname",
                    organization=emp.get("organization", "Первый БИТ"),
                ), []
            if len(surname_results) >= 2:
                scored = [(emp, self._score_match(name, emp)) for emp in surname_results]
                scored.sort(key=lambda x: x[1], reverse=True)
                options = [
                    {
                        "full_name": emp["full_name"],
                        "email": emp.get("email"),
                        "organization": emp.get("organization", "Первый БИТ"),
                        "score": score,
                    }
                    for emp, score in scored
                ]
                return None, options
            return None, []

        scored = [(emp, self._score_match(name, emp)) for emp in results]
        scored.sort(key=lambda x: x[1], reverse=True)
        options = [
            {
                "full_name": emp["full_name"],
                "email": emp.get("email"),
                "organization": emp.get("organization", "Первый БИТ"),
                "score": score,
            }
            for emp, score in scored
        ]
        return None, options

    def match_customer_from_contacts(self, name: str, contact_index) -> ResolvedParticipant | None:
        contacts = contact_index.find_by_name(name)

        if len(contacts) == 1:
            c = contacts[0]
            return ResolvedParticipant(
                full_name=c.full_name or name,
                email=c.email,
                side=ParticipantSide.CUSTOMER,
                role=ParticipantRole.REQUIRED,
                source_name=name,
                match_source="contact_index_exact",
                organization=c.organization,
            )

        if len(contacts) == 0:
            return ResolvedParticipant(
                full_name=name,
                email=None,
                side=ParticipantSide.CUSTOMER,
                role=ParticipantRole.REQUIRED,
                source_name=name,
                match_source="name_only_no_email",
                confidence=0.3,
            )

        return None

    @staticmethod
    def _score_match(name: str, employee: dict) -> float:
        from difflib import SequenceMatcher
        name_lower = name.lower()
        full = employee.get("full_name", "").lower()
        surname = employee.get("surname", "").lower()
        score = SequenceMatcher(None, name_lower, full).ratio()
        if surname and surname in name_lower:
            score = max(score, 0.9)
        return score
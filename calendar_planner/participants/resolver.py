from __future__ import annotations

from calendar_planner.domain.models import (
    MeetingCandidate,
    CandidateParticipants,
    ResolvedParticipant,
    UnresolvedParticipant,
    ParticipantSide,
    ParticipantRole,
    ExtractedSource,
)
from calendar_planner.participants.matcher import NameMatcher
from calendar_planner.participants.contact_index import ContactIndex


class ParticipantResolver:
    def __init__(
        self,
        directory_gateway=None,
        performer_domain: str = "1bit.ru",
        fuzzy_threshold: float = 0.85,
    ):
        self.directory = directory_gateway
        self.performer_domain = performer_domain
        self.fuzzy_threshold = fuzzy_threshold
        self.name_matcher = NameMatcher(directory_gateway, fuzzy_threshold)

    def resolve(
        self,
        candidates: list[MeetingCandidate],
        source: ExtractedSource,
    ) -> list[CandidateParticipants]:
        contact_index = ContactIndex()
        contact_index.build_from_source(source, performer_domain=self.performer_domain)

        results: list[CandidateParticipants] = []

        for candidate in candidates:
            cp = CandidateParticipants(candidate_id=candidate.candidate_id)

            for name in candidate.performer_names:
                matched = self.name_matcher.match_performer(name)
                if matched:
                    matched.role = ParticipantRole.REQUIRED
                    cp.performer.append(matched)
                elif name.strip():
                    employee_results = self.directory.search(name) if self.directory and self.directory.is_available() else []
                    cp.unresolved.append(UnresolvedParticipant(
                        source_name=name,
                        side=ParticipantSide.PERFORMER,
                        reason="Не найдено в каталоге" if not employee_results else "Несколько вариантов",
                        possible_matches=employee_results[:5],
                    ))

            for name in candidate.customer_names:
                customer_contacts = contact_index.find_by_name(name)
                contacts_without_performer_domain = [
                    c for c in customer_contacts
                    if not c.email or self.performer_domain not in (c.email or "")
                ]

                if len(contacts_without_performer_domain) >= 1:
                    c = contacts_without_performer_domain[0]
                    resolved = ResolvedParticipant(
                        full_name=c.full_name or name,
                        email=c.email,
                        side=ParticipantSide.CUSTOMER,
                        role=ParticipantRole.REQUIRED,
                        source_name=name,
                        match_source="contact_index",
                        organization=c.organization,
                    )
                    cp.customer.append(resolved)
                elif len(customer_contacts) > 0:
                    cp.unresolved.append(UnresolvedParticipant(
                        source_name=name,
                        side=ParticipantSide.CUSTOMER,
                        reason="Найден, но email совпадает с доменом Исполнителя",
                        possible_matches=[{"full_name": c.full_name or name, "email": c.email} for c in customer_contacts],
                    ))
                elif name.strip():
                    cp.customer.append(ResolvedParticipant(
                        full_name=name,
                        email=None,
                        side=ParticipantSide.CUSTOMER,
                        role=ParticipantRole.REQUIRED,
                        source_name=name,
                        match_source="name_only_no_contact",
                        confidence=0.3,
                    ))

            results.append(cp)

        return results
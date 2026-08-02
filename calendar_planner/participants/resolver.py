from __future__ import annotations

from calendar_planner.domain.models import (
    CandidateParticipants,
    ExtractedSource,
    MeetingCandidate,
    ParticipantRole,
    ParticipantSide,
    ResolvedParticipant,
    UnresolvedParticipant,
)
from calendar_planner.participants.contact_index import (
    ContactIndex,
    fuzzy_match_surname,
)
from calendar_planner.participants.matcher import NameMatcher


class ParticipantResolver:
    def __init__(
        self,
        directory_gateway=None,
        performer_domains: list[str] | None = None,
        fuzzy_threshold: float = 0.85,
    ):
        self.directory = directory_gateway
        self.performer_domains = performer_domains or ["1bit.ru"]
        self.fuzzy_threshold = fuzzy_threshold
        self.name_matcher = NameMatcher(directory_gateway, fuzzy_threshold)

    def resolve(
        self,
        candidates: list[MeetingCandidate],
        source: ExtractedSource,
    ) -> list[CandidateParticipants]:
        contact_index = ContactIndex()
        contact_index.build_from_source(source, performer_domain=self.performer_domains[0])

        results: list[CandidateParticipants] = []

        for candidate in candidates:
            cp = CandidateParticipants(candidate_id=candidate.candidate_id)

            for name in candidate.performer_names:
                matched, options = self.name_matcher.match_performer_with_options(name)
                if matched:
                    matched.role = ParticipantRole.REQUIRED
                    cp.performer.append(matched)
                elif options:
                    cp.unresolved.append(UnresolvedParticipant(
                        source_name=name,
                        side=ParticipantSide.PERFORMER,
                        reason="Несколько вариантов в каталоге",
                        possible_matches=options[:5],
                    ))
                elif name.strip():
                    cp.unresolved.append(UnresolvedParticipant(
                        source_name=name,
                        side=ParticipantSide.PERFORMER,
                        reason="Не найдено в каталоге",
                        possible_matches=[],
                    ))

            for name in candidate.customer_names:
                customer_contacts = contact_index.find_by_name(name)
                contacts_without_performer_domain = [
                    c for c in customer_contacts
                    if not c.email or not any(d in (c.email or "") for d in self.performer_domains)
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
                    fuzzy_candidates: list[tuple] = []
                    for contact in contact_index.contacts:
                        if not contact.full_name:
                            continue
                        score = fuzzy_match_surname(name, contact.full_name, self.fuzzy_threshold)
                        if score >= self.fuzzy_threshold:
                            fuzzy_candidates.append((contact, score))

                    if len(fuzzy_candidates) == 1:
                        contact, score = fuzzy_candidates[0]
                        cp.customer.append(ResolvedParticipant(
                            full_name=contact.full_name or name,
                            email=contact.email,
                            side=ParticipantSide.CUSTOMER,
                            role=ParticipantRole.REQUIRED,
                            source_name=name,
                            match_source="fuzzy_match",
                            confidence=score,
                            organization=contact.organization,
                            is_fuzzy_match=True,
                            fuzzy_score=score,
                        ))
                    elif len(fuzzy_candidates) > 1:
                        cp.unresolved.append(UnresolvedParticipant(
                            source_name=name,
                            side=ParticipantSide.CUSTOMER,
                            reason="Несколько вариантов fuzzy-совпадения",
                            possible_matches=[
                                {"full_name": c.full_name, "email": c.email, "fuzzy_score": s}
                                for c, s in fuzzy_candidates[:5]
                            ],
                        ))
                    else:
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
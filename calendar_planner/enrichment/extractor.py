from __future__ import annotations

from calendar_planner.domain.models import (
    MeetingCandidate,
    DescriptionItem,
    ExtractedSource,
    DescriptionItemType,
)


class EnrichmentExtractor:
    def extract(
        self,
        candidates: list[MeetingCandidate],
        source: ExtractedSource,
    ) -> dict[str, list[DescriptionItem]]:
        result: dict[str, list[DescriptionItem]] = {}

        for candidate in candidates:
            items: list[DescriptionItem] = []
            item_counter = 0

            if candidate.description_base:
                agenda_lines = [l.strip() for l in candidate.description_base.split("\n") if l.strip()]
                agenda_text = "\n".join(f"{i + 1}. {l}" for i, l in enumerate(agenda_lines))
                item_counter += 1
                items.append(DescriptionItem(
                    item_id=f"ENR-{candidate.candidate_id}-{item_counter:03d}",
                    item_type=DescriptionItemType.AGENDA,
                    title="Повестка",
                    value=agenda_text,
                    source_location=f"{candidate.sheet_name}:R{candidate.row_number}",
                    reasoning="Извлечено из многострочного блока темы",
                    confidence=0.9,
                    candidate_id=candidate.candidate_id,
                ))

            for i, link in enumerate(candidate.links):
                item_counter += 1
                items.append(DescriptionItem(
                    item_id=f"ENR-{candidate.candidate_id}-{item_counter:03d}",
                    item_type=DescriptionItemType.LINK,
                    title=f"Ссылка {i + 1}",
                    value=link,
                    source_location=f"{candidate.sheet_name}:R{candidate.row_number}",
                    reasoning="Найдено в строке встречи",
                    confidence=0.9,
                    candidate_id=candidate.candidate_id,
                ))

            if candidate.location:
                item_counter += 1
                items.append(DescriptionItem(
                    item_id=f"ENR-{candidate.candidate_id}-{item_counter:03d}",
                    item_type=DescriptionItemType.LOCATION,
                    title="Место",
                    value=candidate.location,
                    source_location=f"{candidate.sheet_name}:R{candidate.row_number}",
                    reasoning="Найдено в строке встречи",
                    confidence=0.8,
                    candidate_id=candidate.candidate_id,
                ))

            if candidate.online_meeting_url:
                item_counter += 1
                items.append(DescriptionItem(
                    item_id=f"ENR-{candidate.candidate_id}-{item_counter:03d}",
                    item_type=DescriptionItemType.ONLINE_MEETING_URL,
                    title="Ссылка на встречу",
                    value=candidate.online_meeting_url,
                    source_location=f"{candidate.sheet_name}:R{candidate.row_number}",
                    reasoning="Найдено в строке встречи",
                    confidence=0.9,
                    candidate_id=candidate.candidate_id,
                ))

            self._search_across_source(candidate, source, items, item_counter)

            result[candidate.candidate_id] = items

        return result

    def _search_across_source(
        self,
        candidate: MeetingCandidate,
        source: ExtractedSource,
        items: list[DescriptionItem],
        start_counter: int,
    ) -> None:
        counter = start_counter

        for sheet_name, sheet_data in source.sheets.items():
            if candidate.sheet_name and sheet_name == candidate.sheet_name:
                continue

            for row_idx, row in enumerate(sheet_data):
                row_text = " ".join(row).lower()
                subject_lower = candidate.subject.lower()

                if subject_lower and subject_lower.split(":")[0].strip() in row_text:
                    counter += 1
                    row_value = " ".join(row)
                    if "http://" in row_value or "https://" in row_value:
                        item_type = DescriptionItemType.LINK
                        item_title = f"Ссылка с листа '{sheet_name}'"
                    elif any(keyword in row_text for keyword in ["заметка", "note", "коммент", "примечание", "comment"]):
                        item_type = DescriptionItemType.NOTE
                        item_title = f"Заметка с листа '{sheet_name}'"
                    else:
                        item_type = DescriptionItemType.DOCUMENT
                        item_title = f"Документ с листа '{sheet_name}'"
                    items.append(DescriptionItem(
                        item_id=f"ENR-{candidate.candidate_id}-{counter:03d}",
                        item_type=item_type,
                        title=item_title,
                        value=row_value,
                        source_location=f"{sheet_name}:R{row_idx + 1}",
                        reasoning=f"Связано с темой встречи через '{candidate.subject[:50]}'",
                        confidence=0.5,
                        candidate_id=candidate.candidate_id,
                    ))
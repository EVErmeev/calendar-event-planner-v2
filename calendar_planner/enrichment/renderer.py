from __future__ import annotations

from calendar_planner.domain.models import DescriptionItem, DescriptionItemType


class DescriptionRenderer:
    def render(self, items: list[DescriptionItem], candidate_subject: str = "") -> str:
        sections: dict[str, list[str]] = {
            "Повестка": [],
            "Ссылки": [],
            "Материалы": [],
            "Место": [],
            "Дополнительная информация": [],
        }

        for item in items:
            if not item.included:
                continue

            if item.item_type == DescriptionItemType.AGENDA:
                sections["Повестка"].append(item.value)
            elif item.item_type in (DescriptionItemType.LINK, DescriptionItemType.ONLINE_MEETING_URL):
                sections["Ссылки"].append(f"{item.title}: {item.value}")
            elif item.item_type in (DescriptionItemType.MATERIAL, DescriptionItemType.DOCUMENT):
                sections["Материалы"].append(f"{item.title}: {item.value}")
            elif item.item_type == DescriptionItemType.LOCATION:
                sections["Место"].append(item.value)
            else:
                sections["Дополнительная информация"].append(f"{item.title}: {item.value}")

        parts: list[str] = []
        for section_name, lines in sections.items():
            if lines:
                parts.append(f"--- {section_name} ---")
                parts.extend(lines)
                parts.append("")

        return "\n".join(parts).strip()

    def render_for_candidate(
        self,
        candidate_id: str,
        enrichment_map: dict[str, list[DescriptionItem]],
        candidate_subject: str = "",
    ) -> str:
        items = enrichment_map.get(candidate_id, [])
        return self.render(items, candidate_subject)
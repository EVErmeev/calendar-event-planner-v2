from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DirectoryPerson:
    display_name: str
    email: str = ""
    mailbox_type: str | None = None
    company: str | None = None
    department: str | None = None
    job_title: str | None = None
    source: str = ""
    confidence: float | None = None

    @property
    def full_name(self) -> str:
        return self.display_name

    def to_dict(self) -> dict:
        return {
            "full_name": self.display_name,
            "email": self.email,
            "mailbox_type": self.mailbox_type,
            "company": self.company,
            "department": self.department,
            "job_title": self.job_title,
            "source": self.source,
            "confidence": self.confidence,
        }


@dataclass
class DirectorySearchResult:
    query: str
    status: str = "failed"
    source: str = "unknown"
    people: list[DirectoryPerson] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    correlation_id: str | None = None

    @property
    def count(self) -> int:
        return len(self.people)

    def __iter__(self):
        return iter(self.people)

    def __len__(self):
        return len(self.people)

    def __getitem__(self, idx):
        return self.people[idx]
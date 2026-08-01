from __future__ import annotations

from calendar_planner.domain.models import SourceReference, ExtractedSource
from calendar_planner.source.adapters.file_adapters import (
    TxtSourceAdapter,
    MarkdownSourceAdapter,
    CsvSourceAdapter,
    XlsxSourceAdapter,
    DocxSourceAdapter,
    PdfSourceAdapter,
    HtmlSourceAdapter,
    GoogleSheetsSourceAdapter,
    GoogleDocsSourceAdapter,
    ConfluenceSourceAdapter,
    SharePointSourceAdapter,
)


class SourceAdapterRegistry:
    def __init__(self) -> None:
        self._adapters = [
            GoogleSheetsSourceAdapter(),
            GoogleDocsSourceAdapter(),
            XlsxSourceAdapter(),
            DocxSourceAdapter(),
            PdfSourceAdapter(),
            CsvSourceAdapter(),
            HtmlSourceAdapter(),
            ConfluenceSourceAdapter(),
            SharePointSourceAdapter(),
            MarkdownSourceAdapter(),
            TxtSourceAdapter(),
        ]

    def find_adapter(self, source: SourceReference):
        for adapter in self._adapters:
            if adapter.can_handle(source):
                return adapter
        return None

    def read_source(self, source: SourceReference) -> ExtractedSource:
        adapter = self.find_adapter(source)
        if adapter is None:
            raise ValueError(f"No adapter found for source: {source}")
        return adapter.read(source)


registry = SourceAdapterRegistry()
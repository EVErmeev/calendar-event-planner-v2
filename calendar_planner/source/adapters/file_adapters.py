from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Protocol

from calendar_planner.domain.models import SourceReference, ExtractedSource


class SourceAdapter(Protocol):
    def can_handle(self, source: SourceReference) -> bool: ...
    def read(self, source: SourceReference) -> ExtractedSource: ...


class TxtSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.path and Path(source.path).suffix.lower() in (".txt", ".md", ".markdown"):
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        path = Path(source.path)
        raw_text = path.read_text(encoding="utf-8")
        lines = raw_text.split("\n")
        extracted = ExtractedSource(
            source=source,
            sheets={"Sheet1": [[cell] for cell in lines]},
            raw_text=raw_text,
        )
        return extracted


class MarkdownSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.path and Path(source.path).suffix.lower() in (".md", ".markdown"):
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        path = Path(source.path)
        raw_text = path.read_text(encoding="utf-8")
        lines = raw_text.split("\n")
        extracted = ExtractedSource(
            source=source,
            sheets={"Sheet1": [[cell] for cell in lines]},
            raw_text=raw_text,
        )
        return extracted


class CsvSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.path and Path(source.path).suffix.lower() == ".csv":
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        path = Path(source.path)
        raw_text = path.read_text(encoding="utf-8")
        reader = csv.reader(io.StringIO(raw_text))
        rows = [list(row) for row in reader]
        extracted = ExtractedSource(
            source=source,
            sheets={"Sheet1": rows},
            raw_text=raw_text,
        )
        return extracted


class XlsxSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.path and Path(source.path).suffix.lower() in (".xlsx", ".xlsm"):
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        import openpyxl

        path = Path(source.path)
        wb = openpyxl.load_workbook(path, data_only=True)
        sheets: dict[str, list[list[str]]] = {}
        merged_cells: list[dict] = []
        hyperlinks: dict[str, str] = {}
        notes: dict[str, str] = {}

        metadata = {
            "workbook_timezone": wb.properties.excelBaseDate if hasattr(wb.properties, "excelBaseDate") else None,
            "creator": wb.properties.creator,
            "sheet_names": wb.sheetnames,
        }

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows: list[list[str]] = []
            for row_idx, row in enumerate(ws.iter_rows(), start=1):
                cells: list[str] = []
                for col_idx, cell in enumerate(row, start=1):
                    value = str(cell.value) if cell.value is not None else ""
                    cells.append(value)
                    if cell.hyperlink:
                        key = f"{sheet_name}!{cell.coordinate}"
                        hyperlinks[key] = str(cell.hyperlink.target) if cell.hyperlink.target else ""
                    if cell.comment:
                        key = f"{sheet_name}!{cell.coordinate}"
                        notes[key] = cell.comment.text if cell.comment else ""
                rows.append(cells)

            for merged_range in ws.merged_cells.ranges:
                merged_cells.append({
                    "sheet": sheet_name,
                    "range": str(merged_range),
                    "min_row": merged_range.min_row,
                    "max_row": merged_range.max_row,
                    "min_col": merged_range.min_col,
                    "max_col": merged_range.max_col,
                })

            sheets[sheet_name] = rows

        wb.close()

        extracted = ExtractedSource(
            source=source,
            sheets=sheets,
            raw_text="",
            metadata=metadata,
            merged_cells=merged_cells,
            hyperlinks=hyperlinks,
            notes=notes,
        )
        return extracted


class DocxSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.path and Path(source.path).suffix.lower() == ".docx":
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        import docx

        path = Path(source.path)
        doc = docx.Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs]

        tables_data: list[list[str]] = []
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text for cell in row.cells]
                tables_data.append(row_cells)

        all_rows = [[p] for p in paragraphs]
        if tables_data:
            all_rows = tables_data

        extracted = ExtractedSource(
            source=source,
            sheets={"Document": all_rows},
            raw_text="\n".join(paragraphs),
        )
        return extracted


class PdfSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.path and Path(source.path).suffix.lower() == ".pdf":
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        from PyPDF2 import PdfReader

        path = Path(source.path)
        reader = PdfReader(str(path))
        all_lines: list[list[str]] = []
        full_text_parts: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            full_text_parts.append(text)
            for line in text.split("\n"):
                if line.strip():
                    all_lines.append([line])

        extracted = ExtractedSource(
            source=source,
            sheets={"PDF": all_lines},
            raw_text="\n".join(full_text_parts),
            metadata={"pages": len(reader.pages)},
        )
        return extracted


class HtmlSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.path and Path(source.path).suffix.lower() in (".html", ".htm"):
            return True
        if source.url and source.format == "html":
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        from bs4 import BeautifulSoup

        if source.path:
            path = Path(source.path)
            html_content = path.read_text(encoding="utf-8")
        elif source.url:
            import requests
            resp = requests.get(source.url, timeout=30)
            resp.raise_for_status()
            html_content = resp.text
        else:
            raise ValueError("No path or URL provided for HTML source")

        soup = BeautifulSoup(html_content, "html.parser")

        tables = soup.find_all("table")
        sheets: dict[str, list[list[str]]] = {}
        if tables:
            for i, table in enumerate(tables):
                rows_data: list[list[str]] = []
                for tr in table.find_all("tr"):
                    cells = tr.find_all(["td", "th"])
                    if cells:
                        rows_data.append([cell.get_text(strip=True) for cell in cells])
                if rows_data:
                    sheets[f"Table{i + 1}"] = rows_data
        if not sheets:
            sheets["HTML"] = [[soup.get_text()]]

        extracted = ExtractedSource(
            source=source,
            sheets=sheets,
            raw_text=soup.get_text(),
        )
        return extracted


class GoogleSheetsSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.url and "docs.google.com/spreadsheets" in source.url:
            return True
        if source.type == "google_sheets":
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        import requests

        sheet_id = self._extract_sheet_id(source.url or "")
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

        resp = requests.get(export_url, timeout=30)
        if resp.status_code == 200:
            import io
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name

            xlsx_adapter = XlsxSourceAdapter()
            temp_source = SourceReference(type="file", path=tmp_path, format="xlsx")
            extracted = xlsx_adapter.read(temp_source)
            extracted.source = source
            extracted.metadata["google_sheet_id"] = sheet_id
            extracted.metadata["google_sheet_url"] = source.url

            Path(tmp_path).unlink(missing_ok=True)
            return extracted

        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        resp = requests.get(csv_url, timeout=30)
        resp.raise_for_status()
        reader = csv.reader(io.StringIO(resp.text))
        rows = [list(row) for row in reader]
        return ExtractedSource(
            source=source,
            sheets={"Sheet1": rows},
            raw_text=resp.text,
            metadata={"google_sheet_id": sheet_id},
        )

    @staticmethod
    def _extract_sheet_id(url: str) -> str:
        import re
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
        if match:
            return match.group(1)
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            return match.group(1)
        raise ValueError(f"Cannot extract sheet ID from URL: {url}")


class GoogleDocsSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.url and "docs.google.com/document" in source.url:
            return True
        if source.type == "google_docs":
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        import re
        import requests

        match = re.search(r"/document/d/([a-zA-Z0-9-_]+)", source.url or "")
        if not match:
            raise ValueError(f"Cannot extract doc ID from URL: {source.url}")
        doc_id = match.group(1)

        export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
        resp = requests.get(export_url, timeout=30)
        resp.raise_for_status()
        lines = resp.text.split("\n")
        return ExtractedSource(
            source=source,
            sheets={"Document": [[l] for l in lines]},
            raw_text=resp.text,
            metadata={"google_doc_id": doc_id},
        )


class ConfluenceSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.url and ("confluence" in source.url.lower() or source.type == "confluence"):
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        import requests

        resp = requests.get(source.url or "", timeout=30)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        lines = text.split("\n")

        tables = soup.find_all("table")
        sheets: dict[str, list[list[str]]] = {}
        if tables:
            for i, table in enumerate(tables):
                rows_data: list[list[str]] = []
                for tr in table.find_all("tr"):
                    cells = tr.find_all(["td", "th"])
                    if cells:
                        rows_data.append([cell.get_text(strip=True) for cell in cells])
                if rows_data:
                    sheets[f"Table{i + 1}"] = rows_data
        if not sheets:
            sheets["Content"] = [[l] for l in lines]

        return ExtractedSource(
            source=source,
            sheets=sheets,
            raw_text=text,
            metadata={"url": source.url},
        )


class SharePointSourceAdapter:
    def can_handle(self, source: SourceReference) -> bool:
        if source.url and "sharepoint.com" in source.url.lower():
            return True
        if source.type == "sharepoint":
            return True
        return False

    def read(self, source: SourceReference) -> ExtractedSource:
        import requests

        resp = requests.get(source.url or "", timeout=30)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text()
        lines = text.split("\n")

        tables = soup.find_all("table")
        sheets: dict[str, list[list[str]]] = {}
        if tables:
            for i, table in enumerate(tables):
                rows_data: list[list[str]] = []
                for tr in table.find_all("tr"):
                    cells = tr.find_all(["td", "th"])
                    if cells:
                        rows_data.append([cell.get_text(strip=True) for cell in cells])
                if rows_data:
                    sheets[f"Table{i + 1}"] = rows_data
        if not sheets:
            sheets["Content"] = [[l] for l in lines]

        return ExtractedSource(
            source=source,
            sheets=sheets,
            raw_text=text,
            metadata={"url": source.url},
        )
from __future__ import annotations

import logging
import uuid
from typing import Protocol

logger = logging.getLogger(__name__)


class DirectoryGateway(Protocol):
    def search(self, name: str) -> list[dict]: ...
    def is_available(self) -> bool: ...
    def get_capability(self) -> str: ...


class MCPDirectoryGateway:
    def __init__(self, mcp_call_function=None, search_tool: str = "search_employees"):
        self._mcp_call = mcp_call_function
        self._search_tool = search_tool

    def is_available(self) -> bool:
        return self._mcp_call is not None

    def get_capability(self) -> str:
        if self._search_tool == "search_employees":
            return "gal"
        if self._search_tool == "search_mail_history":
            return "mail_history"
        return "unavailable"

    def search(self, name: str) -> list[dict]:
        correlation_id = str(uuid.uuid4())
        if not self._mcp_call:
            logger.warning(
                "MCPDirectoryGateway.search: MCP client not configured, returning empty list",
                extra={"correlation_id": correlation_id, "query_name": name},
            )
            return []
        try:
            result = self._mcp_call(self._search_tool, {"query": name})
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "employees" in result:
                return result["employees"]
            logger.warning(
                "MCPDirectoryGateway.search: unexpected result type=%s",
                type(result).__name__,
                extra={"correlation_id": correlation_id, "query_name": name, "result_type": str(type(result))},
            )
            return []
        except Exception:
            logger.exception(
                "MCPDirectoryGateway.search: exception during MCP call",
                extra={"correlation_id": correlation_id, "query_name": name, "search_tool": self._search_tool},
            )
            return []


class FixtureDirectoryGateway:
    def __init__(self, employees: list[dict] | None = None):
        self._employees = employees or [
            {"full_name": "Гуреев Дмитрий Валерьевич", "email": "gureev@1bit.ru", "surname": "Гуреев"},
            {"full_name": "Исламгалиев Дмитрий Фанисович", "email": "islamgaliev@1bit.ru", "surname": "Исламгалиев"},
            {"full_name": "Исламгиев Дмитрий", "email": "islamgaliev@1bit.ru", "surname": "Исламгиев"},
            {"full_name": "Петров Александр Сергеевич", "email": "petrov@1bit.ru", "surname": "Петров"},
            {"full_name": "Сидорова Елена Ивановна", "email": "sidorova@1bit.ru", "surname": "Сидорова"},
        ]

    def is_available(self) -> bool:
        return True

    def get_capability(self) -> str:
        return "fixture"

    def search(self, name: str) -> list[dict]:
        results = []
        name_lower = name.lower()
        for emp in self._employees:
            fn_lower = emp["full_name"].lower()
            if name_lower in fn_lower or (emp.get("surname", "").lower() in name_lower):
                results.append(emp)
        return results

    def search_by_surname(self, surname: str) -> list[dict]:
        results = []
        surname_lower = surname.lower()
        for emp in self._employees:
            if surname_lower in emp.get("surname", "").lower() or surname_lower in emp["full_name"].lower():
                results.append(emp)
        return results
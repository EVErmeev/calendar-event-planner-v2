from __future__ import annotations

from typing import Protocol


class DirectoryGateway(Protocol):
    def search(self, name: str) -> list[dict]: ...
    def is_available(self) -> bool: ...


class MCPDirectoryGateway:
    def __init__(self, mcp_call_function=None, search_tool: str = "search_employees"):
        self._mcp_call = mcp_call_function
        self._search_tool = search_tool

    def is_available(self) -> bool:
        return self._mcp_call is not None

    def search(self, name: str) -> list[dict]:
        if not self._mcp_call:
            return []
        try:
            result = self._mcp_call(self._search_tool, {"query": name})
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "employees" in result:
                return result["employees"]
            return []
        except Exception:
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
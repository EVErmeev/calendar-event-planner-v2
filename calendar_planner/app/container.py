from __future__ import annotations

import logging
from typing import Any

from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway
from calendar_planner.participants.directory_gateway import MCPDirectoryGateway
from calendar_planner.app.mcp_transport import MCPTransport

logger = logging.getLogger(__name__)


class AppContainer:
    """Assembles all dependencies for the application."""

    def __init__(self, settings):
        self.settings = settings
        self._calendar_gateway = None
        self._directory_gateway = None
        self._mcp_transport: MCPTransport | None = None
        self._mcp_initialized = False
        self._init_warnings: list[str] = []

    def init_mcp(self) -> dict:
        """Initialize MCP transport and gateways."""
        if not self.settings.MCP_ENABLED:
            self._init_warnings.append("MCP is disabled (MCP_ENABLED=false)")
            return {
                "component": "MCP",
                "status": "warning",
                "message": "MCP is disabled in settings",
            }

        if not self.settings.MCP_SERVER_URL:
            self._init_warnings.append("MCP_SERVER_URL is empty")
            return {
                "component": "MCP",
                "status": "warning",
                "message": "MCP_SERVER_URL is not set — MCP transport not available",
            }

        self._mcp_transport = MCPTransport(self.settings.MCP_SERVER_URL)
        result = self._mcp_transport.connect()

        if self._mcp_transport.is_connected():
            mcp_call = self._mcp_transport.call_tool

            self._calendar_gateway = MCPCalendarGateway(
                mcp_call_function=mcp_call,
                server_url=self.settings.MCP_SERVER_URL,
                find_tool=self.settings.MCP_CALENDAR_FIND_TOOL,
                create_tool=self.settings.MCP_CALENDAR_CREATE_TOOL,
            )

            self._directory_gateway = MCPDirectoryGateway(
                mcp_call_function=mcp_call,
                search_tool=self.settings.MCP_DIRECTORY_SEARCH_TOOL,
            )

            self._mcp_initialized = True
            return result
        else:
            self._init_warnings.append(
                f"MCP connection failed: {result.get('message', 'unknown')}"
            )
            return result

    def get_calendar_gateway(self):
        if self._calendar_gateway is not None:
            return self._calendar_gateway
        from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
        self._init_warnings.append("Using FixtureCalendarGateway (MCP not available)")
        return FixtureCalendarGateway()

    def get_directory_gateway(self):
        if self._directory_gateway is not None:
            return self._directory_gateway
        from calendar_planner.participants.directory_gateway import FixtureDirectoryGateway
        self._init_warnings.append("Using FixtureDirectoryGateway (MCP not available)")
        return FixtureDirectoryGateway()

    def check_all_connections(self) -> list[dict]:
        """Check MCP, calendar, directory, source accessibility."""
        results: list[dict] = []

        results.append(self._check_mcp_transport())

        calendar_gw = self._calendar_gateway
        if calendar_gw is not None:
            results.append(calendar_gw.check_connection())
        else:
            results.append({
                "component": "MCP Calendar",
                "status": "warning",
                "message": "Calendar gateway not initialized",
            })

        directory_gw = self._directory_gateway
        if directory_gw is not None:
            dir_available = directory_gw.is_available()
            results.append({
                "component": "MCP Directory",
                "status": "success" if dir_available else "failed",
                "message": (
                    "Directory service available"
                    if dir_available
                    else "Directory service unavailable"
                ),
            })
        else:
            results.append({
                "component": "MCP Directory",
                "status": "warning",
                "message": "Directory gateway not initialized",
            })

        server_url = self.settings.MCP_SERVER_URL
        if not server_url:
            results.append({
                "component": "MCP Source URL",
                "status": "warning",
                "message": "MCP_SERVER_URL is empty",
            })
        else:
            results.append({
                "component": "MCP Source URL",
                "status": "success",
                "message": f"Configured: {server_url}",
            })

        return results

    def _check_mcp_transport(self) -> dict:
        if self._mcp_transport is None:
            if not self.settings.MCP_SERVER_URL:
                return {
                    "component": "MCP Transport",
                    "status": "warning",
                    "message": "MCP_SERVER_URL is empty",
                }
            self._mcp_transport = MCPTransport(self.settings.MCP_SERVER_URL)

        return self._mcp_transport.check_connection()
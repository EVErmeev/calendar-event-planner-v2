from __future__ import annotations

import logging

from calendar_planner.app.mcp_transport import MCPTransport
from calendar_planner.app.stdio_mcp_transport import StdioMCPTransport
from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway
from calendar_planner.participants.directory_gateway import MCPDirectoryGateway

logger = logging.getLogger(__name__)


class AppContainer:
    """Assembles all dependencies for the application."""

    def __init__(self, settings):
        self.settings = settings
        self._calendar_gateway = None
        self._directory_gateway = None
        self._mcp_transport: MCPTransport | StdioMCPTransport | None = None
        self._mcp_initialized = False
        self._mcp_disabled_or_unavailable = False
        self._init_warnings: list[str] = []

    @property
    def _is_test_env(self) -> bool:
        return self.settings.APP_ENV == "test"

    def init_mcp(self) -> dict:
        """Initialize MCP transport and gateways.

        Stores state clearly:
          - _mcp_disabled_or_unavailable = True  if MCP is off or not reachable
          - _mcp_initialized = True              only on full success

        Supports both HTTP URL and stdio command transports.
        """
        if not self.settings.MCP_ENABLED:
            self._mcp_disabled_or_unavailable = True
            self._init_warnings.append("MCP is disabled (MCP_ENABLED=false)")
            return {
                "component": "MCP",
                "status": "warning",
                "message": "MCP is disabled in settings",
            }

        # Try stdio transport first if MCP_STDIO_COMMAND is set
        if self.settings.MCP_STDIO_COMMAND:
            self._mcp_transport = StdioMCPTransport(self.settings.MCP_STDIO_COMMAND)
        elif self.settings.MCP_SERVER_URL:
            self._mcp_transport = MCPTransport(self.settings.MCP_SERVER_URL)
        else:
            self._mcp_disabled_or_unavailable = True
            self._init_warnings.append("Neither MCP_SERVER_URL nor MCP_STDIO_COMMAND is set")
            return {
                "component": "MCP",
                "status": "warning",
                "message": "MCP connection not configured",
            }
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
            self._mcp_disabled_or_unavailable = False
            return result
        else:
            self._mcp_disabled_or_unavailable = True
            self._init_warnings.append(
                f"MCP connection failed: {result.get('message', 'unknown')}"
            )
            return result

    def get_calendar_gateway(self):
        if self._calendar_gateway is not None:
            return self._calendar_gateway

        if self._is_test_env:
            from calendar_planner.calendar.fixture_gateway import FixtureCalendarGateway
            self._init_warnings.append("Using FixtureCalendarGateway (test env)")
            return FixtureCalendarGateway()

        raise RuntimeError(
            "MCP not available — calendar gateway is None and APP_ENV is not 'test'. "
            "Ensure MCP is initialized before calling get_calendar_gateway()."
        )

    def get_directory_gateway(self):
        if self._directory_gateway is not None:
            return self._directory_gateway

        if self._is_test_env:
            from calendar_planner.participants.directory_gateway import (
                FixtureDirectoryGateway,
            )
            self._init_warnings.append("Using FixtureDirectoryGateway (test env)")
            return FixtureDirectoryGateway()

        raise RuntimeError(
            "MCP not available — directory gateway is None and APP_ENV is not 'test'. "
            "Ensure MCP is initialized before calling get_directory_gateway()."
        )

    def check_all_connections(self) -> dict:
        """Check MCP, calendar, directory, source accessibility.
        Returns dict with ready_for_analysis flag."""
        results: list[dict] = []
        required_ok = True

        results.append(self._check_mcp_transport())

        calendar_gw = self._calendar_gateway
        if calendar_gw is not None:
            cal_result = calendar_gw.check_connection()
            results.append(cal_result)
            if cal_result.get("status") == "failed":
                required_ok = False
        else:
            results.append({
                "component": "MCP Calendar",
                "status": "warning",
                "message": "Calendar gateway not initialized",
            })
            required_ok = False

        directory_gw = self._directory_gateway
        if directory_gw is not None:
            dir_available = directory_gw.is_available()
            dir_result = {
                "component": "MCP Directory",
                "status": "success" if dir_available else "failed",
                "message": "Directory service available" if dir_available else "Directory service unavailable",
            }
            results.append(dir_result)
            if not dir_available:
                required_ok = False
        else:
            results.append({
                "component": "MCP Directory",
                "status": "warning",
                "message": "Directory gateway not initialized",
            })
            required_ok = False

        transport_ok = self._mcp_transport is not None and self._mcp_transport.is_connected()
        if not transport_ok:
            required_ok = False

        using_stdio = bool(self.settings.MCP_STDIO_COMMAND)
        if using_stdio:
            results.append({
                "component": "MCP Transport Type",
                "status": "success",
                "message": "Local stdio transport",
            })
        elif self.settings.MCP_SERVER_URL:
            results.append({
                "component": "MCP Transport Type",
                "status": "success",
                "message": f"HTTP transport: {self.settings.MCP_SERVER_URL[:60]}",
            })
        else:
            results.append({
                "component": "MCP Transport Type",
                "status": "failed",
                "message": "No transport configured (need MCP_STDIO_COMMAND or MCP_SERVER_URL)",
            })
            required_ok = False

        ready = transport_ok and required_ok
        return {
            "ready_for_analysis": ready,
            "required_components_ok": required_ok,
            "results": results,
        }

    def _check_mcp_transport(self) -> dict:
        if self._mcp_transport is None:
            using_stdio = bool(self.settings.MCP_STDIO_COMMAND)
            using_http = bool(self.settings.MCP_SERVER_URL)
            if using_stdio:
                self._mcp_transport = StdioMCPTransport(self.settings.MCP_STDIO_COMMAND)
            elif using_http:
                self._mcp_transport = MCPTransport(self.settings.MCP_SERVER_URL)
            else:
                return {
                    "component": "MCP Transport",
                    "status": "failed",
                    "message": "MCP transport not configured.",
                }

        return self._mcp_transport.check_connection()
from __future__ import annotations

import logging

from calendar_planner.app.credential_provider import CredentialProvider
from calendar_planner.app.mcp_transport import MCPTransport
from calendar_planner.app.stdio_mcp_transport import StdioMCPTransport
from calendar_planner.calendar.mcp_gateway import MCPCalendarGateway

logger = logging.getLogger(__name__)


class AppContainer:
    """Assembles all dependencies for the application."""

    def __init__(self, settings):
        self.settings = settings
        self._calendar_gateway = None
        self._directory_gateway = None
        self._directory_gateway_revision: int = -1
        self._mcp_transport: MCPTransport | StdioMCPTransport | None = None
        self._mcp_initialized = False
        self._mcp_disabled_or_unavailable = False
        self._init_warnings: list[str] = []
        self.credential_provider = CredentialProvider()
        self.ews_credentials_state: dict = {"available": False, "source": "none", "username": ""}
        self._initialize_ews_credentials()

    @property
    def _is_test_env(self) -> bool:
        return self.settings.APP_ENV == "test"

    def _reset_mcp_state(self) -> None:
        """Close and drop all MCP state so it can be rebuilt."""
        if self._mcp_transport is not None:
            try:
                self._mcp_transport.close()
            except Exception:
                logger.debug("close old MCP transport failed", exc_info=True)
        self._mcp_transport = None
        self._calendar_gateway = None
        self._mcp_initialized = False
        self._mcp_disabled_or_unavailable = False
        self._init_warnings = []

    def _ensure_mcp_settings_from_env(self) -> None:
        """Self-heal: if MCP is enabled but no transport is configured in runtime
        settings, reload the MCP keys from the actual .env file.

        Only fires when the MCP config is absent from the whole environment
        (i.e. the app started before .env was applied) — never overrides an
        explicit MCP_ENABLED/MCP_STDIO_COMMAND set by the caller. Avoids
        touching the real .env during tests.
        """
        import os
        if self._is_test_env:
            return
        if "MCP_ENABLED" in os.environ:
            # The app (or the caller) already decided on MCP — respect it.
            return
        if self.settings.MCP_STDIO_COMMAND or self.settings.MCP_SERVER_URL:
            return
        if not self.settings.MCP_ENABLED:
            return
        try:
            from calendar_planner.app.env_config import EnvConfigWriter
            data = EnvConfigWriter.default().read_dict()
            cmd = data.get("MCP_STDIO_COMMAND", "").strip()
            if not cmd:
                return
            self.settings.MCP_STDIO_COMMAND = cmd
            os.environ["MCP_STDIO_COMMAND"] = cmd
            if data.get("MCP_CALENDAR_FIND_TOOL"):
                self.settings.MCP_CALENDAR_FIND_TOOL = data["MCP_CALENDAR_FIND_TOOL"].strip()
                os.environ["MCP_CALENDAR_FIND_TOOL"] = self.settings.MCP_CALENDAR_FIND_TOOL
            if data.get("MCP_CALENDAR_CREATE_TOOL"):
                self.settings.MCP_CALENDAR_CREATE_TOOL = data["MCP_CALENDAR_CREATE_TOOL"].strip()
                os.environ["MCP_CALENDAR_CREATE_TOOL"] = self.settings.MCP_CALENDAR_CREATE_TOOL
            logger.info("MCP settings self-healed from .env")
        except Exception:
            logger.debug("MCP settings self-heal skipped", exc_info=True)

    def _mcp_tool_status(self) -> dict:
        """Read tools and check find/create availability without calling create."""
        transport = self._mcp_transport
        connected = transport is not None and transport.is_connected()
        tools: list[str] = []
        if connected:
            list_tools = getattr(transport, "list_tools", None)
            if callable(list_tools):
                tools = list_tools()
        return {
            "connected": connected,
            "tools": tools,
            "tools_count": len(tools),
            "find_events": self.settings.MCP_CALENDAR_FIND_TOOL in tools,
            "create_event": self.settings.MCP_CALENDAR_CREATE_TOOL in tools,
            "calendar_gateway_ready": self._calendar_gateway is not None,
        }

    def configure_mcp_stdio(
        self,
        command: str,
        find_tool: str,
        create_tool: str,
        persist: bool = True,
    ) -> dict:
        """Configure, persist, connect and verify a local stdio MCP in one call.

        Steps: reset -> update settings + os.environ -> save .env -> init_mcp ->
        tools/list -> verify find_events/create_event -> create calendar gateway.

        Never invokes ``create_event`` — only checks its presence in tools/list.
        """
        import os

        self._reset_mcp_state()

        self.settings.MCP_ENABLED = True
        self.settings.MCP_STDIO_COMMAND = command
        self.settings.MCP_SERVER_URL = ""
        self.settings.MCP_CALENDAR_FIND_TOOL = find_tool
        self.settings.MCP_CALENDAR_CREATE_TOOL = create_tool

        os.environ["MCP_ENABLED"] = "true"
        os.environ["MCP_STDIO_COMMAND"] = command
        os.environ["MCP_SERVER_URL"] = ""
        os.environ["MCP_CALENDAR_FIND_TOOL"] = find_tool
        os.environ["MCP_CALENDAR_CREATE_TOOL"] = create_tool

        if persist:
            from calendar_planner.app.env_config import EnvConfigWriter
            EnvConfigWriter.default().set({
                "MCP_ENABLED": "true",
                "MCP_SERVER_URL": "",
                "MCP_STDIO_COMMAND": command,
                "MCP_CALENDAR_FIND_TOOL": find_tool,
                "MCP_CALENDAR_CREATE_TOOL": create_tool,
            })

        init_result = self.init_mcp()
        status = self._mcp_tool_status()
        status["init_result"] = init_result
        status["saved"] = bool(persist)
        status["command"] = command
        status["transport"] = "local stdio"
        status["find_tool_name"] = find_tool
        status["create_tool_name"] = create_tool
        status["status"] = "success" if status["connected"] else "failed"
        status["message"] = (
            f"Connected to {status['tools_count']} tools" if status["connected"]
            else (init_result or {}).get("message", "MCP not connected")
        )
        return status

    def reload_mcp_from_settings(self) -> dict:
        """Recreate the transport and calendar gateway from current runtime settings."""
        self._reset_mcp_state()
        init_result = self.init_mcp()
        status = self._mcp_tool_status()
        status["init_result"] = init_result
        status["status"] = "success" if status["connected"] else "failed"
        status["message"] = (
            f"Connected to {status['tools_count']} tools" if status["connected"]
            else (init_result or {}).get("message", "MCP not connected")
        )
        return status

    def init_mcp(self) -> dict:
        """Initialize MCP transport and gateways.

        Stores state clearly:
          - _mcp_disabled_or_unavailable = True  if MCP is off or not reachable
          - _mcp_initialized = True              only on full success

        Supports both HTTP URL and stdio command transports.
        """
        self._ensure_mcp_settings_from_env()
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

    def _initialize_ews_credentials(self) -> None:
        username = self.settings.EWS_USERNAME or ""
        if username:
            result = self.credential_provider.load_persistent(username)
            if result.available:
                self.ews_credentials_state = {"available": True, "source": result.source, "username": username}
                return
        self.ews_credentials_state = {"available": False, "source": "none", "username": username or ""}

    def reload_persistent_ews_credentials(self):
        username = self.settings.EWS_USERNAME or ""
        result = self.credential_provider.load_persistent(username)
        self._directory_gateway = None
        self._directory_gateway_revision = -1
        if result.available:
            self.ews_credentials_state = {"available": True, "source": result.source, "username": username}
        return result

    def get_directory_gateway(self):
        if self._directory_gateway is not None:
            current_rev = self.credential_provider.credentials_revision
            if self._directory_gateway_revision == current_rev:
                return self._directory_gateway
            self._directory_gateway = None

        # Test env always uses fixture
        if self._is_test_env:
            from calendar_planner.participants.directory_gateway import (
                FixtureDirectoryGateway,
            )
            self._directory_gateway = FixtureDirectoryGateway()
            return self._directory_gateway

        endpoint = self.settings.EWS_ENDPOINT or ""
        creds = self.credential_provider.get_credentials()

        from calendar_planner.participants.ews_directory_gateway import (
            EWSDirectoryGateway,
        )
        gw = EWSDirectoryGateway(
            endpoint=endpoint,
            username=creds.username if creds.available else (self.settings.EWS_USERNAME or ""),
            password=creds.password if creds.available else "",
        )
        if creds.available:
            self._directory_gateway = gw
            self._directory_gateway_revision = self.credential_provider.credentials_revision
        return gw

    def configure_ews(self, endpoint: str, username: str, password: str | None) -> None:
        """Configure EWS and reset cached gateway. Password stored in session only."""
        import os
        if endpoint:
            os.environ["EWS_ENDPOINT"] = endpoint
        if username:
            os.environ["EWS_USERNAME"] = username
        if password:
            self.credential_provider.set_session_credentials(username, password)
        self._directory_gateway = None

    def reset_directory_gateway(self) -> None:
        self._directory_gateway = None
        return self._directory_gateway

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

            # Timezone warning
            tz_warnings = cal_result.get("timezone_warnings", 0)
            if tz_warnings > 0:
                results.append({
                    "component": "Calendar Timezone",
                    "status": "warning",
                    "message": f"Часть событий ({tz_warnings}) без timezone — использована нормализация UTC.",
                })
        else:
            results.append({
                "component": "MCP Calendar",
                "status": "warning",
                "message": "Calendar gateway not initialized",
            })
            required_ok = False

        try:
            directory_gw = self.get_directory_gateway()
        except RuntimeError:
            directory_gw = None

        if directory_gw is not None:
            dir_cap = directory_gw.get_capability()
            if "ews" in dir_cap.lower() and directory_gw.is_available():
                # Probe real EWS ResolveNames
                try:
                    # Use last user probe query or the username as probe
                    probe_query = self.settings.EWS_USERNAME or "calendar-planner-probe"
                    probe_result = directory_gw.search(probe_query)
                    probe_status = probe_result.status if isinstance(probe_result, object) and hasattr(probe_result, "status") else "ok"
                    if probe_status in ("success", "ambiguous", "not_found"):
                        results.append({
                            "component": "EWS Directory",
                            "status": "success",
                            "message": f"EWS ResolveNames available ({probe_status})",
                        })
                        results.append({
                            "component": "Authentication",
                            "status": "success",
                            "message": "NTLM session credentials accepted",
                        })
                    elif probe_status == "auth_failed":
                        results.append({
                            "component": "EWS Directory",
                            "status": "failed",
                            "message": "Ошибка авторизации EWS. Проверьте логин/пароль.",
                            "error": "AUTH_FAILED",
                        })
                        required_ok = False
                    elif probe_status == "forbidden":
                        results.append({
                            "component": "EWS Directory",
                            "status": "failed",
                            "message": "EWS доступ запрещён (403).",
                            "error": "FORBIDDEN",
                        })
                        required_ok = False
                    elif probe_status == "timeout":
                        results.append({
                            "component": "EWS Directory",
                            "status": "failed",
                            "message": "EWS таймаут.",
                            "error": "TIMEOUT",
                        })
                        required_ok = False
                    else:
                        results.append({
                            "component": "EWS Directory",
                            "status": "failed",
                            "message": f"EWS error: {probe_status}",
                        })
                        required_ok = False
                except Exception as exc:
                    results.append({
                        "component": "EWS Directory",
                        "status": "failed",
                        "message": f"EWS probe error: {exc}",
                    })
                    required_ok = False
            else:
                dir_available = directory_gw.is_available()
                dir_result = {
                    "component": "Directory",
                    "status": "success" if dir_available else "warning",
                    "message": "EWS directory not configured" if not dir_available else f"Directory ({dir_cap}) available",
                }
                results.append(dir_result)
                if not dir_available:
                    required_ok = False
        else:
            results.append({
                "component": "Directory",
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
        self._ensure_mcp_settings_from_env()
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
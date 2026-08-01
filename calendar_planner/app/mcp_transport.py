from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

import requests

logger = logging.getLogger(__name__)

SUPPORTED_PROTOCOL_VERSIONS = ["2025-03-26"]


class MCPProtocolError(Exception):
    """Protocol-level error: version mismatch, invalid response, tool isError, etc."""


class MCPTransport:
    """Connects to MCP server URL and provides tool calling capability."""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/") if server_url else ""
        self.tools: list[dict] = []
        self._connected = False
        self._request_id = 0
        self._session: requests.Session | None = None
        self._server_info: dict = {}
        self._server_capabilities: dict = {}
        self._protocol_version: str | None = None
        self._server_name: str = "unknown"
        self._mcp_session_id: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> dict:
        """Connect to MCP server, negotiate version, discover tools. Returns status dict."""
        if not self.server_url:
            return {
                "component": "MCP Transport",
                "status": "warning",
                "message": "MCP_SERVER_URL is empty, MCP transport disabled",
            }

        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        })
        self._apply_custom_headers()

        try:
            # --- 1. initialize ---
            init_result = self._send_initialize()

            self._server_info = init_result
            self._server_capabilities = init_result.get("capabilities", {})
            self._server_name = init_result.get("serverInfo", {}).get("name", "unknown")

            # --- 2. version negotiation ---
            server_version = init_result.get("protocolVersion", "2025-03-26")
            self._negotiate_version(server_version)

            # --- 3. initialized notification ---
            self._send_notification("notifications/initialized")

            # --- 4. discover tools (with pagination) ---
            self.tools = self._discover_tools()
            self._connected = True

            return {
                "component": "MCP Transport",
                "status": "success",
                "message": f"Connected to {self._server_name}, discovered {len(self.tools)} tools",
                "server": self._server_name,
                "tool_count": len(self.tools),
                "tool_names": [t.get("name", "?") for t in self.tools],
            }

        except MCPProtocolError:
            self._connected = False
            raise
        except requests.ConnectionError as e:
            self._connected = False
            correlation_id = str(uuid.uuid4())[:8]
            return {
                "component": "MCP Transport",
                "status": "failed",
                "message": f"Cannot connect to MCP server at {self.server_url}",
                "error": str(e),
                "correlation_id": correlation_id,
            }
        except requests.Timeout as e:
            self._connected = False
            correlation_id = str(uuid.uuid4())[:8]
            return {
                "component": "MCP Transport",
                "status": "failed",
                "message": f"Timeout connecting to MCP server at {self.server_url}",
                "error": str(e),
                "correlation_id": correlation_id,
            }
        except Exception as e:
            self._connected = False
            correlation_id = str(uuid.uuid4())[:8]
            return {
                "component": "MCP Transport",
                "status": "failed",
                "message": f"MCP initialization error: {e}",
                "error": str(e),
                "correlation_id": correlation_id,
            }

    def call_tool(self, tool_name: str, arguments: dict) -> dict | list:
        """Call an MCP tool with arguments. Raises MCPProtocolError on isError."""
        if not self._connected:
            correlation_id = str(uuid.uuid4())[:8]
            raise ConnectionError(
                f"MCP transport not connected [cid={correlation_id}]"
            )

        try:
            result = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments,
            })

            # --- top-level isError handling ---
            if isinstance(result, dict) and result.get("isError") is True:
                raise MCPProtocolError(
                    f"Tool '{tool_name}' returned top-level isError: "
                    f"{result.get('error', 'Unknown error')}"
                )

            # --- isError handling ---
            if isinstance(result, dict):
                content = result.get("content")
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("isError") is True:
                            error_text = item.get("text", "Unknown error")
                            raise MCPProtocolError(
                                f"Tool '{tool_name}' returned isError: {error_text}"
                            )
                elif isinstance(content, dict) and content.get("isError") is True:
                    error_text = content.get("text", "Unknown error")
                    raise MCPProtocolError(
                        f"Tool '{tool_name}' returned isError: {error_text}"
                    )

            # --- unwrap content ---
            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list):
                    texts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            texts.append(item.get("text", ""))
                    if len(texts) == 1:
                        try:
                            return json.loads(texts[0])
                        except (json.JSONDecodeError, ValueError):
                            return texts[0]
                    return texts
                return content

            return result

        except MCPProtocolError:
            raise
        except requests.RequestException as e:
            correlation_id = str(uuid.uuid4())[:8]
            raise ConnectionError(
                f"Tool call '{tool_name}' failed [cid={correlation_id}]: {e}"
            ) from e

    def list_tools(self) -> list[str]:
        """Return discovered tool names."""
        return [t.get("name", "?") for t in self.tools]

    def is_connected(self) -> bool:
        return self._connected

    @property
    def server_capabilities(self) -> dict:
        return self._server_capabilities

    @property
    def protocol_version(self) -> str | None:
        return self._protocol_version

    def check_connection(self) -> dict:
        """Comprehensive connection check returning component status."""
        if not self.server_url:
            return {
                "component": "MCP Transport",
                "status": "warning",
                "message": "MCP_SERVER_URL not configured",
            }

        if not self._connected:
            return self.connect()

        try:
            self._send_request("tools/list", {})
            return {
                "component": "MCP Transport",
                "status": "success",
                "message": f"Connected ({len(self.tools)} tools available)",
                "tool_count": len(self.tools),
            }
        except Exception as e:
            self._connected = False
            correlation_id = str(uuid.uuid4())[:8]
            return {
                "component": "MCP Transport",
                "status": "failed",
                "message": f"Connection lost: {e}",
                "correlation_id": correlation_id,
            }

    def close(self) -> None:
        if self._session:
            self._session.close()
            self._session = None
        self._connected = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_request(self, method: str, params: dict) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id,
        }

        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            })

        response = self._session.post(
            self.server_url,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()

        self._extract_mcp_session_id(response)

        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            data = self._parse_sse_stream(response)
        else:
            data = response.json()

        if isinstance(data, dict) and "error" in data:
            error_info = data["error"]
            raise MCPProtocolError(
                f"MCP error {error_info.get('code', '?')}: {error_info.get('message', 'Unknown error')}"
            )

        if isinstance(data, dict):
            result = data.get("result", data)
        else:
            result = data

        if isinstance(result, dict) and result.get("isError") is True:
            raise MCPProtocolError(
                f"MCP tool returned top-level isError: {result.get('error', 'Unknown error')}"
            )

        return result

    def _extract_mcp_session_id(self, response: requests.Response) -> None:
        session_id = response.headers.get("Mcp-Session-Id")
        if session_id and session_id != self._mcp_session_id:
            self._mcp_session_id = session_id
            if self._session is not None:
                self._session.headers.update({"Mcp-Session-Id": session_id})
            logger.debug("Extracted Mcp-Session-Id: %s", session_id)

    def _parse_sse_stream(self, response: requests.Response) -> Any:
        results: list[Any] = []
        current_event: str | None = None
        for line in response.iter_lines(decode_unicode=True):
            if line is None:
                continue
            if line.startswith("event:"):
                current_event = line[len("event:"):].strip()
                continue
            if line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                if not data_str or data_str == "[DONE]":
                    break
                try:
                    parsed = json.loads(data_str)
                except json.JSONDecodeError:
                    logger.warning("SSE: failed to JSON-decode data line: %s", data_str[:200])
                    continue
                if current_event == "message" and isinstance(parsed, dict) and "result" in parsed:
                    return parsed
                results.append(parsed)
                continue
            if line == "":
                current_event = None
        if not results:
            return {}
        if len(results) == 1:
            return results[0]
        return results

    def _send_notification(self, method: str, params: dict | None = None) -> None:
        """Send a JSON-RPC notification (no 'id' field, no response expected)."""
        if self._session is None:
            return
        payload: dict = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        try:
            response = self._session.post(
                self.server_url,
                json=payload,
                timeout=15,
            )
            if response.status_code == 202:
                logger.info("Notification %s accepted (202)", method)
            elif response.status_code >= 300:
                logger.warning(
                    "Notification %s returned non-2xx status %d: %s",
                    method, response.status_code, response.text[:500],
                )
        except Exception:
            logger.warning("Failed to send notification %s", method, exc_info=True)

    def _send_initialize(self) -> dict:
        return self._send_request("initialize", {
            "protocolVersion": SUPPORTED_PROTOCOL_VERSIONS[0],
            "capabilities": {},
            "clientInfo": {
                "name": "calendar-event-planner-v2",
                "version": "2.0.0",
            },
        })

    def _negotiate_version(self, server_version: str) -> None:
        if server_version in SUPPORTED_PROTOCOL_VERSIONS:
            self._protocol_version = server_version
            logger.debug("Negotiated protocol version: %s", server_version)
        else:
            raise MCPProtocolError(
                f"Server protocol version '{server_version}' is not supported. "
                f"This client only supports: {SUPPORTED_PROTOCOL_VERSIONS}"
            )

    def _discover_tools(self) -> list[dict]:
        """Fetch tools/list with pagination support."""
        all_tools: list[dict] = []
        cursor: str | None = None

        while True:
            params: dict = {}
            if cursor is not None:
                params["cursor"] = cursor

            result = self._send_request("tools/list", params)

            # tools/list result format: { "tools": [...], "nextCursor": "..." } or just [...]
            if isinstance(result, list):
                all_tools.extend(result)
                break
            elif isinstance(result, dict):
                raw_tools = result.get("tools", [])
                if isinstance(raw_tools, list):
                    all_tools.extend(raw_tools)
                next_cursor = result.get("nextCursor")
                if next_cursor is None:
                    break
                cursor = next_cursor
            else:
                break

        return all_tools

    def _apply_custom_headers(self) -> None:
        headers_json = os.getenv("MCP_CUSTOM_HEADERS", "")
        if not headers_json:
            return
        try:
            custom_headers = json.loads(headers_json)
            if isinstance(custom_headers, dict) and self._session is not None:
                self._session.headers.update(custom_headers)
                logger.debug("Applied %d custom headers from MCP_CUSTOM_HEADERS", len(custom_headers))
        except json.JSONDecodeError:
            logger.warning("MCP_CUSTOM_HEADERS is not valid JSON: %s", headers_json)
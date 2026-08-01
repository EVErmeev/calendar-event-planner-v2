from __future__ import annotations

import uuid
import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class MCPTransport:
    """Connects to MCP server URL and provides tool calling capability."""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/") if server_url else ""
        self.tools: list[dict] = []
        self._connected = False
        self._request_id = 0
        self._session: requests.Session | None = None
        self._server_info: dict = {}

    def connect(self) -> dict:
        """Connect to MCP server, discover tools. Returns status dict."""
        if not self.server_url:
            return {
                "component": "MCP Transport",
                "status": "warning",
                "message": "MCP_SERVER_URL is empty, MCP transport disabled",
            }

        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        try:
            init_result = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "calendar-event-planner-v2",
                    "version": "2.0.0",
                },
            })

            self._server_info = init_result
            self._server_name = init_result.get("serverInfo", {}).get("name", "unknown")

            tools_result = self._send_request("tools/list", {})
            raw_tools = tools_result if isinstance(tools_result, list) else tools_result.get("tools", [])
            self.tools = raw_tools if isinstance(raw_tools, list) else []
            self._connected = True

            return {
                "component": "MCP Transport",
                "status": "success",
                "message": f"Connected to {self._server_name}, discovered {len(self.tools)} tools",
                "server": self._server_name,
                "tool_count": len(self.tools),
                "tool_names": [t.get("name", "?") for t in self.tools],
            }

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
        """Call an MCP tool with arguments."""
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

            if isinstance(result, dict) and "content" in result:
                content = result["content"]
                if isinstance(content, list):
                    texts = []
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            texts.append(item.get("text", ""))
                    if len(texts) == 1:
                        try:
                            import json
                            return json.loads(texts[0])
                        except (json.JSONDecodeError, ValueError):
                            return texts[0]
                    return texts
                return content

            return result

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
            self._session.headers.update({"Content-Type": "application/json"})

        response = self._session.post(
            self.server_url,
            json=payload,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()

        if "error" in data:
            error_info = data["error"]
            raise ConnectionError(
                f"MCP error {error_info.get('code', '?')}: {error_info.get('message', 'Unknown error')}"
            )

        return data.get("result", data)

    def close(self) -> None:
        if self._session:
            self._session.close()
            self._session = None
        self._connected = False
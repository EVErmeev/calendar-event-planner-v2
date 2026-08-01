"""Stdio-based MCP transport for local MCP servers.

Communicates with MCP servers that run as local processes over stdin/stdout
using JSON-RPC 2.0 protocol, compatible with the MCP specification.
"""

from __future__ import annotations

import json
import logging
import subprocess
import uuid
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class MCPProtocolError(Exception):
    """Protocol-level MCP error."""


class StdioMCPTransport:
    """Connects to a local MCP server via stdin/stdout."""

    SUPPORTED_PROTOCOL_VERSIONS: ClassVar[list[str]] = ["2025-03-26"]

    def __init__(self, command: str):
        self.command = command
        self.tools: list[dict] = []
        self._connected = False
        self._request_id = 0
        self._process: subprocess.Popen | None = None
        self._server_info: dict = {}
        self._server_capabilities: dict = {}
        self._server_name = "unknown"
        self._protocol_version = self.SUPPORTED_PROTOCOL_VERSIONS[0]

    def connect(self) -> dict:
        if not self.command:
            return {
                "component": "MCP Transport",
                "status": "warning",
                "message": "No stdio command configured",
            }

        try:
            self._process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True,
                encoding="utf-8",
            )

            # Initialize
            init_result = self._send_request("initialize", {
                "protocolVersion": self._protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "calendar-event-planner-v2",
                    "version": "2.0.0",
                },
            })

            self._server_info = init_result
            self._server_capabilities = init_result.get("capabilities", {})
            self._server_name = init_result.get("serverInfo", {}).get("name", "unknown")

            # Negotiate version
            server_version = init_result.get("protocolVersion", self._protocol_version)
            self._negotiate_version(server_version)

            # Send initialized notification
            self._send_notification("notifications/initialized")

            # Discover tools
            tools_result = self._send_request("tools/list", {})
            raw_tools = (
                tools_result if isinstance(tools_result, list)
                else tools_result.get("tools", [])
            )
            self.tools = raw_tools if isinstance(raw_tools, list) else []
            self._connected = True

            return {
                "component": "MCP Transport",
                "status": "success",
                "message": f"Connected to {self._server_name}, {len(self.tools)} tools",
                "server": self._server_name,
                "tool_count": len(self.tools),
                "tool_names": [t.get("name", "?") for t in self.tools],
            }

        except MCPProtocolError:
            self._connected = False
            raise
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

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        if not self._connected:
            raise ConnectionError("MCP transport not connected")

        result = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list):
                has_error = any(
                    isinstance(c, dict) and c.get("isError")
                    for c in content
                )
                if has_error:
                    raise MCPProtocolError(
                        f"Tool '{tool_name}' returned isError"
                    )
                texts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        txt = item.get("text", "")
                        texts.append(txt)
                if len(texts) == 1:
                    try:
                        return json.loads(texts[0])
                    except (json.JSONDecodeError, ValueError):
                        return texts[0]
                return texts
            return content

        return result

    def list_tools(self) -> list[str]:
        return [t.get("name", "?") for t in self.tools]

    def is_connected(self) -> bool:
        return self._connected

    def check_connection(self) -> dict:
        if not self.command:
            return {
                "component": "MCP Transport",
                "status": "warning",
                "message": "No stdio command configured",
            }

        if not self._connected:
            return self.connect()

        return {
            "component": "MCP Transport",
            "status": "success",
            "message": f"Connected ({len(self.tools)} tools)",
            "tool_count": len(self.tools),
        }

    def _send_request(self, method: str, params: dict) -> Any:
        if self._process is None or self._process.stdin is None or self._process.stdout is None:
            raise ConnectionError("Process not running")

        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id,
        }

        request_text = json.dumps(payload, ensure_ascii=False) + "\n"
        self._process.stdin.write(request_text)
        self._process.stdin.flush()

        response_line = self._process.stdout.readline()
        if not response_line:
            raise ConnectionError("No response from MCP server")

        try:
            data = json.loads(response_line.strip())
        except json.JSONDecodeError as e:
            raise ConnectionError(f"Invalid JSON response: {e}")

        if "error" in data:
            error_info = data["error"]
            raise MCPProtocolError(
                f"MCP error {error_info.get('code', '?')}: "
                f"{error_info.get('message', 'Unknown')}"
            )

        return data.get("result", data)

    def _send_notification(self, method: str, params: dict | None = None) -> None:
        if self._process is None or self._process.stdin is None:
            return
        payload: dict = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        try:
            self._process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._process.stdin.flush()
        except Exception:
            logger.warning("Failed to send notification %s", method)

    def _negotiate_version(self, server_version: str) -> None:
        if server_version in self.SUPPORTED_PROTOCOL_VERSIONS:
            self._protocol_version = server_version
        else:
            raise MCPProtocolError(
                f"Server version '{server_version}' not supported"
            )

    def close(self) -> None:
        if self._process:
            try:
                self._process.stdin.close()
                self._process.stdout.close()
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()
            self._process = None
        self._connected = False
"""Stdio-based MCP transport with timeout, stderr drain, thread-safe I/O."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
import uuid
from collections import deque
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


class MCPProtocolError(Exception):
    """Protocol-level MCP error."""


class MCPTimeoutError(Exception):
    """MCP operation timed out."""


class StdioMCPTransport:
    """Connects to a local MCP server via stdin/stdout with timeout protection."""

    SUPPORTED_PROTOCOL_VERSIONS: ClassVar[list[str]] = ["2025-03-26"]
    STDERR_RING_SIZE: ClassVar[int] = 200

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
        self._stdout_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._responses: dict[int, Any] = {}
        self._response_events: dict[int, threading.Event] = {}
        self._stderr_ring: deque[str] = deque(maxlen=self.STDERR_RING_SIZE)
        self._reader_stop = threading.Event()
        self._connect_timeout = int(os.getenv("MCP_CONNECT_TIMEOUT_SECONDS", "30"))
        self._tool_timeout = int(os.getenv("MCP_TOOL_TIMEOUT_SECONDS", "60"))

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
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=True, text=True, encoding="utf-8",
            )
            self._reader_stop.clear()
            self._start_stderr_reader()
            self._start_stdout_reader()

            init_result = self._send_request("initialize", {
                "protocolVersion": self._protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "calendar-event-planner-v2", "version": "2.0.0"},
            }, timeout=self._connect_timeout)

            self._server_info = init_result
            self._server_capabilities = init_result.get("capabilities", {})
            self._server_name = init_result.get("serverInfo", {}).get("name", "unknown")

            server_version = init_result.get("protocolVersion", self._protocol_version)
            self._negotiate_version(server_version)

            self._send_notification("notifications/initialized")

            tools_result = self._send_request("tools/list", {}, timeout=self._connect_timeout)
            raw_tools = tools_result if isinstance(tools_result, list) else tools_result.get("tools", [])
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
        except MCPTimeoutError as e:
            self._connected = False
            self._kill_process()
            return {"component": "MCP Transport", "status": "failed", "message": f"Connection timed out: {e}", "error": str(e)}
        except MCPProtocolError:
            self._connected = False
            self._kill_process()
            raise
        except Exception as e:
            self._connected = False
            self._kill_process()
            return {"component": "MCP Transport", "status": "failed", "message": f"Connection error: {e}", "error": str(e), "correlation_id": str(uuid.uuid4())[:8]}

    def call_tool(self, tool_name: str, arguments: dict) -> Any:
        if not self._connected:
            raise ConnectionError("MCP transport not connected")

        result = self._send_request("tools/call", {"name": tool_name, "arguments": arguments}, timeout=self._tool_timeout)

        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list):
                has_error = any(isinstance(c, dict) and c.get("isError") for c in content)
                if has_error:
                    raise MCPProtocolError(f"Tool '{tool_name}' returned isError")
                texts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
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
            return {"component": "MCP Transport", "status": "warning", "message": "No stdio command configured"}
        if not self._connected:
            return self.connect()
        return {"component": "MCP Transport", "status": "success", "message": f"Connected ({len(self.tools)} tools)", "tool_count": len(self.tools)}

    def get_stderr_lines(self) -> list[str]:
        return list(self._stderr_ring)

    def close(self) -> None:
        self._connected = False
        self._reader_stop.set()
        self._kill_process()

    # --- Internal ---

    def _send_request(self, method: str, params: dict, timeout: int = 30) -> Any:
        with self._lock:
            self._request_id += 1
            rid = self._request_id
            event = threading.Event()
            self._response_events[rid] = event

        payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": rid}, ensure_ascii=False) + "\n"

        if self._process is None or self._process.stdin is None:
            raise ConnectionError("Process not running")

        self._process.stdin.write(payload)
        self._process.stdin.flush()

        if not event.wait(timeout=timeout):
            with self._lock:
                self._response_events.pop(rid, None)
            raise MCPTimeoutError(f"Request {method} (id={rid}) timed out after {timeout}s")

        with self._lock:
            data = self._responses.pop(rid, None)
            self._response_events.pop(rid, None)

        if data is None:
            raise ConnectionError(f"No response for request {rid}")

        if isinstance(data, dict) and "error" in data:
            e = data["error"]
            raise MCPProtocolError(f"MCP error {e.get('code','?')}: {e.get('message','Unknown')}")

        return data.get("result", data) if isinstance(data, dict) else data

    def _send_notification(self, method: str, params: dict | None = None) -> None:
        if self._process is None or self._process.stdin is None:
            return
        payload: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        try:
            self._process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._process.stdin.flush()
        except Exception:
            logger.warning("Failed to send notification %s", method)

    def _start_stdout_reader(self) -> None:
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stdout_thread.start()

    def _read_stdout(self) -> None:
        if self._process is None or self._process.stdout is None:
            return
        try:
            for line in self._process.stdout:
                if self._reader_stop.is_set():
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(data, dict) and "id" in data:
                    rid = data["id"]
                    with self._lock:
                        self._responses[rid] = data
                        evt = self._response_events.get(rid)
                    if evt:
                        evt.set()
        except Exception:
            pass

    def _start_stderr_reader(self) -> None:
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr_thread.start()

    def _read_stderr(self) -> None:
        if self._process is None or self._process.stderr is None:
            return
        try:
            for line in self._process.stderr:
                if self._reader_stop.is_set():
                    break
                self._stderr_ring.append(line.rstrip("\n\r"))
        except Exception:
            pass

    def _kill_process(self) -> None:
        self._reader_stop.set()
        p = self._process
        self._process = None
        if p is None:
            return
        try:
            p.stdin.close()
        except Exception:
            pass
        try:
            p.stdout.close()
        except Exception:
            pass
        try:
            p.stderr.close()
        except Exception:
            pass
        try:
            p.terminate()
            p.wait(timeout=5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass
        with self._lock:
            for evt in self._response_events.values():
                evt.set()
            self._response_events.clear()
            self._responses.clear()

    def _negotiate_version(self, server_version: str) -> None:
        if server_version in self.SUPPORTED_PROTOCOL_VERSIONS:
            self._protocol_version = server_version
        else:
            raise MCPProtocolError(f"Server version '{server_version}' not supported")

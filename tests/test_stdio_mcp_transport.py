"""Tests for StdioMCPTransport — timeout, stderr ring, cancellation, close."""
from __future__ import annotations

import time

import pytest

from calendar_planner.app.stdio_mcp_transport import StdioMCPTransport


class TestStdioTransportConstruction:
    def test_constructs_with_stderr_ring(self):
        t = StdioMCPTransport("dummy")
        assert t.get_stderr_lines() == []
        assert t._stderr_ring.maxlen == t.STDERR_RING_SIZE

    def test_stderr_ring_size_is_200(self):
        t = StdioMCPTransport("dummy")
        assert t.STDERR_RING_SIZE == 200

    def test_not_connected_initially(self):
        t = StdioMCPTransport("dummy")
        assert t.is_connected() is False

    def test_lists_tools_empty(self):
        t = StdioMCPTransport("dummy")
        assert t.list_tools() == []

    def test_connect_with_empty_command(self):
        t = StdioMCPTransport("")
        result = t.connect()
        assert result["status"] == "warning"

    def test_close_before_connect(self):
        t = StdioMCPTransport("dummy")
        t.close()
        assert t.is_connected() is False

    def test_call_tool_not_connected_raises(self):
        t = StdioMCPTransport("dummy")
        with pytest.raises(ConnectionError):
            t.call_tool("test", {})

    def test_check_connection_empty_command(self):
        t = StdioMCPTransport("")
        result = t.check_connection()
        assert result["status"] == "warning"

    def test_stderr_lines_are_empty_initially(self):
        t = StdioMCPTransport("dummy")
        lines = t.get_stderr_lines()
        assert isinstance(lines, list)
        assert len(lines) == 0


class TestStdioTransportWithFakeServer:
    @pytest.fixture
    def fake_server_script(self, tmp_path):
        script = tmp_path / "fake_mcp.py"
        script.write_text("""
import sys, json, time
sys.stderr.write("fake-mcp started\\n")
sys.stderr.flush()
for line in sys.stdin:
    line = line.strip()
    if not line: continue
    try: msg = json.loads(line)
    except: continue
    method = msg.get("method", "")
    rid = msg.get("id")
    if method == "initialize":
        sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2025-03-26","serverInfo":{"name":"fake-mcp"},"capabilities":{}}})+"\\n")
        sys.stdout.flush()
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":rid,"result":{"tools":[{"name":"find_events"},{"name":"create_event"}]}})+"\\n")
        sys.stdout.flush()
    elif method == "tools/call":
        tool_name = msg.get("params",{}).get("name","")
        if tool_name == "find_events":
            sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":"OK"}]}})+"\\n")
            sys.stdout.flush()
        else:
            sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":rid,"result":{"content":[{"type":"text","text":"UNKNOWN"}]}})+"\\n")
            sys.stdout.flush()
    else:
        sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":rid,"result":{}})+"\\n")
        sys.stdout.flush()
""")
        return f"python {script}"

    def test_connect_success(self, fake_server_script):
        t = StdioMCPTransport(fake_server_script)
        result = t.connect()
        assert result["status"] == "success"
        assert t.is_connected()
        t.close()

    def test_tools_list_after_connect(self, fake_server_script):
        t = StdioMCPTransport(fake_server_script)
        t.connect()
        tools = t.list_tools()
        assert "find_events" in tools
        assert "create_event" in tools
        t.close()

    def test_tool_call_works(self, fake_server_script):
        t = StdioMCPTransport(fake_server_script)
        t.connect()
        result = t.call_tool("find_events", {"days_ahead": 3})
        assert result == "OK"
        t.close()

    def test_close_releases_process(self, fake_server_script):
        t = StdioMCPTransport(fake_server_script)
        t.connect()
        t.close()
        assert t._process is None

    def test_stderr_drained(self, fake_server_script):
        t = StdioMCPTransport(fake_server_script)
        t.connect()
        time.sleep(0.2)  # let stderr reader catch up
        lines = t.get_stderr_lines()
        assert any("fake-mcp" in line for line in lines)
        t.close()

    def test_call_tool_after_close_raises(self, fake_server_script):
        t = StdioMCPTransport(fake_server_script)
        t.connect()
        t.close()
        with pytest.raises(ConnectionError):
            t.call_tool("test", {})

    def test_connect_timeout_detected(self):
        t = StdioMCPTransport("python -c \"import time; time.sleep(99)\"")
        t._connect_timeout = 1
        result = t.connect()
        assert result["status"] == "failed"
        t.close()

    def test_negotiate_bad_version(self, fake_server_script):
        t = StdioMCPTransport(fake_server_script)
        from calendar_planner.app.stdio_mcp_transport import MCPProtocolError
        with pytest.raises(MCPProtocolError):
            t._negotiate_version("2019-01-01")
        t.close()

    def test_stdout_reader_stops_on_close(self, fake_server_script):
        t = StdioMCPTransport(fake_server_script)
        t.connect()
        t.close()
        assert t._reader_stop.is_set()
        assert t._process is None


class TestStdioTransportTimeoutAndCancel:
    def test_custom_timeout_values(self):
        t = StdioMCPTransport("dummy")
        assert t._connect_timeout > 0
        assert t._tool_timeout > 0

    def test_send_request_timeout(self):
        import os
        os.environ["MCP_TOOL_TIMEOUT_SECONDS"] = "1"
        t = StdioMCPTransport("dummy")
        t._connected = True
        t._process = None
        with pytest.raises(ConnectionError):
            t._send_request("test", {}, timeout=1)
        os.environ.pop("MCP_TOOL_TIMEOUT_SECONDS", None)

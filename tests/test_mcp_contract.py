from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from calendar_planner.app.mcp_transport import (
    MCPProtocolError,
    MCPTransport,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_response(json_data, status=200, headers=None):
    resp = mock.MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    resp.status_code = status
    resp.headers = headers or {}
    return resp


def _mock_sse_response(lines, status=200, headers=None):
    resp = mock.MagicMock()
    resp.raise_for_status.return_value = None
    resp.status_code = status
    resp.headers = headers or {"Content-Type": "text/event-stream"}
    resp.iter_lines.return_value = lines
    return resp


def _build_jsonrpc(id_val, result=None, error=None):
    payload = {"jsonrpc": "2.0", "id": id_val}
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error
    return payload


def _init_result(protocol_version="2025-03-26", server_name="test-server"):
    return {
        "protocolVersion": protocol_version,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": {"name": server_name, "version": "1.0.0"},
    }


_NOTIFY_RESP = _mock_response({"jsonrpc": "2.0"})


def _patch_and_connect(transport, post_side_effect):
    """Patch requests.Session and call transport.connect() inside the patch."""
    with mock.patch("calendar_planner.app.mcp_transport.requests.Session") as sess_cls:
        mock_sess = mock.MagicMock()
        mock_sess.post.side_effect = post_side_effect
        mock_sess.headers = {}
        sess_cls.return_value = mock_sess
        transport.connect()
        return mock_sess


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 format
# ---------------------------------------------------------------------------


class TestJSONRPCFormat:
    def test_request_has_jsonrpc_field(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]
        mock_sess = _patch_and_connect(transport, post_side_effect)

        call_args_list = mock_sess.post.call_args_list
        assert len(call_args_list) >= 2

        init_call = call_args_list[0]
        sent_payload = init_call[1]["json"]
        assert sent_payload["jsonrpc"] == "2.0"
        assert "id" in sent_payload
        assert sent_payload["method"]

    def test_notification_has_no_id(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]
        mock_sess = _patch_and_connect(transport, post_side_effect)

        notification_found = False
        for call_args in mock_sess.post.call_args_list:
            payload = call_args[1]["json"]
            if "id" not in payload and payload.get("method") == "notifications/initialized":
                notification_found = True
                assert payload["jsonrpc"] == "2.0"
        assert notification_found, "notifications/initialized was not sent"


# ---------------------------------------------------------------------------
# Version negotiation
# ---------------------------------------------------------------------------


class TestVersionNegotiation:
    def test_accepts_2025_03_26(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]
        _patch_and_connect(transport, post_side_effect)

        assert transport.protocol_version == "2025-03-26"
        assert transport.is_connected()

    def test_rejects_unsupported_version(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2024-11-05"))),
        ]

        with pytest.raises(MCPProtocolError, match="not supported"):
            _patch_and_connect(transport, post_side_effect)

    def test_raises_when_server_init_fails(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, error={"code": -32600, "message": "Bad"})),
        ]

        with pytest.raises(MCPProtocolError):
            _patch_and_connect(transport, post_side_effect)


# ---------------------------------------------------------------------------
# initialized notification
# ---------------------------------------------------------------------------


class TestInitializedNotification:
    def test_notification_sent_after_initialize(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]
        mock_sess = _patch_and_connect(transport, post_side_effect)

        calls = mock_sess.post.call_args_list
        assert len(calls) == 3

        notification_call = calls[1]
        payload = notification_call[1]["json"]
        assert payload["method"] == "notifications/initialized"
        assert "id" not in payload
        assert payload["jsonrpc"] == "2.0"


# ---------------------------------------------------------------------------
# tools/list pagination
# ---------------------------------------------------------------------------


class TestToolsListPagination:
    def test_single_page_no_pagination(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": [{"name": "t1"}, {"name": "t2"}]})),
        ]
        _patch_and_connect(transport, post_side_effect)

        assert len(transport.tools) == 2
        assert transport.tools[0]["name"] == "t1"
        assert transport.tools[1]["name"] == "t2"

    def test_multi_page_with_next_cursor(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": [{"name": "t1"}], "nextCursor": "page2"})),
            _mock_response(_build_jsonrpc(3, {"tools": [{"name": "t2"}, {"name": "t3"}]})),
        ]
        _patch_and_connect(transport, post_side_effect)

        assert len(transport.tools) == 3
        names = [t["name"] for t in transport.tools]
        assert names == ["t1", "t2", "t3"]

    def test_passes_cursor_in_subsequent_request(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": [{"name": "t1"}], "nextCursor": "abc123"})),
            _mock_response(_build_jsonrpc(3, {"tools": [{"name": "t2"}]})),
        ]
        mock_sess = _patch_and_connect(transport, post_side_effect)

        tools_calls = []
        for call in mock_sess.post.call_args_list:
            payload = call[1]["json"]
            if payload.get("method") == "tools/list":
                tools_calls.append(payload)

        assert len(tools_calls) == 2
        assert "cursor" not in tools_calls[0].get("params", {})
        assert tools_calls[1]["params"]["cursor"] == "abc123"


# ---------------------------------------------------------------------------
# isError handling
# ---------------------------------------------------------------------------


class TestIsErrorHandling:
    def test_raises_on_iserror_in_content_list(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        error_response = _build_jsonrpc(1, {
            "content": [
                {"type": "text", "text": "Something went wrong", "isError": True},
            ],
        })
        transport._session.post.return_value = _mock_response(error_response)

        with pytest.raises(MCPProtocolError, match="isError"):
            transport.call_tool("bad_tool", {})

    def test_does_not_raise_when_iserror_is_false(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        ok_response = _build_jsonrpc(1, {
            "content": [
                {"type": "text", "text": '{"ok": true}', "isError": False},
            ],
        })
        transport._session.post.return_value = _mock_response(ok_response)

        result = transport.call_tool("good_tool", {})
        assert result == {"ok": True}

    def test_raises_on_iserror_single_content(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        error_response = _build_jsonrpc(1, {
            "content": {"type": "text", "text": "Fatal", "isError": True},
        })
        transport._session.post.return_value = _mock_response(error_response)

        with pytest.raises(MCPProtocolError, match="isError"):
            transport.call_tool("failing_tool", {})


# ---------------------------------------------------------------------------
# Auth / custom headers
# ---------------------------------------------------------------------------


class TestCustomHeaders:
    def test_applies_custom_headers_from_env(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]

        with mock.patch("calendar_planner.app.mcp_transport.requests.Session") as sess_cls:
            mock_sess = mock.MagicMock()
            mock_sess.headers = {}
            mock_sess.post.side_effect = post_side_effect
            sess_cls.return_value = mock_sess

            with mock.patch.dict(os.environ, {
                "MCP_CUSTOM_HEADERS": '{"Authorization": "Bearer secret", "X-Tenant": "acme"}',
            }):
                transport.connect()

            headers = mock_sess.headers
            assert headers.get("Authorization") == "Bearer secret"
            assert headers.get("X-Tenant") == "acme"

    def test_ignores_invalid_json_custom_headers(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]

        with mock.patch.dict(os.environ, {"MCP_CUSTOM_HEADERS": "not-json"}):
            _patch_and_connect(transport, post_side_effect)

        assert transport.is_connected()

    def test_no_headers_when_env_empty(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]

        with mock.patch.dict(os.environ, {}, clear=True):
            _patch_and_connect(transport, post_side_effect)

        assert transport.is_connected()


# ---------------------------------------------------------------------------
# Server capabilities storage
# ---------------------------------------------------------------------------


class TestServerCapabilities:
    def test_stores_capabilities_from_initialize(self):
        transport = MCPTransport("http://fake-mcp.local")
        init_result = _init_result("2025-03-26")
        init_result["capabilities"] = {
            "tools": {"listChanged": True},
            "resources": {"subscribe": False},
        }
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, init_result)),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]
        _patch_and_connect(transport, post_side_effect)

        caps = transport.server_capabilities
        assert caps["tools"]["listChanged"] is True
        assert caps["resources"]["subscribe"] is False

    def test_empty_capabilities_when_omitted(self):
        transport = MCPTransport("http://fake-mcp.local")
        init_result = _init_result("2025-03-26")
        del init_result["capabilities"]
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, init_result)),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]
        _patch_and_connect(transport, post_side_effect)

        assert transport.server_capabilities == {}


# ---------------------------------------------------------------------------
# Container: fixture fallback policy
# ---------------------------------------------------------------------------


class TestContainerFixturePolicy:
    def test_rejects_fixture_in_production_env(self):
        os.environ["APP_ENV"] = "production"
        os.environ["MCP_ENABLED"] = "false"

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings

        settings = Settings()
        container = AppContainer(settings)
        container.init_mcp()

        with pytest.raises(RuntimeError, match="MCP not available"):
            container.get_calendar_gateway()

        with pytest.raises(RuntimeError, match="MCP not available"):
            container.get_directory_gateway()

    def test_rejects_fixture_in_development_env(self):
        os.environ["APP_ENV"] = "development"
        os.environ["MCP_ENABLED"] = "false"

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings

        settings = Settings()
        container = AppContainer(settings)
        container.init_mcp()

        with pytest.raises(RuntimeError, match="MCP not available"):
            container.get_calendar_gateway()

        with pytest.raises(RuntimeError, match="MCP not available"):
            container.get_directory_gateway()

    def test_allows_fixture_in_test_env(self):
        os.environ["APP_ENV"] = "test"
        os.environ["MCP_ENABLED"] = "false"

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings

        settings = Settings()
        container = AppContainer(settings)
        container.init_mcp()

        cal = container.get_calendar_gateway()
        assert cal is not None

        dir_gw = container.get_directory_gateway()
        assert dir_gw is not None

    def test_returns_mcp_gateway_when_initialized(self):
        os.environ["APP_ENV"] = "production"

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings

        settings = Settings()
        container = AppContainer(settings)

        container._mcp_initialized = True
        container._calendar_gateway = mock.MagicMock()
        container._directory_gateway = mock.MagicMock()

        cal = container.get_calendar_gateway()
        assert cal is container._calendar_gateway

        dir_gw = container.get_directory_gateway()
        assert dir_gw is container._directory_gateway

    def test_init_mcp_stores_disabled_state(self):
        os.environ["APP_ENV"] = "production"
        os.environ["MCP_ENABLED"] = "false"

        from calendar_planner.app.container import AppContainer
        from calendar_planner.app.settings import Settings

        settings = Settings()
        container = AppContainer(settings)

        result = container.init_mcp()
        assert result["status"] == "warning"
        assert container._mcp_disabled_or_unavailable is True
        assert container._mcp_initialized is False


# ---------------------------------------------------------------------------
# SSE response parsing
# ---------------------------------------------------------------------------


class TestSSEResponseParsing:
    def test_parse_sse_stream_with_data_lines(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        sse_lines = [
            'event: message',
            'data: {"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"t1"}]}}',
            '',
        ]
        mock_resp = _mock_sse_response(sse_lines)
        transport._session.post.return_value = mock_resp

        result = transport._send_request("tools/list", {})
        assert result["tools"][0]["name"] == "t1"

    def test_parse_sse_stream_with_done_termination(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        sse_lines = [
            'data: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}',
            'data: [DONE]',
        ]
        mock_resp = _mock_sse_response(sse_lines)
        transport._session.post.return_value = mock_resp

        result = transport._send_request("tools/call", {"name": "t", "arguments": {}})
        assert result == {"ok": True}

    def test_parse_sse_stream_with_empty_data_termination(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        sse_lines = [
            'data: {"jsonrpc":"2.0","id":1,"result":{"a":1}}',
            'data:',
        ]
        mock_resp = _mock_sse_response(sse_lines)
        transport._session.post.return_value = mock_resp

        result = transport._send_request("tools/call", {"name": "t", "arguments": {}})
        assert result == {"a": 1}

    def test_parse_sse_stream_returns_empty_dict_for_empty_stream(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        mock_resp = _mock_sse_response([])
        transport._session.post.return_value = mock_resp

        result = transport._send_request("tools/list", {})
        assert result == {}

    def test_parse_sse_stream_collects_multiple_results(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        sse_lines = [
            'data: {"a":1}',
            'data: {"b":2}',
            'data:',
        ]
        mock_resp = _mock_sse_response(sse_lines)
        transport._session.post.return_value = mock_resp

        result = transport._send_request("tools/list", {})
        assert isinstance(result, list)
        assert result == [{"a": 1}, {"b": 2}]


# ---------------------------------------------------------------------------
# Session ID management
# ---------------------------------------------------------------------------


class TestSessionIdManagement:
    def test_extracts_mcp_session_id_from_response_headers(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._session.headers = {}
        transport._connected = True

        mock_resp = _mock_response(
            _build_jsonrpc(1, _init_result("2025-03-26")),
            headers={"Mcp-Session-Id": "abc-123-session"},
        )
        transport._session.post.return_value = mock_resp

        transport._send_request("initialize", {"protocolVersion": "2025-03-26"})
        assert transport._mcp_session_id == "abc-123-session"
        assert transport._session.headers.get("Mcp-Session-Id") == "abc-123-session"

    def test_replays_session_id_on_subsequent_requests(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._session.headers = {}
        transport._connected = True

        resp1 = _mock_response(
            _build_jsonrpc(1, _init_result("2025-03-26")),
            headers={"Mcp-Session-Id": "session-xyz"},
        )
        resp2 = _mock_response(
            _build_jsonrpc(2, {"tools": []}),
            headers={},
        )
        transport._session.post.side_effect = [resp1, resp2]

        transport._send_request("initialize", {"protocolVersion": "2025-03-26"})
        transport._send_request("tools/list", {})

        sent_headers = transport._session.headers
        assert sent_headers.get("Mcp-Session-Id") == "session-xyz"

    def test_does_not_overwrite_session_id_with_none(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._session.headers = {"Mcp-Session-Id": "existing-id"}
        transport._mcp_session_id = "existing-id"
        transport._connected = True

        mock_resp = _mock_response(
            _build_jsonrpc(1, {"tools": []}),
            headers={},
        )
        transport._session.post.return_value = mock_resp

        transport._send_request("tools/list", {})
        assert transport._mcp_session_id == "existing-id"


# ---------------------------------------------------------------------------
# Top-level isError handling
# ---------------------------------------------------------------------------


class TestTopLevelIsError:
    def test_raises_on_top_level_iserror_in_send_request(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        error_response = _build_jsonrpc(1, {
            "isError": True,
            "error": "Something bad happened",
        })
        transport._session.post.return_value = _mock_response(error_response)

        with pytest.raises(MCPProtocolError, match="top-level isError"):
            transport._send_request("tools/call", {"name": "t", "arguments": {}})

    def test_does_not_raise_when_iserror_is_false_top_level(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        ok_response = _build_jsonrpc(1, {"isError": False, "content": []})
        transport._session.post.return_value = _mock_response(ok_response)

        result = transport._send_request("tools/call", {"name": "t", "arguments": {}})
        assert result == {"isError": False, "content": []}

    def test_call_tool_raises_on_top_level_iserror(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        error_response = _build_jsonrpc(1, {
            "isError": True,
            "error": "Tool-level failure",
        })
        transport._session.post.return_value = _mock_response(error_response)

        with pytest.raises(MCPProtocolError, match="top-level isError"):
            transport.call_tool("bad_tool", {})


# ---------------------------------------------------------------------------
# Notification handling (HTTP 202 / non-2xx)
# ---------------------------------------------------------------------------


class TestNotificationHandling:
    def test_notification_accepts_202_status(self, caplog):
        caplog.set_level(logging.INFO)
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        mock_resp = mock.MagicMock()
        mock_resp.status_code = 202
        mock_resp.text = ""
        transport._session.post.return_value = mock_resp

        transport._send_notification("notifications/initialized")

        assert "accepted (202)" in caplog.text

    def test_notification_logs_warning_on_non_2xx(self, caplog):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = mock.MagicMock()
        transport._connected = True

        mock_resp = mock.MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal error"
        transport._session.post.return_value = mock_resp

        transport._send_notification("notifications/initialized")

        assert "non-2xx" in caplog.text

    def test_notification_sent_with_no_id_field(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _mock_response({"jsonrpc": "2.0"}, status=202),
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]
        mock_sess = _patch_and_connect(transport, post_side_effect)

        notification_call = None
        for call_args in mock_sess.post.call_args_list:
            payload = call_args[1]["json"]
            if payload.get("method") == "notifications/initialized":
                notification_call = payload
                break
        assert notification_call is not None
        assert "id" not in notification_call


# ---------------------------------------------------------------------------
# Accept header presence
# ---------------------------------------------------------------------------


class TestAcceptHeader:
    def test_accept_header_set_on_session(self):
        transport = MCPTransport("http://fake-mcp.local")
        post_side_effect = [
            _mock_response(_build_jsonrpc(1, _init_result("2025-03-26"))),
            _NOTIFY_RESP,
            _mock_response(_build_jsonrpc(2, {"tools": []})),
        ]

        with mock.patch("calendar_planner.app.mcp_transport.requests.Session") as sess_cls:
            mock_sess = mock.MagicMock()
            mock_sess.headers = {}
            mock_sess.post.side_effect = post_side_effect
            sess_cls.return_value = mock_sess

            transport.connect()

            headers = mock_sess.headers
            assert "Accept" in headers
            assert "text/event-stream" in headers["Accept"]
            assert "application/json" in headers["Accept"]

    def test_accept_header_present_in_fallback_session_creation(self):
        transport = MCPTransport("http://fake-mcp.local")
        transport._session = None
        transport._connected = True

        mock_resp = _mock_response(_build_jsonrpc(1, {"tools": []}))
        with mock.patch("calendar_planner.app.mcp_transport.requests.Session") as sess_cls:
            mock_sess = mock.MagicMock()
            mock_sess.headers = {}
            mock_sess.post.return_value = mock_resp
            sess_cls.return_value = mock_sess

            transport._send_request("tools/list", {})

            assert "Accept" in mock_sess.headers
            assert "text/event-stream" in mock_sess.headers["Accept"]
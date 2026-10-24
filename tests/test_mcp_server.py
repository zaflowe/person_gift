"""Tests for the Personal Telemetry MCP adapter."""
import asyncio
import pytest
from mcp.server.fastmcp import FastMCP
from starlette.testclient import TestClient

import app.mcp_server as mcp_server
from app.mcp_server import AgentKeyAuthMiddleware, mcp
from app.config import settings


@pytest.mark.parametrize(
    "host,origin,expected_status",
    [
        ("telemetry.example.com", None, 200),
        ("untrusted.example.com", None, 421),
        ("telemetry.example.com", "https://untrusted.example.com", 403),
    ],
)
def test_public_transport_keeps_host_and_origin_checks(monkeypatch, host, origin, expected_status):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "telemetry.example.com, telemetry.example.com:443")
    monkeypatch.setenv("MCP_ALLOWED_ORIGINS", "https://telemetry.example.com")
    monkeypatch.setattr(settings, "telemetry_agent_key", "test-agent-key")
    server = FastMCP(
        "transport-test", streamable_http_path="/", stateless_http=True,
        json_response=True, transport_security=mcp_server._transport_security(),
    )
    headers = {
        "Authorization": "Bearer test-agent-key",
        "Accept": "application/json, text/event-stream",
    }
    if origin:
        headers["Origin"] = origin
    with TestClient(AgentKeyAuthMiddleware(server.streamable_http_app()), base_url=f"https://{host}") as client:
        response = client.post("/", headers=headers, json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "transport-test", "version": "1"}},
        })
    assert response.status_code == expected_status
    if expected_status == 200:
        assert "result" in response.json()


class _DummyApp:
    def __init__(self):
        self.called = False

    async def __call__(self, scope, receive, send):
        self.called = True


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def _http_scope(auth_header: bytes | None) -> dict:
    headers = []
    if auth_header is not None:
        headers.append((b"authorization", auth_header))
    return {"type": "http", "headers": headers}


def _capture():
    sent = []

    async def send(message):
        sent.append(message)

    return sent, send


def test_mcp_tools_registered():
    expected = {
        "get_context",
        "get_today",
        "search_life",
        "get_state",
        "update_state",
        "add_life_note",
        "get_metrics",
        "add_metric",
        "get_analysis_status",
        "correct_event",
    }
    tools = _run(mcp.list_tools())
    registered = {tool.name for tool in tools}
    assert expected <= registered


def test_auth_rejects_missing_key():
    app = _DummyApp()
    guard = AgentKeyAuthMiddleware(app)
    sent, send = _capture()
    _run(guard(_http_scope(None), None, send))
    assert not app.called
    assert sent[0]["status"] == 401


def test_auth_rejects_wrong_key():
    app = _DummyApp()
    guard = AgentKeyAuthMiddleware(app)
    sent, send = _capture()
    _run(guard(_http_scope(b"Bearer definitely-wrong-key"), None, send))
    assert not app.called
    assert sent[0]["status"] == 401


def test_auth_accepts_agent_key(monkeypatch):
    monkeypatch.setattr(settings, "telemetry_agent_key", "test-agent-key")
    app = _DummyApp()
    guard = AgentKeyAuthMiddleware(app)
    sent, send = _capture()
    _run(guard(_http_scope(b"Bearer test-agent-key"), None, send))
    assert app.called
    assert sent == []


def test_auth_rejects_when_server_key_unset(monkeypatch):
    monkeypatch.setattr(settings, "telemetry_agent_key", "")
    app = _DummyApp()
    guard = AgentKeyAuthMiddleware(app)
    sent, send = _capture()
    _run(guard(_http_scope(b"Bearer anything"), None, send))
    assert not app.called
    assert sent[0]["status"] == 401


def _patch_request(monkeypatch, calls):
    async def fake_request(method, path, params=None, payload=None):
        calls["call"] = {"method": method, "path": path, "params": params, "payload": payload}
        return {"ok": True}

    monkeypatch.setattr(mcp_server, "_request", fake_request)


def test_request_auth_header_uses_agent_key(monkeypatch):
    monkeypatch.setattr(settings, "telemetry_agent_key", "test-agent-key")
    assert mcp_server._headers()["Authorization"] == "Bearer test-agent-key"


def test_get_context_maps_to_rest(monkeypatch):
    calls = {}
    _patch_request(monkeypatch, calls)
    assert _run(mcp_server.get_context(event_hours=10, note_days=5)) == {"ok": True}
    call = calls["call"]
    assert call["method"] == "GET"
    assert call["path"] == "/telemetry/context"
    assert call["params"] == {"event_hours": 10, "note_days": 5}


def test_search_life_maps_query(monkeypatch):
    calls = {}
    _patch_request(monkeypatch, calls)
    _run(mcp_server.search_life("3D雷达"))
    call = calls["call"]
    assert call["path"] == "/telemetry/search"
    assert call["params"]["q"] == "3D雷达"


def test_update_state_maps_key_and_value(monkeypatch):
    calls = {}
    _patch_request(monkeypatch, calls)
    _run(mcp_server.update_state("current_project", "douyin integration"))
    call = calls["call"]
    assert call["method"] == "PUT"
    assert call["path"] == "/telemetry/state/current_project"
    assert call["payload"] == {"value": "douyin integration", "source": "gpt"}


def test_add_life_note_defaults(monkeypatch):
    calls = {}
    _patch_request(monkeypatch, calls)
    _run(mcp_server.add_life_note("决定申请3D激光雷达", importance=0.9))
    call = calls["call"]
    assert call["method"] == "POST"
    assert call["path"] == "/telemetry/notes"
    assert call["payload"]["text"] == "决定申请3D激光雷达"
    assert call["payload"]["tags"] == []
    assert call["payload"]["importance"] == 0.9


def test_add_metric_defaults_observed_at(monkeypatch):
    calls = {}
    _patch_request(monkeypatch, calls)
    _run(mcp_server.add_metric("douyin", "douyin.followers.total", 1234.0))
    call = calls["call"]
    assert call["method"] == "POST"
    assert call["path"] == "/telemetry/metrics"
    assert call["payload"]["metric"] == "douyin.followers.total"
    assert call["payload"]["observed_at"]  # auto-filled ISO timestamp

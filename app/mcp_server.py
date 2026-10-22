"""MCP adapter for Personal Telemetry.

A thin MCP layer over the existing telemetry REST API. It is mounted into the
main FastAPI app at /mcp so ChatGPT (or any MCP client) can read and write
telemetry through the same backend and database. No new storage, no separate
service.

Security model:
- The MCP endpoint requires the telemetry AGENT key as an HTTP Bearer token.
- The key lives only in server-side environment configuration. It is never
  returned to clients, never written to logs, and never exposed to the
  frontend or Git.
- iPhone/collectors keep using the separate ingest key against the REST API.
"""
from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

from app.config import settings

# Internal base URL of the telemetry REST API. The adapter normally runs
# in-process inside the backend container, so loopback is correct. Override
# with TELEMETRY_BASE_URL only if it is ever split into its own service.
TELEMETRY_BASE_URL = os.environ.get("TELEMETRY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _transport_security() -> TransportSecuritySettings:
    """Trust configured public hosts while keeping DNS rebinding checks on."""
    def configured(name: str) -> list[str]:
        return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"] + configured("MCP_ALLOWED_HOSTS"),
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]
        + configured("MCP_ALLOWED_ORIGINS"),
    )

# stateless_http: the backend runs multiple gunicorn workers, so MCP sessions
# must not be pinned to one process. json_response keeps replies as plain JSON
# for maximum client compatibility.
mcp = FastMCP(
    "personal-telemetry",
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
    transport_security=_transport_security(),
)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.telemetry_agent_key}"}


async def _request(
    method: str,
    path: str,
    params: Optional[dict[str, Any]] = None,
    payload: Optional[dict[str, Any]] = None,
) -> Any:
    """Call the internal telemetry REST API.

    Async on purpose: the adapter normally calls back into the same backend
    process over loopback, so blocking HTTP here could deadlock the worker.
    """
    async with httpx.AsyncClient(base_url=TELEMETRY_BASE_URL, timeout=20) as client:
        resp = await client.request(
            method,
            path,
            headers=_headers(),
            params={k: v for k, v in (params or {}).items() if v is not None},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def get_context(event_hours: int = 72, note_days: int = 30) -> dict[str, Any]:
    """Get the user's current personal context: current state, important life
    notes, recent raw events and latest metrics. Call this FIRST whenever you
    need to understand the user's current situation, projects or goals."""
    return await _request("GET", "/telemetry/context", params={"event_hours": event_hours, "note_days": note_days})


@mcp.tool()
async def get_today() -> dict[str, Any]:
    """Get today's summary: events, notes, metrics and detected spending (CNY)
    for the current local day. Test events are excluded from spending. Event
    analysis is an AI proposal unless confirmed_by_user is true; never present
    an unconfirmed activity as fact. Use for 'what did I spend today'."""
    return await _request("GET", "/telemetry/today")


@mcp.tool()
async def search_life(query: str, limit: int = 50) -> dict[str, Any]:
    """Search life notes, raw events and effective event interpretations by
    keyword (including 午饭/打车). Respect confirmed_by_user: AI guesses are not
    facts. Use for questions like 'when did I first mention wanting a 3D lidar'."""
    return await _request("GET", "/telemetry/search", params={"q": query, "limit": limit})


@mcp.tool()
async def get_analysis_status() -> dict[str, Any]:
    """Read DeepSeek interpretation availability, durable queue counts and
    user correction count. No secrets. Learning uses retrieved history and
    confirmed corrections, not model weight training."""
    return await _request("GET", "/telemetry/analysis/status")


@mcp.tool()
async def correct_event(event_id: str, category: str, activity: str, summary: str,
                        merchant: Optional[str] = None, comment: Optional[str] = None) -> dict[str, Any]:
    """ONLY when the user explicitly corrects or confirms an event's purpose,
    save their interpretation. First find the exact event ID via get_today or
    search_life; never guess an ID. Preserve raw data. category: food, transport,
    shopping, bills, income, refund, transfer, other, unknown. activity: breakfast,
    lunch, dinner, snack, taxi, public_transit, groceries, shopping, bill_payment,
    income, refund, transfer, other, unknown. The correction becomes authoritative
    and informs future similar events. Do not write inferred preferences."""
    return await _request("PUT", f"/telemetry/events/{event_id}/analysis", payload={
        "category": category, "activity": activity, "summary": summary,
        "merchant": merchant, "comment": comment,
    })


@mcp.tool()
async def get_state() -> dict[str, Any]:
    """Read the user's current personal state (current_project, current_goal,
    research direction, desires, tools, etc.) as key -> value entries."""
    return await _request("GET", "/telemetry/state")


@mcp.tool()
async def update_state(key: str, value: Any) -> dict[str, Any]:
    """Update one entry of the user's current state, e.g. key='current_project'
    value='Douyin OpenAPI integration'. Only update when the user clearly
    states a change; the value can be any JSON value."""
    return await _request("PUT", f"/telemetry/state/{key}", payload={"value": value, "source": "gpt"})


@mcp.tool()
async def add_life_note(text: str, tags: Optional[list[str]] = None, importance: float = 0.5) -> dict[str, Any]:
    """Save a long-term semantic note about the user's life: decisions, plans,
    meaningful events. importance is 0.0-1.0 (use >=0.7 only for major items).
    Do not save trivial chat content."""
    return await _request("POST", "/telemetry/notes", payload={"text": text, "tags": tags or [], "importance": importance, "source": "gpt"})


@mcp.tool()
async def get_metrics(
    metric: Optional[str] = None,
    source: Optional[str] = None,
    hours: int = 168,
    limit: int = 500,
) -> dict[str, Any]:
    """Query numeric time series, e.g. metric='douyin.followers.total' or
    source='douyin'. hours is the look-back window (default 7 days)."""
    return await _request("GET", "/telemetry/metrics", params={"metric": metric, "source": source, "hours": hours, "limit": limit})


@mcp.tool()
async def add_metric(
    source: str,
    metric: str,
    value: float,
    unit: Optional[str] = None,
    dimensions: Optional[dict[str, Any]] = None,
    observed_at: Optional[str] = None,
) -> dict[str, Any]:
    """Write one numeric metric observation. observed_at is ISO-8601; defaults
    to now (UTC) when omitted. dimensions can hold labels like video_id."""
    ts = observed_at or datetime.now(timezone.utc).isoformat()
    return await _request(
        "POST",
        "/telemetry/metrics",
        payload={"source": source, "metric": metric, "value": value, "unit": unit, "dimensions": dimensions, "observed_at": ts},
    )


class AgentKeyAuthMiddleware:
    """Pure-ASGI guard: only requests bearing the telemetry agent key may
    reach the MCP endpoint. Returns 401 without leaking any key material."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            auth = headers.get(b"authorization", b"").decode("latin-1")
            token = auth[7:].strip() if auth.startswith("Bearer ") else ""
            key = settings.telemetry_agent_key
            if not (token and key and hmac.compare_digest(token, key)):
                response = JSONResponse({"detail": "invalid agent key"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def build_mcp_app() -> Any:
    """Return the MCP ASGI app wrapped in agent-key auth, ready to mount."""
    return AgentKeyAuthMiddleware(mcp.streamable_http_app())

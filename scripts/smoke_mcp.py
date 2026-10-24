"""Smoke test for the Personal Telemetry MCP endpoint.

Verifies the full chain a GPT client depends on:
  1. Unauthenticated requests are rejected (401).
  2. MCP initialize + tools/list works with the agent key.
  3. Optionally, one real tool call (get_today) against live data.

Usage after deploying to Aliyun:

    # Read TELEMETRY_AGENT_KEY from the environment, without putting it in argv.
    python scripts/smoke_mcp.py --base-url https://YOUR_DOMAIN

Local check of protocol + auth only (no live REST data):

    python scripts/smoke_mcp.py --base-url http://127.0.0.1:8000 --agent-key local-test --skip-calls
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import requests

PROTOCOL_VERSION = "2025-06-18"


def _headers(agent_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {agent_key}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }


def _post(url: str, agent_key: str, payload: dict) -> requests.Response:
    return requests.post(url, headers=_headers(agent_key), json=payload, timeout=30)


def _check(label: str, ok: bool, detail: str = "") -> bool:
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  ({detail})" if detail else ""))
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="e.g. https://your-domain (no trailing slash)")
    parser.add_argument("--agent-key", help="Legacy option; prefer an environment variable to keep secrets out of argv")
    parser.add_argument("--agent-key-env", default="TELEMETRY_AGENT_KEY", help="Name of the environment variable holding the agent key")
    parser.add_argument("--skip-calls", action="store_true", help="skip live tool calls (protocol check only)")
    args = parser.parse_args()
    agent_key = args.agent_key or os.environ.get(args.agent_key_env, "")
    if not agent_key:
        parser.error(f"set {args.agent_key_env} in the environment before running the check")

    url = args.base_url.rstrip("/") + "/mcp/"
    ok = True

    # 1. Auth must be enforced.
    resp = requests.post(url, json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}, timeout=15)
    ok &= _check("unauthenticated request rejected", resp.status_code == 401, f"status={resp.status_code}")

    # 2. Initialize handshake.
    resp = _post(url, agent_key, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "smoke-mcp", "version": "0.1"},
        },
    })
    init_ok = resp.status_code == 200 and "result" in resp.json()
    ok &= _check("initialize", init_ok, f"status={resp.status_code}")
    if not init_ok:
        print(resp.text[:500])
        return 1
    print(f"      server: {json.dumps(resp.json()['result'].get('serverInfo', {}), ensure_ascii=False)}")

    _post(url, agent_key, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    # 3. Tool list.
    resp = _post(url, agent_key, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    names = [t["name"] for t in resp.json().get("result", {}).get("tools", [])] if resp.status_code == 200 else []
    expected = {"get_context", "get_today", "search_life", "get_state", "update_state", "add_life_note", "get_metrics", "add_metric", "get_analysis_status", "correct_event"}
    ok &= _check("tools/list exposes all tools", expected <= set(names), ",".join(sorted(names)))

    # 4. One real read.
    if not args.skip_calls:
        resp = _post(url, agent_key, {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "get_today", "arguments": {}}})
        body = resp.json()
        call_ok = resp.status_code == 200 and not body.get("result", {}).get("isError", True)
        ok &= _check("tools/call get_today", call_ok, f"status={resp.status_code}")
        if not call_ok:
            print(json.dumps(body, ensure_ascii=False)[:500])

    print("\nResult:", "ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

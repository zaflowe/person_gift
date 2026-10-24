"""Parse visible Alipay rows and retain an idempotent, versioned local ledger."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo


def parse_row(row: dict) -> dict:
    cells = [str(x).strip() for x in row.get("cells", [])]
    link = next((x for x in row.get("links", [])
                 if "/record/detail/simpleDetail.htm" in x.get("href", "")), None)
    if not link:
        raise ValueError("missing_official_transaction_link")
    url = urlparse(link["href"])
    if url.hostname != "consumeprod.alipay.com":
        raise ValueError("unexpected_detail_host")
    query = parse_qs(url.query)
    trade_id = query.get("bizInNo", [""])[0]
    biz_type = query.get("bizType", [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", trade_id):
        raise ValueError("invalid_transaction_id")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", biz_type):
        raise ValueError("invalid_transaction_type")
    if not cells:
        raise ValueError("missing_cells")
    when = re.search(r"(20\d{2})[.\-/](\d{2})[.\-/](\d{2})\s+(\d{2}):(\d{2})(?::(\d{2}))?", cells[0])
    if not when:
        raise ValueError("missing_creation_time")
    parts = [int(x or 0) for x in when.groups()]
    created = datetime(*parts, tzinfo=ZoneInfo("Asia/Shanghai"))
    precision = "minute" if when[6] is None else "second"
    detailed_time = query.get("gmtBizCreate", [""])[0]
    if re.fullmatch(r"\d{14}", detailed_time):
        detailed = datetime.strptime(detailed_time, "%Y%m%d%H%M%S").replace(tzinfo=created.tzinfo)
        if detailed.strftime("%Y%m%d%H%M") == created.strftime("%Y%m%d%H%M"):
            created, precision = detailed, "second"
    amounts = [re.fullmatch(r"([+-])\s*[¥￥]?\s*(\d[\d,]*(?:\.\d{1,2})?)", c) for c in cells]
    amounts = [x for x in amounts if x]
    if len(amounts) != 1:
        raise ValueError("ambiguous_signed_amount")
    amount = amounts[0]
    try:
        number = Decimal(amount[2].replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError("invalid_amount") from exc
    cents = int(number * 100)
    if number < 0 or cents > 10**14:
        raise ValueError("amount_out_of_range")
    headers = row.get("headers", [])
    counterparty = ""
    for index, header in enumerate(headers):
        if str(header).strip() == "对方" and index < len(cells):
            counterparty = cells[index]
    known_status = {"交易成功", "交易关闭", "交易失败", "等待付款", "等待买家付款", "等待卖家发货", "等待买家确认收货", "退款成功", "退款处理中", "等待确认收货"}
    status = next((c for c in cells if c in known_status), "unknown")
    result = {
        "external_id": f"{biz_type}:{trade_id}", "trade_id": trade_id,
        "biz_type": biz_type, "created_at": created.isoformat(),
        "time_precision": precision, "currency": "CNY", "amount_cents": cents,
        "direction": "outflow" if amount[1] == "-" else "inflow",
        "name": link.get("text", "").strip(), "counterparty": counterparty,
        "status": status,
        # Direction is a cash-flow sign, not an accounting classification.
        "raw": {"headers": headers, "cells": cells, "detail_url": link["href"]},
    }
    result["content_hash"] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return result


class Ledger:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS transactions (
            external_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
            amount_cents INTEGER NOT NULL, direction TEXT NOT NULL,
            name TEXT NOT NULL, status TEXT NOT NULL, content_hash TEXT NOT NULL,
            data_json TEXT NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1);
          CREATE TABLE IF NOT EXISTS transaction_versions (
            id INTEGER PRIMARY KEY, external_id TEXT NOT NULL, observed_at TEXT NOT NULL,
            content_hash TEXT NOT NULL, data_json TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT NOT NULL,
            state TEXT NOT NULL, metadata_json TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS session_events (
            id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, state TEXT NOT NULL,
            metadata_json TEXT NOT NULL);
        """)

    def save(self, rows: list[dict], observed_at: str) -> dict:
        new = changed = 0
        with self.db:
            for row in rows:
                old = self.db.execute("SELECT content_hash FROM transactions WHERE external_id=?", (row["external_id"],)).fetchone()
                encoded = json.dumps(row, ensure_ascii=False, sort_keys=True)
                if old is None:
                    self.db.execute("INSERT INTO transactions(external_id,created_at,amount_cents,direction,name,status,content_hash,data_json,first_seen,last_seen) VALUES(?,?,?,?,?,?,?,?,?,?)", (row["external_id"], row["created_at"], row["amount_cents"], row["direction"], row["name"], row["status"], row["content_hash"], encoded, observed_at, observed_at))
                    new += 1
                elif old[0] != row["content_hash"]:
                    self.db.execute("UPDATE transactions SET created_at=?,amount_cents=?,direction=?,name=?,status=?,content_hash=?,data_json=?,last_seen=?,version=version+1 WHERE external_id=?", (row["created_at"], row["amount_cents"], row["direction"], row["name"], row["status"], row["content_hash"], encoded, observed_at, row["external_id"]))
                    changed += 1
                else:
                    self.db.execute("UPDATE transactions SET last_seen=? WHERE external_id=?", (observed_at, row["external_id"]))
                if old is None or old[0] != row["content_hash"]:
                    self.db.execute("INSERT INTO transaction_versions(external_id,observed_at,content_hash,data_json) VALUES(?,?,?,?)", (row["external_id"], observed_at, row["content_hash"], encoded))
        return {"new": new, "changed": changed, "total": self.db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]}

    def record(self, table: str, observed_at: str, state: str, metadata: dict, started_at=None):
        if table not in {"runs", "session_events"}:
            raise ValueError("invalid_log_table")
        encoded = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        with self.db:
            if table == "runs":
                self.db.execute("INSERT INTO runs(started_at,finished_at,state,metadata_json) VALUES(?,?,?,?)", (started_at or observed_at, observed_at, state, encoded))
            else:
                self.db.execute("INSERT INTO session_events(observed_at,state,metadata_json) VALUES(?,?,?)", (observed_at, state, encoded))

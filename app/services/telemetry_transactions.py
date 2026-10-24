"""Deterministic payment amounts and conservative cross-source reconciliation."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

NUMBER = r"([0-9]+(?:\.[0-9]{1,2})?)"
ACTION = r"(?:成功付款|付款|支付|支出|消费|扣款|收款|到账|退款|退回|转账|转给|收到)"


def parse_transaction(text: str) -> Optional[dict]:
    if not text or re.search(r"登录提醒|验证码|记账日报", text):
        return None
    candidates = []
    for clause in re.split(r"[，。；;\n]", text):
        clause = clause.strip()
        if not re.search(ACTION, clause) or re.match(r"(?:点击)?(?:领取?|可领|立减|奖励|优惠)", clause):
            continue
        patterns = [
            ACTION + r"\s*(?:人民币|金额为?|了)?\s*[¥￥]?\s*" + NUMBER + r"\s*元",
            ACTION + r"\s*[¥￥]\s*" + NUMBER + r"(?![0-9.])",
            NUMBER + r"\s*元(?:的)?(?:免密/自动扣款支付|免密支付|自动扣款|支出|消费|付款|扣款|收款|到账|退款|已退回)",
            r"(?:有一笔|本次|本笔)\s*[¥￥]?\s*" + NUMBER + r"\s*元",
            ACTION + r"\s*" + NUMBER + r"\s*$",
        ]
        for pattern in patterns:
            matches = list(re.finditer(pattern, clause))
            if matches:
                amounts = {Decimal(m.group(1)) for m in matches}
                if len(amounts) != 1:
                    return None
                kind = "refund" if re.search(r"退款|退回|已退", clause) else "transfer" if re.search(r"转账|转给", clause) else "income" if re.search(r"收款|到账|收到", clause) else "expense"
                candidates.append((next(iter(amounts)), kind))
                break
    if not candidates or len(set(candidates)) != 1:
        return None
    amount, kind = candidates[0]
    return {"type": kind, "amount": float(amount), "amount_cents": int(amount * 100), "currency": "CNY", "parser": "rules-v2"}


def notification_time(text: str, received: datetime, zone_name: str) -> Optional[datetime]:
    """Use an explicit notification transaction date, never its account digits."""
    if not parse_transaction(text):
        return None
    match = re.search(r"(?:(20\d{2})年)?(\d{1,2})月(\d{1,2})日\s*(\d{1,2})(?:时|:)(\d{1,2})(?:分)?", text)
    if not match:
        return None
    zone = ZoneInfo(zone_name)
    local = received.replace(tzinfo=timezone.utc).astimezone(zone) if received.tzinfo is None else received.astimezone(zone)
    year, month, day, hour, minute = match.groups()
    try:
        years = [int(year)] if year else [local.year - 1, local.year, local.year + 1]
        options = [datetime(y, int(month), int(day), int(hour), int(minute), tzinfo=zone) for y in years]
        found = min(options, key=lambda value: abs(value - local))
    except ValueError:
        return None
    return found.astimezone(timezone.utc).replace(tzinfo=None) if abs(found - local) <= timedelta(days=7) else None


def event_time(event):
    return event.occurred_at or event.received_at


def accounting(events):
    """Keep originals; match only mutually unique Alipay amount/time pairs.

    Ambiguous pairs stay visible for review and are excluded from the total.
    Multiple real web trades with equal amounts are never collapsed.
    """
    values = {e.id: json.loads(e.normalized_json) if e.normalized_json else None for e in events}
    result = {}
    web = [e for e in events if e.source == "alipay_web"]
    for e in events:
        n = values[e.id]
        payload = json.loads(e.payload_json) if e.payload_json else {}
        reason = "test_event" if e.kind in {"deployment_test", "analysis_test", "test"} or payload.get("test") else "not_a_transaction" if not n or n.get("amount") is None else n.get("exclusion_reason")
        result[e.id] = {"included": not bool(reason), "exclusion_reason": reason, "duplicate_of": None}
    candidates = {}
    for e in events:
        if e.source == "alipay_web" or not result[e.id]["included"]:
            continue
        text = "\n".join(x for x in (e.title, e.body) if x)
        # ios_payment is shared by WeChat and Alipay; never match by source alone.
        if "微信" in text or not re.search(r"支付宝|花呗|账户\d+\*+\d+.*付款", text, re.S):
            continue
        n = values[e.id]
        matches = [w for w in web if values[w.id] and not (json.loads(w.payload_json or "{}").get("test"))
                   and values[w.id].get("type") == n.get("type")
                   and Decimal(str(values[w.id].get("amount"))) == Decimal(str(n.get("amount")))
                   and abs((event_time(w) - event_time(e)).total_seconds()) <= 180]
        if matches:
            candidates[e.id] = [w.id for w in matches]
    for event_id, matches in candidates.items():
        mutual = len(matches) == 1 and sum(matches[0] in m for m in candidates.values()) == 1
        result[event_id] = {"included": False, "exclusion_reason": "duplicate_notification" if mutual else "ambiguous_notification", "duplicate_of": matches[0] if mutual else None}
    return result


def spending_summary(events, decisions):
    totals = {"expense": Decimal(0), "income": Decimal(0), "refund": Decimal(0), "transfer": Decimal(0), "repayment": Decimal(0)}
    count = 0
    for e in events:
        if not decisions[e.id]["included"]:
            continue
        n = json.loads(e.normalized_json)
        kind = n.get("type")
        if kind in totals:
            totals[kind] += Decimal(str(n["amount"]))
            count += kind == "expense"
    return {"detected_spending_cny": float(totals["expense"]), "detected_transaction_count": count,
            "income_cny": float(totals["income"]), "refund_cny": float(totals["refund"]),
            "net_spending_cny": float(totals["expense"] - totals["refund"]),
            "transfer_cny": float(totals["transfer"]), "repayment_cny": float(totals["repayment"]),
            "duplicate_notification_count": sum(d["exclusion_reason"] == "duplicate_notification" for d in decisions.values()),
            "unreconciled_notification_count": sum(d["exclusion_reason"] == "ambiguous_notification" for d in decisions.values())}

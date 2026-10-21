"""Personal telemetry ingestion and GPT-facing context API."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.telemetry import LifeNote, PersonalState, TelemetryEvent, TelemetryMetric

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class EventIn(BaseModel):
    source: str = Field(min_length=1, max_length=64)
    kind: str = Field(default="raw", min_length=1, max_length=64)
    title: Optional[str] = None
    body: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    occurred_at: Optional[datetime] = None
    event_id: Optional[str] = Field(default=None, max_length=256)


class MetricIn(BaseModel):
    source: str = Field(min_length=1, max_length=64)
    metric: str = Field(min_length=1, max_length=128)
    value: float
    unit: Optional[str] = Field(default=None, max_length=32)
    dimensions: Optional[dict[str, Any]] = None
    observed_at: datetime


class LifeNoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=20000)
    tags: list[str] = Field(default_factory=list)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = Field(default="gpt", min_length=1, max_length=64)


class StateIn(BaseModel):
    value: Any
    source: str = Field(default="gpt", min_length=1, max_length=64)


def _bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return ""
    return authorization[7:].strip()


def _constant_time_any(token: str, allowed: list[str]) -> bool:
    return bool(token) and any(secret and hmac.compare_digest(token, secret) for secret in allowed)


def require_ingest(authorization: Optional[str] = Header(default=None)) -> None:
    token = _bearer(authorization)
    if not _constant_time_any(token, [settings.telemetry_ingest_key, settings.telemetry_agent_key]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid telemetry key")


def require_agent(authorization: Optional[str] = Header(default=None)) -> None:
    token = _bearer(authorization)
    if not _constant_time_any(token, [settings.telemetry_agent_key]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid agent key")


def _json(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_transaction(text: str) -> Optional[dict[str, Any]]:
    """Best-effort Chinese payment parser. Raw input remains authoritative."""
    if not text:
        return None
    amount = None
    patterns = [
        r"[¥￥]\s*([0-9]+(?:\.[0-9]{1,2})?)",
        r"(?:人民币|金额|付款|支付|支出|收款|退款)[^0-9]{0,8}([0-9]+(?:\.[0-9]{1,2})?)\s*元?",
        r"([0-9]+(?:\.[0-9]{1,2})?)\s*元",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            amount = float(match.group(1))
            break

    if any(word in text for word in ("退款", "退回", "已退")):
        tx_type = "refund"
    elif any(word in text for word in ("收款", "到账", "收到")):
        tx_type = "income"
    elif any(word in text for word in ("转账", "转给")):
        tx_type = "transfer"
    elif amount is not None or any(word in text for word in ("付款", "支付", "支出", "消费")):
        tx_type = "expense"
    else:
        return None

    return {"type": tx_type, "amount": amount, "currency": "CNY", "parser": "rules-v1"}


def _dedupe_key(item: EventIn) -> str:
    if item.event_id:
        raw = f"event-id:{item.source}:{item.event_id}"
    else:
        minute = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        raw = "|".join([item.source, item.kind, item.title or "", item.body or "", minute])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _serialize_event(row: TelemetryEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "source": row.source,
        "kind": row.kind,
        "title": row.title,
        "body": row.body,
        "payload": json.loads(row.payload_json) if row.payload_json else None,
        "normalized": json.loads(row.normalized_json) if row.normalized_json else None,
        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
        "received_at": row.received_at.replace(tzinfo=timezone.utc).isoformat(),
    }


@router.post("/events", dependencies=[Depends(require_ingest)])
def ingest_event(item: EventIn, db: Session = Depends(get_db)):
    combined = "\n".join(part for part in (item.title, item.body) if part)
    normalized = _parse_transaction(combined)
    row = TelemetryEvent(
        source=item.source.strip().lower(),
        kind=item.kind.strip().lower(),
        title=item.title,
        body=item.body,
        payload_json=_json(item.payload),
        normalized_json=_json(normalized),
        dedupe_key=_dedupe_key(item),
        occurred_at=item.occurred_at.astimezone(timezone.utc).replace(tzinfo=None) if item.occurred_at and item.occurred_at.tzinfo else item.occurred_at,
        processed=normalized is not None,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(TelemetryEvent).filter(TelemetryEvent.dedupe_key == row.dedupe_key).first()
        return {"ok": True, "duplicate": True, "event": _serialize_event(existing)}
    db.refresh(row)
    return {"ok": True, "duplicate": False, "event": _serialize_event(row)}


@router.get("/events", dependencies=[Depends(require_agent)])
def list_events(source: Optional[str] = None, kind: Optional[str] = None, hours: int = Query(default=24, ge=1, le=2160), limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(TelemetryEvent).filter(TelemetryEvent.received_at >= since)
    if source:
        query = query.filter(TelemetryEvent.source == source.lower())
    if kind:
        query = query.filter(TelemetryEvent.kind == kind.lower())
    rows = query.order_by(desc(TelemetryEvent.received_at)).limit(limit).all()
    return {"events": [_serialize_event(row) for row in rows]}


@router.post("/metrics", dependencies=[Depends(require_ingest)])
def ingest_metric(item: MetricIn, db: Session = Depends(get_db)):
    observed = item.observed_at.astimezone(timezone.utc).replace(tzinfo=None) if item.observed_at.tzinfo else item.observed_at
    row = TelemetryMetric(source=item.source.strip().lower(), metric=item.metric.strip().lower(), value=item.value, unit=item.unit, dimensions_json=_json(item.dimensions), observed_at=observed)
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return {"ok": True, "duplicate": False, "id": row.id}
    except IntegrityError:
        db.rollback()
        return {"ok": True, "duplicate": True}


@router.get("/metrics", dependencies=[Depends(require_agent)])
def list_metrics(metric: Optional[str] = None, source: Optional[str] = None, hours: int = Query(default=168, ge=1, le=8784), limit: int = Query(default=500, ge=1, le=5000), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(TelemetryMetric).filter(TelemetryMetric.observed_at >= since)
    if metric:
        query = query.filter(TelemetryMetric.metric == metric.lower())
    if source:
        query = query.filter(TelemetryMetric.source == source.lower())
    rows = query.order_by(TelemetryMetric.observed_at.asc()).limit(limit).all()
    return {"metrics": [{"source": row.source, "metric": row.metric, "value": row.value, "unit": row.unit, "dimensions": json.loads(row.dimensions_json) if row.dimensions_json else None, "observed_at": row.observed_at.replace(tzinfo=timezone.utc).isoformat()} for row in rows]}


@router.post("/notes", dependencies=[Depends(require_agent)])
def add_note(item: LifeNoteIn, db: Session = Depends(get_db)):
    row = LifeNote(text=item.text, tags_json=_json(item.tags), importance=item.importance, source=item.source)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "id": row.id, "created_at": row.created_at.replace(tzinfo=timezone.utc).isoformat()}


@router.get("/notes", dependencies=[Depends(require_agent)])
def list_notes(days: int = Query(default=30, ge=1, le=3650), limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.query(LifeNote).filter(LifeNote.created_at >= since).order_by(desc(LifeNote.created_at)).limit(limit).all()
    return {"notes": [{"id": row.id, "text": row.text, "tags": json.loads(row.tags_json) if row.tags_json else [], "importance": row.importance, "source": row.source, "created_at": row.created_at.replace(tzinfo=timezone.utc).isoformat()} for row in rows]}


@router.put("/state/{key}", dependencies=[Depends(require_agent)])
def put_state(key: str, item: StateIn, db: Session = Depends(get_db)):
    row = db.query(PersonalState).filter(PersonalState.key == key).first()
    if row is None:
        row = PersonalState(key=key, value_json=_json(item.value), source=item.source)
        db.add(row)
    else:
        row.value_json = _json(item.value)
        row.source = item.source
        row.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "key": key}


@router.get("/state", dependencies=[Depends(require_agent)])
def get_state(db: Session = Depends(get_db)):
    rows = db.query(PersonalState).order_by(PersonalState.key.asc()).all()
    return {"state": {row.key: {"value": json.loads(row.value_json), "source": row.source, "updated_at": row.updated_at.replace(tzinfo=timezone.utc).isoformat()} for row in rows}}


def _local_day_bounds() -> tuple[datetime, datetime, ZoneInfo]:
    zone = ZoneInfo(settings.timezone)
    local_now = datetime.now(zone)
    start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc).replace(tzinfo=None), end_local.astimezone(timezone.utc).replace(tzinfo=None), zone


@router.get("/today", dependencies=[Depends(require_agent)])
def today(db: Session = Depends(get_db)):
    start, end, zone = _local_day_bounds()
    events = db.query(TelemetryEvent).filter(TelemetryEvent.received_at >= start, TelemetryEvent.received_at < end).order_by(TelemetryEvent.received_at.asc()).all()
    notes = db.query(LifeNote).filter(LifeNote.created_at >= start, LifeNote.created_at < end).order_by(LifeNote.created_at.asc()).all()
    metrics = db.query(TelemetryMetric).filter(TelemetryMetric.observed_at >= start, TelemetryMetric.observed_at < end).order_by(TelemetryMetric.observed_at.asc()).all()
    spending = 0.0
    transaction_count = 0
    for event in events:
        if event.normalized_json:
            normalized = json.loads(event.normalized_json)
            if normalized.get("type") == "expense" and normalized.get("amount") is not None:
                spending += float(normalized["amount"])
                transaction_count += 1
    return {"date": datetime.now(zone).date().isoformat(), "timezone": settings.timezone, "summary": {"event_count": len(events), "metric_count": len(metrics), "note_count": len(notes), "detected_spending_cny": round(spending, 2), "detected_transaction_count": transaction_count}, "events": [_serialize_event(row) for row in events], "notes": [{"text": row.text, "importance": row.importance, "source": row.source} for row in notes], "metrics": [{"source": row.source, "metric": row.metric, "value": row.value, "unit": row.unit} for row in metrics]}


@router.get("/context", dependencies=[Depends(require_agent)])
def context(event_hours: int = Query(default=72, ge=1, le=720), note_days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    event_since = datetime.utcnow() - timedelta(hours=event_hours)
    note_since = datetime.utcnow() - timedelta(days=note_days)
    events = db.query(TelemetryEvent).filter(TelemetryEvent.received_at >= event_since).order_by(desc(TelemetryEvent.received_at)).limit(150).all()
    notes = db.query(LifeNote).filter(LifeNote.created_at >= note_since).order_by(desc(LifeNote.importance), desc(LifeNote.created_at)).limit(80).all()
    states = db.query(PersonalState).all()
    latest_metrics: dict[str, dict[str, Any]] = {}
    for row in db.query(TelemetryMetric).order_by(desc(TelemetryMetric.observed_at)).limit(1000).all():
        key = f"{row.source}:{row.metric}:{row.dimensions_json or ''}"
        if key not in latest_metrics:
            latest_metrics[key] = {"source": row.source, "metric": row.metric, "value": row.value, "unit": row.unit, "dimensions": json.loads(row.dimensions_json) if row.dimensions_json else None, "observed_at": row.observed_at.replace(tzinfo=timezone.utc).isoformat()}
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "timezone": settings.timezone, "state": {row.key: json.loads(row.value_json) for row in states}, "important_notes": [{"text": row.text, "importance": row.importance, "tags": json.loads(row.tags_json) if row.tags_json else [], "created_at": row.created_at.replace(tzinfo=timezone.utc).isoformat()} for row in notes], "recent_events": [_serialize_event(row) for row in events], "latest_metrics": list(latest_metrics.values())}


@router.get("/search", dependencies=[Depends(require_agent)])
def search_life(q: str = Query(min_length=1, max_length=300), limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    pattern = f"%{q}%"
    events = db.query(TelemetryEvent).filter((TelemetryEvent.title.ilike(pattern)) | (TelemetryEvent.body.ilike(pattern)) | (TelemetryEvent.payload_json.ilike(pattern))).order_by(desc(TelemetryEvent.received_at)).limit(limit).all()
    notes = db.query(LifeNote).filter((LifeNote.text.ilike(pattern)) | (LifeNote.tags_json.ilike(pattern))).order_by(desc(LifeNote.created_at)).limit(limit).all()
    return {"query": q, "events": [_serialize_event(row) for row in events], "notes": [{"id": row.id, "text": row.text, "tags": json.loads(row.tags_json) if row.tags_json else [], "importance": row.importance, "source": row.source, "created_at": row.created_at.replace(tzinfo=timezone.utc).isoformat()} for row in notes]}


@router.get("/ping")
def ping():
    return {"ok": True, "service": "personal-telemetry-v1"}

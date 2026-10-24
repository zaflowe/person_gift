"""Idempotent private bridge: official browser ledger -> existing telemetry DB.

Run inside backend: python -m app.services.alipay_import < snapshot.json.
No network endpoint, database schema change or new credential is required.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.database import SessionLocal
from app.models import habit, planning, conversation, study  # Register legacy mapper targets.
from app.models.telemetry import TelemetryEvent, TelemetryEventAnalysis, TelemetryAnalysisJob
from app.services import telemetry_enrichment as enrichment
from app.services.telemetry_transactions import parse_transaction, notification_time
from app.config import settings


class Bill(BaseModel):
    external_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,32}:[A-Za-z0-9_-]{8,128}$")
    created_at: datetime
    amount_cents: int = Field(ge=0, le=10**14, strict=True)
    direction: str = Field(pattern=r"^(inflow|outflow)$")
    name: str = Field(max_length=2000)
    status: str = Field(max_length=64)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw: dict

    @field_validator('created_at')
    @classmethod
    def aware_date(cls, value):
        if value.tzinfo is None:
            raise ValueError('timezone required')
        return value


def normalize(bill):
    kind = 'expense' if bill.direction == 'outflow' else 'income'
    if bill.direction == 'inflow' and ('退款' in bill.name or bill.status == '退款成功'):
        kind = 'refund'
    elif any(word in bill.name for word in ('花呗还款', '借呗还款', '信用卡还款')):
        kind = 'repayment'
    elif any(word in bill.name for word in ('余额充值', '余额提现', '转账', '转给')):
        kind = 'transfer'
    valid = bill.status in {'交易成功', '等待卖家发货', '等待买家确认收货', '等待确认收货', '退款成功'}
    return {'type': kind, 'amount': bill.amount_cents / 100, 'amount_cents': bill.amount_cents,
            'currency': 'CNY', 'parser': 'alipay-ledger-v1', 'status': bill.status,
            'exclusion_reason': None if valid else 'unsettled_or_unknown_status'}


def reset_analysis(db, row):
    analysis = db.get(TelemetryEventAnalysis, row.id)
    if analysis is None:
        db.add(TelemetryEventAnalysis(event_id=row.id))
    elif analysis.correction_json:
        return  # Preserve explicit user feedback and its current job.
    else:
        analysis.status, analysis.result_json, analysis.context_json = 'queued', None, None
        analysis.error_code, analysis.updated_at = None, datetime.utcnow()
    job = db.get(TelemetryAnalysisJob, row.id)
    if job is None:
        db.add(TelemetryAnalysisJob(event_id=row.id))
    else:
        job.status, job.attempts, job.claim_token, job.lease_until = 'pending', 0, None, None
        job.next_attempt_at, job.updated_at = datetime.utcnow(), datetime.utcnow()


def import_bills(db, rows):
    # Validate the entire batch before writing any record.
    bills = [Bill.model_validate(row) for row in rows]
    new = changed = 0
    for bill in bills:
        key = hashlib.sha256(('alipay-web:' + bill.external_id).encode()).hexdigest()
        row = db.query(TelemetryEvent).filter_by(dedupe_key=key).first()
        payload = bill.model_dump(mode='json')
        normalized = normalize(bill)
        if row and json.loads(row.payload_json) == payload and json.loads(row.normalized_json) == normalized:
            continue
        if row is None:
            row = TelemetryEvent(source='alipay_web', kind='bill', dedupe_key=key)
            db.add(row)
            new += 1
        else:
            changed += 1
        row.title = bill.name
        row.body = f"支付宝账单：{bill.name}；{bill.status}；{'流出' if bill.direction == 'outflow' else '流入'} {bill.amount_cents / 100:.2f} 元"
        row.payload_json = enrichment.dumps(payload)
        row.normalized_json = enrichment.dumps(normalized)
        row.occurred_at = bill.created_at.astimezone(timezone.utc).replace(tzinfo=None)
        row.processed = True
        db.flush()
        reset_analysis(db, row)
    db.commit()
    return {'new': new, 'changed': changed, 'total': db.query(TelemetryEvent).filter_by(source='alipay_web').count()}


def reparse_existing(db):
    changes = []
    # Lock only reparsed events, keeping other personal data untouched.
    rows = db.execute(select(TelemetryEvent).where(TelemetryEvent.source != 'alipay_web').with_for_update()).scalars().all()
    for row in rows:
        text = '\n'.join(x for x in (row.title, row.body) if x)
        normalized = parse_transaction(text)
        timestamp = row.occurred_at or notification_time(text, row.received_at, settings.timezone)
        if (json.loads(row.normalized_json) if row.normalized_json else None) == normalized and timestamp == row.occurred_at:
            continue
        changes.append({'id': row.id, 'old_normalized': row.normalized_json, 'old_occurred_at': row.occurred_at.isoformat() if row.occurred_at else None})
        row.normalized_json = enrichment.dumps(normalized) if normalized else None
        row.occurred_at, row.processed = timestamp, normalized is not None
        reset_analysis(db, row)
    db.commit()
    return changes


def main():
    data = json.load(sys.stdin)
    with SessionLocal() as db:
        repair = reparse_existing(db) if data.get('repair_existing') else []
        result = import_bills(db, data.get('rows', []))
        print(json.dumps({'import': result, 'reparsed': len(repair)}))


if __name__ == '__main__':
    main()

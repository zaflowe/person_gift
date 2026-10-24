"""Persistence, lease recovery, feedback precedence, context and provider contracts."""
import json
from datetime import datetime, timedelta

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.models import habit, planning, conversation, study  # Register legacy relationship targets, as app.main does.
from app.models.telemetry import (
    LifeNote, PersonalState, TelemetryAnalysisFeedback, TelemetryAnalysisJob,
    TelemetryEvent, TelemetryEventAnalysis, TelemetryMetric,
)
from app.routers import telemetry
from app.services import telemetry_enrichment as service


@pytest.fixture
def sessions(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[model.__table__ for model in (
        TelemetryEvent, TelemetryMetric, LifeNote, PersonalState,
        TelemetryEventAnalysis, TelemetryAnalysisJob, TelemetryAnalysisFeedback,
    )])
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(service, "SessionLocal", factory)
    monkeypatch.setattr(settings, "telemetry_agent_key", "test-agent")
    monkeypatch.setattr(settings, "telemetry_ingest_key", "test-ingest")
    monkeypatch.setattr(settings, "telemetry_enrichment_enabled", True)
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("test-provider-secret"))
    monkeypatch.setattr(settings, "timezone", "Asia/Shanghai")
    yield factory
    engine.dispose()


@pytest.fixture
def client(sessions):
    app = FastAPI()
    app.include_router(telemetry.router)
    def db_dependency():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = db_dependency
    with TestClient(app) as test_client:
        yield test_client


def event(db, *, body="你已向幸福饭店付款￥28.00", when=None, **kwargs):
    row = TelemetryEvent(source="alipay", kind="raw", body=body,
                         occurred_at=when or datetime.utcnow(), **kwargs)
    db.add(row)
    db.commit()
    service.enqueue_event(db, row.id)
    return row


def proposal(**changes):
    value = {"category": "food", "activity": "lunch", "merchant": "幸福饭店",
             "summary": "可能是午饭，尚待确认", "confidence": 0.7, "evidence": ["餐饮商户"]}
    return value | changes


def test_ingest_durable_when_provider_fails_and_retries(sessions, client, monkeypatch):
    response = client.post("/telemetry/events", headers={"Authorization": "Bearer test-ingest"},
                           json={"source": "alipay", "event_id": "delivery-1", "body": "付款￥28.00"})
    assert response.status_code == 200
    event_id = response.json()["event"]["id"]
    def timeout(_):
        raise service.EnrichmentError("provider_timeout")
    monkeypatch.setattr(service, "interpret", timeout)
    service.process_enrichment_tick()
    with sessions() as db:
        assert db.get(TelemetryEvent, event_id).body == "付款￥28.00"
        job = db.get(TelemetryAnalysisJob, event_id)
        assert job.status == "pending" and job.attempts == 1
        assert job.next_attempt_at > datetime.utcnow()
        assert db.get(TelemetryEventAnalysis, event_id).error_code == "provider_timeout"
        assert service.claim_job(db) is None


def test_queue_failure_never_rolls_back_raw_event(sessions, client, monkeypatch):
    def fail(*_):
        raise RuntimeError("unavailable")
    monkeypatch.setattr(service, "enqueue_event", fail)
    response = client.post("/telemetry/events", headers={"Authorization": "Bearer test-ingest"},
                           json={"source": "alipay", "event_id": "delivery", "body": "付款￥1"})
    assert response.status_code == 200
    with sessions() as db:
        assert db.query(TelemetryEvent).count() == 1
        service.recover_missing_jobs(db)
        assert db.query(TelemetryAnalysisJob).count() == 1


def test_delivery_uuid_dedupes_retry_but_preserves_same_amount_payments(client, sessions):
    payload = {"source": "alipay", "body": "付款￥28.00", "event_id": "uuid-1"}
    headers = {"Authorization": "Bearer test-ingest"}
    first = client.post("/telemetry/events", json=payload, headers=headers).json()
    retry = client.post("/telemetry/events", json=payload, headers=headers).json()
    second = client.post("/telemetry/events", json=payload | {"event_id": "uuid-2"}, headers=headers).json()
    assert not first["duplicate"] and retry["duplicate"] and not second["duplicate"]
    with sessions() as db:
        assert db.query(TelemetryEvent).count() == 2


def test_job_claim_is_exclusive_and_expired_lease_recovers(sessions):
    with sessions() as db:
        row = event(db)
        first = service.claim_job(db)
        with sessions() as other:
            assert service.claim_job(other) is None
        db.get(TelemetryAnalysisJob, row.id).lease_until = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
        second = service.claim_job(db)
        assert first[0] == second[0] and first[1] != second[1] and second[2] == 2
        assert not service.complete_job(db, row.id, first[1], result=proposal())


def test_last_attempt_crash_does_not_stay_processing(sessions):
    with sessions() as db:
        row = event(db)
        service.claim_job(db)
        job = db.get(TelemetryAnalysisJob, row.id)
        job.attempts = service.MAX_ATTEMPTS
        job.lease_until = datetime.utcnow() - timedelta(seconds=1)
        db.commit()
        assert service.claim_job(db) is None
        db.refresh(job)
        assert job.status == "failed"
        assert db.get(TelemetryEventAnalysis, row.id).error_code == "worker_lease_expired"


def test_correction_wins_late_model_result_and_preserves_original(sessions):
    with sessions() as db:
        row = event(db)
        claim = service.claim_job(db)
        confirmed = service.Correction(category="shopping", activity="groceries", summary="这是买菜")
        service.correct_event(db, row.id, confirmed)
        assert not service.complete_job(db, row.id, claim[1], result=proposal())
        db.expire_all()
        assert service.analysis_view(db.get(TelemetryEventAnalysis, row.id))["effective"]["activity"] == "groceries"
        assert db.get(TelemetryEvent, row.id).body == "你已向幸福饭店付款￥28.00"
        assert db.query(TelemetryAnalysisFeedback).count() == 1


def test_context_uses_confirmed_history_excludes_future_and_unconfirmed_guesses(sessions):
    reference = datetime(2026, 10, 22, 4)
    with sessions() as db:
        old = event(db, when=reference - timedelta(days=1))
        service.correct_event(db, old.id, service.Correction(category="food", activity="lunch", summary="午饭"))
        unconfirmed = event(db, when=reference - timedelta(hours=1))
        db.get(TelemetryEventAnalysis, unconfirmed.id).result_json = service.dumps(proposal(activity="taxi"))
        future = event(db, when=reference + timedelta(hours=1))
        db.add(LifeNote(text="FUTURE_NOTE", created_at=reference + timedelta(seconds=1)))
        db.add(LifeNote(text="平时午饭在十二点", created_at=reference - timedelta(days=1)))
        db.add(PersonalState(key="future", value_json='"future"', updated_at=reference + timedelta(seconds=1)))
        db.commit()
        current = event(db, when=reference)
        ctx, refs = service.build_context(db, current)
        assert future.id not in refs["event_ids"]
        assert "FUTURE_NOTE" not in service.dumps(ctx) and "future" not in ctx["state"]
        assert "12:00:00+08:00" in ctx["event"]["local_time"]
        assert ctx["confirmed_habits"] == [{"category": "food", "activity": "lunch", "observations": 1}]
        assert "taxi" not in service.dumps(ctx)


@pytest.mark.parametrize("kwargs,reason", [
    ({"kind": "deployment_test"}, "test_event"),
    ({"payload_json": '{"test":true}'}, "test_event"),
    ({"body": "验证码123456，请勿泄露"}, "sensitive_notification"),
])
def test_test_and_otp_events_are_saved_without_sending_to_provider(sessions, monkeypatch, kwargs, reason):
    def should_not_call(_):
        pytest.fail("provider received excluded data")
    monkeypatch.setattr(service, "interpret", should_not_call)
    with sessions() as db:
        row = TelemetryEvent(source="test", **kwargs)
        db.add(row)
        db.commit()
        event_id = row.id
        service.enqueue_event(db, event_id)
    service.process_enrichment_tick()
    with sessions() as db:
        assert db.get(TelemetryEvent, event_id) is not None
        analysis = db.get(TelemetryEventAnalysis, event_id)
        assert analysis.status == "skipped" and analysis.error_code == reason


def test_marked_test_spending_excluded_without_deleting_event(client):
    headers = {"Authorization": "Bearer test-agent"}
    client.post("/telemetry/events", headers=headers,
                json={"source": "alipay", "event_id": "test", "body": "付款￥1", "payload": {"test": True}})
    client.post("/telemetry/events", headers=headers,
                json={"source": "alipay", "event_id": "real", "body": "付款￥28"})
    response = client.get("/telemetry/today", headers=headers).json()
    assert response["summary"]["event_count"] == 2
    assert response["summary"]["test_event_count"] == 1
    assert response["summary"]["detected_spending_cny"] == 28


def test_correction_requires_agent_and_search_uses_effective_result(sessions, client):
    with sessions() as db:
        row = event(db)
        event_id = row.id
        db.get(TelemetryEventAnalysis, event_id).result_json = service.dumps(proposal(activity="taxi"))
        db.commit()
    path = f"/telemetry/events/{event_id}/analysis"
    value = {"category": "food", "activity": "lunch", "summary": "用户确认午饭"}
    assert client.put(path, json=value, headers={"Authorization": "Bearer test-ingest"}).status_code == 401
    headers = {"Authorization": "Bearer test-agent"}
    assert client.put(path, json=value, headers=headers).json()["analysis"]["confirmed_by_user"]
    assert len(client.get("/telemetry/search", params={"q": "午饭"}, headers=headers).json()["events"]) == 1
    assert not client.get("/telemetry/search", params={"q": "打车"}, headers=headers).json()["events"]


def install_provider_mock(monkeypatch, handler):
    real_client = httpx.Client
    monkeypatch.setattr(service.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))


def test_provider_json_contract_and_secrets_not_in_context(sessions, monkeypatch):
    def respond(request):
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer test-provider-secret"
        assert body["response_format"] == {"type": "json_object"}
        assert body["thinking"] == {"type": "disabled"}
        assert "test-provider-secret" not in request.content.decode()
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal())}}],
                                        "model": "provider-resolved-model", "usage": {"total_tokens": 123, "unexpected": "private"}})
    install_provider_mock(monkeypatch, respond)
    result, model, usage = service.interpret({"event": {"body": "付款￥28"}})
    assert result["activity"] == "lunch" and model == "provider-resolved-model"
    assert usage == {"total_tokens": 123}
    assert "test-provider-secret" not in repr(settings.deepseek_api_key)


@pytest.mark.parametrize("response,code", [
    (httpx.Response(401, text="test-provider-secret"), "provider_auth"),
    (httpx.Response(429), "provider_rate_limit"),
    (httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": "{"}}]}), "provider_incomplete_json"),
    (httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": ""}}]}), "provider_invalid_json"),
    (httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal(confidence=4))}}]}), "provider_invalid_json"),
])
def test_provider_errors_are_bounded_and_sanitized(sessions, monkeypatch, response, code):
    install_provider_mock(monkeypatch, lambda _: response)
    with pytest.raises(service.EnrichmentError) as exc:
        service.interpret({"event": {}})
    assert str(exc.value) == code
    assert "test-provider-secret" not in str(exc.value)


def test_successful_worker_exposes_proposal_without_claiming_confirmation(sessions, monkeypatch):
    monkeypatch.setattr(service, "interpret", lambda _: (proposal(), "test-model", {"total_tokens": 10}))
    with sessions() as db:
        row = event(db)
        event_id = row.id
    service.process_enrichment_tick()
    with sessions() as db:
        view = service.analysis_view(db.get(TelemetryEventAnalysis, event_id))
        assert view["status"] == "complete" and not view["confirmed_by_user"]
        assert view["effective"]["activity"] == "lunch"
        assert db.get(TelemetryAnalysisJob, event_id).status == "done"


def test_preview_is_agent_only_and_has_no_database_side_effects(sessions, client, monkeypatch):
    monkeypatch.setattr(service, "interpret", lambda _: (proposal(), "test-model", {}))
    payload = {"source": "alipay", "body": "模拟饭店付款￥28"}
    assert client.post("/telemetry/analysis/preview", json=payload,
                       headers={"Authorization": "Bearer test-ingest"}).status_code == 401
    response = client.post("/telemetry/analysis/preview", json=payload,
                           headers={"Authorization": "Bearer test-agent"})
    assert response.status_code == 200 and response.json()["saved"] is False
    with sessions() as db:
        for model in (TelemetryEvent, TelemetryEventAnalysis, TelemetryAnalysisJob, TelemetryAnalysisFeedback):
            assert db.query(model).count() == 0


def test_reanalyze_invalidates_old_claim_and_refuses_confirmed_event(sessions, client):
    with sessions() as db:
        row = event(db)
        event_id = row.id
        claim = service.claim_job(db)
    headers = {"Authorization": "Bearer test-agent"}
    path = f"/telemetry/events/{event_id}/reanalyze"
    assert client.post(path, headers=headers).status_code == 200
    with sessions() as db:
        assert not service.complete_job(db, event_id, claim[1], result=proposal())
        service.correct_event(db, event_id, service.Correction(category="food", activity="lunch", summary="午饭"))
    assert client.post(path, headers=headers).status_code == 409
    with sessions() as db:
        assert db.get(TelemetryAnalysisJob, event_id).status == "done"
        assert db.get(TelemetryEventAnalysis, event_id).correction_json is not None


def bill_record(*, key='1234567890123456', when=None, cents=1400, name='美食广场032', direction='outflow', status='交易成功'):
    from datetime import timezone
    stamp = when or datetime.now(timezone.utc)
    return {'external_id': 'TRADE:' + key, 'created_at': stamp.isoformat(), 'amount_cents': cents,
            'name': name, 'direction': direction, 'status': status, 'content_hash': 'a' * 64,
            'raw': {'cells': ['original official row']}}


def test_web_backfill_uses_transaction_day_and_is_idempotent(sessions, client):
    from app.services.alipay_import import import_bills
    with sessions() as db:
        old = bill_record(when=datetime.now().astimezone() - timedelta(days=3))
        current = bill_record(key='2234567890123456')
        assert import_bills(db, [old, current]) == {'new': 2, 'changed': 0, 'total': 2}
        assert import_bills(db, [old, current]) == {'new': 0, 'changed': 0, 'total': 2}
        ids = [e.id for e in db.query(TelemetryEvent)]
    headers = {'Authorization': 'Bearer test-agent'}
    today = client.get('/telemetry/today', headers=headers).json()
    assert today['summary']['detected_spending_cny'] == 14
    assert today['summary']['detected_transaction_count'] == 1
    assert len(today['events']) == 1
    assert len(client.get('/telemetry/search', params={'q': '美食广场'}, headers=headers).json()['events']) == 2
    with sessions() as db:
        old['status'] = '交易关闭'
        assert import_bills(db, [old]) == {'new': 0, 'changed': 1, 'total': 2}
        assert sorted(e.id for e in db.query(TelemetryEvent)) == sorted(ids)


def test_web_and_notification_count_once_and_keep_both(sessions, client):
    from app.services.alipay_import import import_bills
    from datetime import timezone
    stamp = datetime.now(timezone.utc)
    with sessions() as db:
        import_bills(db, [bill_record(when=stamp)])
    local = stamp.astimezone(__import__('zoneinfo').ZoneInfo('Asia/Shanghai'))
    body = f'支付成功通知\n账户193****9886于{local.month}月{local.day}日{local.hour}时{local.minute}分成功付款14.00元'
    headers = {'Authorization': 'Bearer test-agent'}
    client.post('/telemetry/events', headers=headers, json={'source': 'ios_payment', 'body': body})
    data = client.get('/telemetry/today', headers=headers).json()
    assert len(data['events']) == 2
    assert data['summary']['detected_spending_cny'] == 14
    assert data['summary']['duplicate_notification_count'] == 1
    notification = next(e for e in data['events'] if e['source'] == 'ios_payment')
    assert notification['accounting']['duplicate_of']
    context = client.get('/telemetry/context', headers=headers).json()
    assert context['today_summary']['detected_spending_cny'] == 14
    assert sum(day['detected_spending_cny'] for day in context['daily_spending']) == 14


def test_same_amount_real_payments_preserved_and_ambiguous_notification_flagged(sessions, client):
    from app.services.alipay_import import import_bills
    with sessions() as db:
        import_bills(db, [bill_record(), bill_record(key='2234567890123456')])
    headers = {'Authorization': 'Bearer test-agent'}
    client.post('/telemetry/events', headers=headers, json={'source': 'ios_payment', 'body': '支付宝成功付款14.00元'})
    data = client.get('/telemetry/today', headers=headers).json()
    assert data['summary']['detected_spending_cny'] == 28
    assert data['summary']['detected_transaction_count'] == 2
    assert data['summary']['unreconciled_notification_count'] == 1
    assert data['summary']['duplicate_notification_count'] == 0


def test_wechat_never_dedupes_against_alipay(sessions, client):
    from app.services.alipay_import import import_bills
    with sessions() as db:
        import_bills(db, [bill_record()])
    headers = {'Authorization': 'Bearer test-agent'}
    client.post('/telemetry/events', headers=headers, json={'source': 'ios_payment', 'body': '微信支付成功付款14.00元'})
    assert client.get('/telemetry/today', headers=headers).json()['summary']['detected_spending_cny'] == 28


def test_status_refunds_transfers_and_repayments(sessions, client):
    from app.services.alipay_import import import_bills
    rows = [bill_record(name='收钱码收款'),
            bill_record(key='2234567890123456', cents=200, direction='inflow', name='退款'),
            bill_record(key='3234567890123456', cents=9999, status='等待付款'),
            bill_record(key='4234567890123456', cents=5000, name='花呗还款'),
            bill_record(key='5234567890123456', cents=3000, name='余额提现')]
    with sessions() as db:
        import_bills(db, rows)
    data = client.get('/telemetry/today', headers={'Authorization': 'Bearer test-agent'}).json()['summary']
    assert data['detected_spending_cny'] == 14  # Outgoing 收钱码收款 is not income.
    assert data['refund_cny'] == 2
    assert data['net_spending_cny'] == 12
    assert data['transfer_cny'] == 30
    assert data['repayment_cny'] == 50


def test_repair_preserves_original_notification_and_user_feedback(sessions):
    from app.services.alipay_import import reparse_existing
    with sessions() as db:
        row = event(db, body='你在友宝有一笔3.10元的免密/自动扣款支付，点击领取6个支付宝积分。', normalized_json='{"type":"expense","amount":6}')
        event_id, body = row.id, row.body
        analysis = db.get(TelemetryEventAnalysis, event_id)
        analysis.correction_json = service.dumps(proposal(summary='用户确认茉莉蜜茶'))
        db.commit()
        assert len(reparse_existing(db)) == 1
        db.expire_all()
        assert db.get(TelemetryEvent, event_id).body == body
        assert json.loads(db.get(TelemetryEvent, event_id).normalized_json)['amount'] == 3.1
        assert json.loads(db.get(TelemetryEventAnalysis, event_id).correction_json)['summary'] == '用户确认茉莉蜜茶'
        assert reparse_existing(db) == []


def test_entire_import_batch_validated_before_changes(sessions):
    from app.services.alipay_import import import_bills
    with sessions() as db:
        with pytest.raises(ValueError):
            import_bills(db, [bill_record(), bill_record(key='2234567890123456', when=datetime.utcnow())])
        assert db.query(TelemetryEvent).count() == 0

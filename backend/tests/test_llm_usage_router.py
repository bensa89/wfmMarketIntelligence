# backend/tests/test_llm_usage_router.py
from datetime import datetime, timedelta, timezone

from app.models.llm_call import LlmCall
from app.models.llm_model_price import LlmModelPrice


def _seed_call(db_session, **overrides):
    defaults = dict(
        caller="analyser", provider="claude", model="claude-haiku-4-5-20251001",
        input_tokens=1000, output_tokens=500, estimated=False, duration_ms=1200,
    )
    defaults.update(overrides)
    call = LlmCall(**defaults)
    db_session.add(call)
    db_session.commit()
    return call


def test_summary_empty(client):
    response = client.get("/api/llm-usage/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["today"]["total_tokens"] == 0
    assert data["all_time"]["total_tokens"] == 0


def test_summary_counts_todays_call(client, db_session):
    _seed_call(db_session)
    response = client.get("/api/llm-usage/summary")
    data = response.json()
    assert data["today"]["total_tokens"] == 1500
    assert data["all_time"]["total_tokens"] == 1500


def test_summary_excludes_old_calls_from_today(client, db_session):
    old_call = _seed_call(db_session)
    old_call.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    db_session.commit()

    response = client.get("/api/llm-usage/summary")
    data = response.json()
    assert data["today"]["total_tokens"] == 0
    assert data["last_30_days"]["total_tokens"] == 1500


def test_summary_computes_cost_from_price_table(client, db_session):
    _seed_call(db_session, input_tokens=1_000_000, output_tokens=1_000_000)
    db_session.add(LlmModelPrice(model="claude-haiku-4-5-20251001", input_price_per_1m=1.0, output_price_per_1m=5.0))
    db_session.commit()

    response = client.get("/api/llm-usage/summary")
    data = response.json()
    assert data["today"]["cost_usd"] == 6.0


def test_timeseries_groups_by_day(client, db_session):
    _seed_call(db_session)
    response = client.get("/api/llm-usage/timeseries?days=7")
    assert response.status_code == 200
    points = response.json()
    assert len(points) == 1
    assert points[0]["total_tokens"] == 1500


def test_breakdown_groups_by_caller_provider_model(client, db_session):
    _seed_call(db_session, caller="analyser")
    _seed_call(db_session, caller="assessor", input_tokens=200, output_tokens=100)
    response = client.get("/api/llm-usage/breakdown?days=30")
    rows = response.json()
    assert len(rows) == 2
    callers = {r["caller"] for r in rows}
    assert callers == {"analyser", "assessor"}

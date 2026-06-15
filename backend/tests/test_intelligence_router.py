from datetime import datetime, timezone, timedelta
from app.models.company import Company, CompanyType
from app.models.source import Source, SourceType
from app.models.document import Document
from app.models.signal import Signal, SignalType


def test_overview_endpoint_returns_expected_keys(client):
    resp = client.get("/api/intelligence/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_movers_7d" in data
    assert "top_movers_30d" in data
    assert "capability_heatmap" in data
    assert "recent_market_shaping" in data
    assert "emerging_risks" in data
    assert "emerging_opportunities" in data
    assert "emerging_watchpoints" in data


def test_signals_feed_returns_paginated_response(client):
    resp = client.get("/api/intelligence/signals/feed")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_competitor_workspace_404_for_unknown_slug(client):
    resp = client.get("/api/intelligence/competitors/nonexistent-slug/workspace")
    assert resp.status_code == 404


def test_assess_signal_endpoint_404_for_unknown_id(client):
    resp = client.post("/api/intelligence/signals/nonexistent-id/assess")
    assert resp.status_code == 404


# --- created_from / created_to filter ---

def _make_signal_with_date(db_session, created_at: datetime) -> Signal:
    company = Company(
        name=f"Co-{created_at.date()}", slug=f"co-{created_at.timestamp():.0f}",
        type=CompanyType.competitor,
    )
    db_session.add(company)
    db_session.flush()
    source = Source(company_id=company.id, url=f"https://co-{created_at.timestamp():.0f}.com", source_type=SourceType.news)
    db_session.add(source)
    db_session.flush()
    doc = Document(source_id=source.id, url=f"https://co-{created_at.timestamp():.0f}.com/1", content_hash=f"h{created_at.timestamp():.0f}")
    db_session.add(doc)
    db_session.flush()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="Test", signal_type=SignalType.other, relevance_score=0.5,
        created_at=created_at,
    )
    db_session.add(signal)
    db_session.commit()
    return signal


def test_signals_feed_created_from_excludes_older_signals(client, db_session):
    now = datetime.now(timezone.utc)
    _make_signal_with_date(db_session, now - timedelta(days=10))
    recent = _make_signal_with_date(db_session, now - timedelta(days=2))

    cutoff = (now - timedelta(days=5)).date().isoformat()
    resp = client.get(f"/api/intelligence/signals/feed?created_from={cutoff}")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert recent.id in ids
    assert all(i != (str(id) for id in ids if id != recent.id) for i in ids)


def test_signals_feed_created_to_excludes_newer_signals(client, db_session):
    now = datetime.now(timezone.utc)
    old = _make_signal_with_date(db_session, now - timedelta(days=10))
    _make_signal_with_date(db_session, now - timedelta(days=1))

    cutoff = (now - timedelta(days=5)).date().isoformat()
    resp = client.get(f"/api/intelligence/signals/feed?created_to={cutoff}")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert old.id in ids


def test_signals_feed_created_range_returns_only_matching(client, db_session):
    now = datetime.now(timezone.utc)
    _make_signal_with_date(db_session, now - timedelta(days=20))
    target = _make_signal_with_date(db_session, now - timedelta(days=5))
    _make_signal_with_date(db_session, now - timedelta(days=1))

    date_from = (now - timedelta(days=7)).date().isoformat()
    date_to = (now - timedelta(days=3)).date().isoformat()
    resp = client.get(f"/api/intelligence/signals/feed?created_from={date_from}&created_to={date_to}")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert ids == [target.id]

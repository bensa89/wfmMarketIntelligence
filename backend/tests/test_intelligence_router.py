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
    assert "capability_heatmap_7d" in data
    assert "capability_heatmap_30d" in data
    assert "recent_market_shaping_7d" in data
    assert "recent_market_shaping_30d" in data
    assert "recent_market_shaping_90d" in data
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


# --- signal stats aggregation ---

def _make_signal(
    db_session,
    company,
    *,
    signal_type: SignalType = SignalType.other,
    created_at: datetime,
    published_at: datetime | None = None,
) -> Signal:
    ts = created_at.timestamp()
    source = Source(company_id=company.id, url=f"https://stats-{ts}-{company.id}.example.com", source_type=SourceType.news)
    db_session.add(source)
    db_session.flush()
    doc = Document(source_id=source.id, url=f"https://stats-{ts}-{company.id}.example.com/1", content_hash=f"h{ts}-{company.id}")
    db_session.add(doc)
    db_session.flush()
    signal = Signal(
        document_id=doc.id, company_id=company.id,
        title="Test", signal_type=signal_type, relevance_score=0.5,
        created_at=created_at, published_at=published_at,
    )
    db_session.add(signal)
    db_session.commit()
    return signal


def _make_company(db_session, name: str) -> Company:
    company = Company(name=name, slug=name.lower().replace(" ", "-"), type=CompanyType.competitor)
    db_session.add(company)
    db_session.flush()
    db_session.commit()
    return company


def test_signal_stats_404_for_unknown_slug(client):
    resp = client.get("/api/intelligence/competitors/nonexistent-slug/signals/stats")
    assert resp.status_code == 404


def test_signal_stats_rejects_invalid_days(client, db_session):
    company = _make_company(db_session, "Stats Co Invalid")
    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=45")
    assert resp.status_code == 422


def test_signal_stats_total_and_category_counts(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Totals")
    _make_signal(db_session, company, signal_type=SignalType.product_update, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))
    _make_signal(db_session, company, signal_type=SignalType.product_update, created_at=now - timedelta(days=2), published_at=now - timedelta(days=2))
    _make_signal(db_session, company, signal_type=SignalType.hiring_signal, created_at=now - timedelta(days=3), published_at=now - timedelta(days=3))

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["period_days"] == 30
    assert data["granularity"] == "day"

    by_cat = {row["signal_type"]: row["count"] for row in data["by_category"]}
    assert by_cat["product_update"] == 2
    assert by_cat["hiring_signal"] == 1
    assert by_cat["other"] == 0
    assert len(data["by_category"]) == 8
    counts = [row["count"] for row in data["by_category"]]
    assert counts == sorted(counts, reverse=True)


def test_signal_stats_excludes_other_companies_and_out_of_range_signals(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Scope")
    other_company = _make_company(db_session, "Stats Co Other")
    _make_signal(db_session, company, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))
    _make_signal(db_session, company, created_at=now - timedelta(days=40), published_at=now - timedelta(days=40))
    _make_signal(db_session, other_company, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=30")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_signal_stats_timeline_is_gap_free_daily(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Timeline Daily")
    _make_signal(db_session, company, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=30")
    data = resp.json()
    assert data["granularity"] == "day"
    assert len(data["timeline"]) == 31
    buckets = [row["bucket"] for row in data["timeline"]]
    assert buckets == sorted(buckets)
    assert sum(row["count"] for row in data["timeline"]) == 1


def test_signal_stats_timeline_is_weekly_for_90d(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Timeline Weekly")
    _make_signal(db_session, company, created_at=now - timedelta(days=1), published_at=now - timedelta(days=1))

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=90")
    data = resp.json()
    assert data["granularity"] == "week"
    assert len(data["timeline"]) == 13
    assert sum(row["count"] for row in data["timeline"]) == 1


def test_signal_stats_falls_back_to_created_at_when_published_at_missing(client, db_session):
    now = datetime.now(timezone.utc)
    company = _make_company(db_session, "Stats Co Fallback")
    _make_signal(db_session, company, created_at=now - timedelta(days=2), published_at=None)

    resp = client.get(f"/api/intelligence/competitors/{company.slug}/signals/stats?days=30")
    data = resp.json()
    assert data["total"] == 1
    assert sum(row["count"] for row in data["timeline"]) == 1

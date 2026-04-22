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

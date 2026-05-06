import pytest
from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus


@pytest.fixture
def company(client):
    r = client.post(
        "/api/companies",
        json={"name": "ATOSS", "slug": "atoss-src", "type": "competitor"},
    )
    return r.json()


def test_list_sources_empty(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    assert response.json() == []


def test_create_source(client, company):
    payload = {
        "company_id": company["id"],
        "url": "https://atoss.com/news",
        "source_type": "news",
        "label": "News",
    }
    response = client.post("/api/sources", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://atoss.com/news"
    assert data["is_active"] is True
    assert data["crawl_status"] == "new"
    assert data["discovered_pages_summary"] == {}


def test_create_duplicate_url_fails(client, company):
    payload = {
        "company_id": company["id"],
        "url": "https://atoss.com/dup",
        "source_type": "blog",
    }
    client.post("/api/sources", json=payload)
    response = client.post("/api/sources", json=payload)
    assert response.status_code == 409


def test_update_source(client, company):
    r = client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://atoss.com/blog",
            "source_type": "blog",
        },
    )
    source_id = r.json()["id"]
    response = client.put(f"/api/sources/{source_id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["crawl_status"] == "new"


def test_delete_source(client, company):
    r = client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://atoss.com/del",
            "source_type": "press",
        },
    )
    source_id = r.json()["id"]
    response = client.delete(f"/api/sources/{source_id}")
    assert response.status_code == 204
    response = client.get("/api/sources")
    assert all(s["id"] != source_id for s in response.json())


def test_filter_sources_by_company(client, company):
    client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://atoss.com/jobs",
            "source_type": "jobs",
        },
    )
    response = client.get(f"/api/sources?company_id={company['id']}")
    assert response.status_code == 200
    assert all(s["company_id"] == company["id"] for s in response.json())


def test_source_respect_robots_defaults_true(client, company):
    response = client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://robots-default.example.com",
            "source_type": "news",
        },
    )
    assert response.status_code == 201
    assert response.json()["respect_robots_txt"] is True


def test_source_respect_robots_can_be_set_false_and_updated(client, company):
    response = client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://robots-false.example.com",
            "source_type": "news",
            "respect_robots_txt": False,
        },
    )
    assert response.status_code == 201
    assert response.json()["respect_robots_txt"] is False
    source_id = response.json()["id"]

    patch_resp = client.put(
        f"/api/sources/{source_id}", json={"respect_robots_txt": True}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["respect_robots_txt"] is True


def test_search_sources_by_url(client, company):
    client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://atoss.com/search-news",
            "source_type": "news",
        },
    )
    client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://atoss.com/search-blog",
            "source_type": "blog",
        },
    )
    response = client.get("/api/sources/search?q=search-news")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source"]["url"] == "https://atoss.com/search-news"
    assert data[0]["matching_subsites"] == []


def test_search_sources_includes_subsites(client, company, db_session):
    r = client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://atoss.com/search-parent",
            "source_type": "news",
        },
    )
    source_id = r.json()["id"]
    page = DiscoveredPage(
        source_id=source_id,
        url="https://atoss.com/search-parent/subpage",
        depth=1,
        status=DiscoveredPageStatus.new,
        is_active=True,
    )
    db_session.add(page)
    db_session.commit()

    response = client.get("/api/sources/search?q=search-parent/sub")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source"]["url"] == "https://atoss.com/search-parent"
    assert len(data[0]["matching_subsites"]) == 1
    assert data[0]["matching_subsites"][0] == "https://atoss.com/search-parent/subpage"


def test_search_sources_no_results(client):
    response = client.get("/api/sources/search?q=nonexistent")
    assert response.status_code == 200
    assert response.json() == []

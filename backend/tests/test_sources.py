import pytest


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

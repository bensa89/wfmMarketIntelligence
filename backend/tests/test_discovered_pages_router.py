import pytest
from datetime import datetime, timezone
from app.models.discovered_page import DiscoveredPage  # noqa: F401 — register with Base
from app.models.company import Company  # noqa: F401
from app.models.source import Source  # noqa: F401


@pytest.fixture
def company_and_source(client):
    company = client.post(
        "/api/companies",
        json={"name": "Test Co", "slug": "test-dp-api", "type": "competitor"},
    ).json()
    source = client.post(
        "/api/sources",
        json={
            "company_id": company["id"],
            "url": "https://test-dp.com",
            "source_type": "news",
        },
    ).json()
    return company, source


@pytest.fixture
def discovered_page(db_session, company_and_source):
    _, source = company_and_source
    from app.models.discovered_page import DiscoveredPage, DiscoveredPageStatus

    page = DiscoveredPage(
        source_id=source["id"],
        url="https://test-dp.com/blog/2024/01/article",
        title="Test Article",
        depth=1,
        status=DiscoveredPageStatus.new,
        content_hash="abc123",
        discovered_at=datetime.now(timezone.utc),
        last_crawled_at=datetime.now(timezone.utc),
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)
    return page


def test_list_discovered_pages_empty(client, company_and_source):
    _, source = company_and_source
    response = client.get(f"/api/discovered-pages/?source_id={source['id']}")
    assert response.status_code == 200
    assert response.json() == []


def test_list_discovered_pages_returns_pages(
    client, company_and_source, discovered_page
):
    _, source = company_and_source
    response = client.get(f"/api/discovered-pages/?source_id={source['id']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["url"] == "https://test-dp.com/blog/2024/01/article"
    assert data[0]["status"] == "new"
    assert data[0]["depth"] == 1


def test_list_discovered_pages_requires_source_id(client):
    response = client.get("/api/discovered-pages/")
    assert response.status_code == 422


def test_patch_discovered_page_deactivate(client, discovered_page):
    response = client.patch(
        f"/api/discovered-pages/{discovered_page.id}",
        json={"is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["status"] == "ignored"


def test_patch_discovered_page_activate(client, discovered_page, db_session):
    from app.models.discovered_page import DiscoveredPageStatus

    discovered_page.is_active = False
    discovered_page.status = DiscoveredPageStatus.ignored
    db_session.commit()

    response = client.patch(
        f"/api/discovered-pages/{discovered_page.id}",
        json={"is_active": True},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_patch_discovered_page_not_found(client):
    response = client.patch(
        "/api/discovered-pages/nonexistent-id",
        json={"is_active": False},
    )
    assert response.status_code == 404


def test_delete_discovered_page(client, discovered_page, db_session):
    from app.models.discovered_page import DiscoveredPage as DP

    response = client.delete(f"/api/discovered-pages/{discovered_page.id}")
    assert response.status_code == 200
    assert response.json()["id"] == discovered_page.id
    assert db_session.query(DP).filter(DP.id == discovered_page.id).first() is None


def test_delete_discovered_page_not_found(client):
    response = client.delete("/api/discovered-pages/nonexistent-id")
    assert response.status_code == 404

from app.models.company import Company  # noqa: F401 — register table with Base


def test_list_companies_empty(client):
    response = client.get("/api/companies")
    assert response.status_code == 200
    assert response.json() == []


def test_create_company(client):
    payload = {
        "name": "ATOSS",
        "slug": "atoss",
        "type": "competitor",
        "website": "https://atoss.com",
    }
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "atoss"
    assert data["type"] == "competitor"
    assert "id" in data


def test_create_duplicate_slug_fails(client):
    payload = {"name": "ATOSS", "slug": "atoss-dup", "type": "competitor"}
    client.post("/api/companies", json=payload)
    response = client.post("/api/companies", json=payload)
    assert response.status_code == 409


def test_get_company_by_slug(client):
    client.post(
        "/api/companies",
        json={"name": "ATOSS", "slug": "atoss-get", "type": "competitor"},
    )
    response = client.get("/api/companies/atoss-get")
    assert response.status_code == 200
    assert response.json()["slug"] == "atoss-get"


def test_get_nonexistent_company(client):
    response = client.get("/api/companies/nonexistent")
    assert response.status_code == 404


def test_update_company(client):
    client.post(
        "/api/companies",
        json={"name": "ATOSS", "slug": "atoss-upd", "type": "competitor"},
    )
    response = client.put(
        "/api/companies/atoss-upd", json={"description": "WFM vendor"}
    )
    assert response.status_code == 200
    assert response.json()["description"] == "WFM vendor"


def test_company_read_includes_logo_path(client):
    client.post(
        "/api/companies",
        json={"name": "ATOSS", "slug": "atoss-logo", "type": "competitor"},
    )
    response = client.get("/api/companies/atoss-logo")
    assert response.status_code == 200
    data = response.json()
    assert "logo_path" in data
    assert data["logo_path"] is None

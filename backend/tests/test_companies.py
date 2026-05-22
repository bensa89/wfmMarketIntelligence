import io
import pathlib
from unittest.mock import patch

from app.models.company import Company  # noqa: F401 — register table with Base

FAKE_UPLOAD_DIR = pathlib.Path("/tmp/test_uploads")


def _make_png() -> bytes:
    # 1×1 red pixel PNG (valid PNG, tiny)
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "z8BQDwADhQGAWjR9awAAAABJRU5ErkJggg=="
    )


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


def test_upload_logo_png(client):
    client.post("/api/companies", json={"name": "Test Co", "slug": "test-co", "type": "competitor"})
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = client.post(
            "/api/companies/test-co/logo",
            files={"file": ("logo.png", io.BytesIO(_make_png()), "image/png")},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["logo_path"] == "logos/test-co.png"


def test_upload_logo_svg(client):
    client.post("/api/companies", json={"name": "SVG Co", "slug": "svg-co", "type": "competitor"})
    svg_content = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = client.post(
            "/api/companies/svg-co/logo",
            files={"file": ("logo.svg", io.BytesIO(svg_content), "image/svg+xml")},
        )
    assert response.status_code == 200
    assert response.json()["logo_path"] == "logos/svg-co.svg"


def test_upload_logo_invalid_mime(client):
    client.post("/api/companies", json={"name": "Bad Co", "slug": "bad-co", "type": "competitor"})
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = client.post(
            "/api/companies/bad-co/logo",
            files={"file": ("doc.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
    assert response.status_code == 400
    assert "Ungültiger Dateityp" in response.json()["detail"]


def test_upload_logo_too_large(client):
    client.post("/api/companies", json={"name": "Big Co", "slug": "big-co", "type": "competitor"})
    large_file = io.BytesIO(b"x" * (2 * 1024 * 1024 + 1))
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        response = client.post(
            "/api/companies/big-co/logo",
            files={"file": ("big.png", large_file, "image/png")},
        )
    assert response.status_code == 400
    assert "zu groß" in response.json()["detail"]


def test_upload_logo_replaces_old_file(client):
    client.post("/api/companies", json={"name": "Re Co", "slug": "re-co", "type": "competitor"})
    svg_content = b'<svg xmlns="http://www.w3.org/2000/svg"/>'
    with patch("app.routers.companies.LOGO_DIR", FAKE_UPLOAD_DIR):
        FAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        # Upload PNG first
        client.post(
            "/api/companies/re-co/logo",
            files={"file": ("logo.png", io.BytesIO(_make_png()), "image/png")},
        )
        # Upload SVG — old PNG should be deleted
        response = client.post(
            "/api/companies/re-co/logo",
            files={"file": ("logo.svg", io.BytesIO(svg_content), "image/svg+xml")},
        )
    assert response.status_code == 200
    assert response.json()["logo_path"] == "logos/re-co.svg"
    # Old file should not exist
    assert not (FAKE_UPLOAD_DIR / "re-co.png").exists()

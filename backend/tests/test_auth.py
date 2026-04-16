def test_unauthenticated_request_is_rejected(client):
    from fastapi.testclient import TestClient
    from app.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/companies")
    assert response.status_code == 401


def test_authenticated_request_succeeds(client):
    response = client.get("/api/companies")
    assert response.status_code == 200

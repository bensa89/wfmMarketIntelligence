import base64
from fastapi.testclient import TestClient


def _basic(username: str, password: str) -> dict:
    return {"Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode()}


def test_valid_admin_credentials(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_unauthenticated_request_is_rejected(client):
    from app.main import app

    unauthenticated = TestClient(app)
    response = unauthenticated.get("/api/companies")
    assert response.status_code == 401


def test_authenticated_request_succeeds(client):
    response = client.get("/api/companies")
    assert response.status_code == 200


def test_invalid_credentials_rejected(db_session):
    from app.main import app
    from app.database import get_db

    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app, headers=_basic("wrong", "wrong")) as c:
        resp = c.get("/api/health")
    app.dependency_overrides.clear()
    assert resp.status_code == 401


def test_inactive_user_rejected(db_session):
    from app.main import app
    from app.database import get_db
    from app.models.user import User

    user = db_session.query(User).filter_by(username="testuser").first()
    user.is_active = False
    db_session.commit()

    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app, headers=_basic("testuser", "testpass")) as c:
        resp = c.get("/api/health")
    app.dependency_overrides.clear()
    assert resp.status_code == 401

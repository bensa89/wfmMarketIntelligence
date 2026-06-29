def test_me_returns_current_user(client):
    resp = client.get("/api/users/me")
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "testuser"
    assert data["role"] == "admin"


def test_list_users_admin_only(client, user_client):
    assert client.get("/api/users").status_code == 200
    assert user_client.get("/api/users").status_code == 403


def test_create_user(client):
    payload = {"username": "newuser", "password": "secret123", "role": "user"}
    resp = client.post("/api/users", json=payload)
    assert resp.status_code == 201
    assert resp.json()["username"] == "newuser"


def test_create_duplicate_username_fails(client):
    client.post("/api/users", json={"username": "dup", "password": "password1", "role": "user"})
    resp = client.post("/api/users", json={"username": "dup", "password": "password2", "role": "user"})
    assert resp.status_code == 409


def test_create_user_requires_admin(user_client):
    resp = user_client.post("/api/users", json={"username": "x", "password": "password1", "role": "user"})
    assert resp.status_code == 403


def test_update_user_role(client):
    create = client.post("/api/users", json={"username": "tochange", "password": "password1", "role": "user"})
    uid = create.json()["id"]
    resp = client.put(f"/api/users/{uid}", json={"role": "admin"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_delete_last_admin_blocked(client, db_session):
    from app.models.user import User
    admin = db_session.query(User).filter_by(username="testuser").first()
    resp = client.delete(f"/api/users/{admin.id}")
    assert resp.status_code == 409


def test_delete_user(client):
    create = client.post("/api/users", json={"username": "todelete", "password": "password1", "role": "user"})
    uid = create.json()["id"]
    assert client.delete(f"/api/users/{uid}").status_code == 204


def test_change_own_password(client):
    resp = client.put("/api/users/me/password", json={"current_password": "testpass", "new_password": "newpass123"})
    assert resp.status_code == 200


def test_change_own_password_wrong_current(client):
    resp = client.put("/api/users/me/password", json={"current_password": "wrongpwd123", "new_password": "newpass123"})
    assert resp.status_code == 400

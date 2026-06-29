def test_user_cannot_create_company(user_client):
    resp = user_client.post("/api/companies", json={"name": "X", "slug": "x", "type": "competitor"})
    assert resp.status_code == 403


def test_user_can_list_companies(user_client):
    assert user_client.get("/api/companies").status_code == 200


def test_user_cannot_create_source(user_client, client):
    client.post("/api/companies", json={"name": "C", "slug": "c-role", "type": "competitor"})
    company = client.get("/api/companies/c-role").json()
    resp = user_client.post("/api/sources", json={
        "url": "https://example.com",
        "type": "blog",
        "company_id": company["id"],
    })
    assert resp.status_code == 403


def test_user_cannot_update_context(user_client):
    resp = user_client.put("/api/context", json={"target_industries": ["HR"]})
    assert resp.status_code == 403


def test_user_cannot_generate_digest(user_client):
    resp = user_client.post("/api/digests/generate")
    assert resp.status_code == 403


def test_user_can_list_digests(user_client):
    assert user_client.get("/api/digests").status_code == 200


def test_user_cannot_update_schedule(user_client):
    resp = user_client.put("/api/schedule", json={"enabled": False})
    assert resp.status_code == 403


def test_user_cannot_update_settings(user_client):
    resp = user_client.put("/api/admin/settings/some_key", json={"value": "x"})
    assert resp.status_code in (403, 404)

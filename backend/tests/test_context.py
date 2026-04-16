def test_get_context_creates_empty_singleton_on_first_call(client):
    response = client.get("/api/context")
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] is None
    assert data["target_industries"] == []


def test_update_context(client):
    payload = {
        "company_name": "WFM Corp",
        "target_industries": ["Retail", "Logistics"],
        "core_capabilities": ["WFM", "Analytics"],
    }
    response = client.put("/api/context", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "WFM Corp"
    assert data["target_industries"] == ["Retail", "Logistics"]


def test_context_is_singleton(client):
    client.put("/api/context", json={"company_name": "Corp A"})
    client.put("/api/context", json={"company_name": "Corp B"})
    response = client.get("/api/context")
    assert response.json()["company_name"] == "Corp B"


def test_partial_update_preserves_fields(client):
    client.put(
        "/api/context", json={"company_name": "WFM", "target_industries": ["Retail"]}
    )
    client.put("/api/context", json={"core_capabilities": ["Planning"]})
    response = client.get("/api/context")
    assert response.json()["company_name"] == "WFM"
    assert response.json()["core_capabilities"] == ["Planning"]

from .conftest import headers

VALID = {"description": "O botão de cadastro não responde.", "page_url": "https://loja.com/cadastro"}


def test_create_complaint_returns_protocol(client):
    r = client.post("/api/support/complaints", json=VALID, headers=headers())
    assert r.status_code == 201
    assert r.json["protocol"].startswith("LPD-") and r.json["protocol"].endswith("-0001")
    assert r.headers["Access-Control-Allow-Origin"] == "https://loja.com"


def test_protocols_are_sequential(client):
    a = client.post("/api/support/complaints", json=VALID, headers=headers()).json["protocol"]
    b = client.post("/api/support/complaints", json=VALID, headers=headers()).json["protocol"]
    assert a != b and b.endswith("-0002")


def test_missing_and_invalid_key(client):
    assert client.post("/api/support/complaints", json=VALID).status_code == 401
    assert client.post("/api/support/complaints", json=VALID, headers=headers(key="x")).status_code == 401


def test_foreign_origin_is_rejected(client):
    r = client.post("/api/support/complaints", json=VALID, headers=headers(origin="https://evil.com"))
    assert r.status_code == 403
    assert "Access-Control-Allow-Origin" not in r.headers


def test_subdomain_is_allowed(client):
    r = client.post("/api/support/complaints", json=VALID, headers=headers(origin="https://app.loja.com"))
    assert r.status_code == 201


def test_validation_errors(client):
    bad = {"description": "curto", "page_url": "javascript:alert(1)", "contact_email": "x"}
    r = client.post("/api/support/complaints", json=bad, headers=headers())
    assert r.status_code == 422
    assert set(r.json["fields"]) == {"description", "page_url", "contact_email"}


def test_rate_limit(client):
    codes = [client.post("/api/support/complaints", json=VALID, headers=headers()).status_code for _ in range(6)]
    assert codes[:5] == [201] * 5 and codes[5] == 429


def test_status_lookup_scoped_to_site(client):
    proto = client.post("/api/support/complaints", json=VALID, headers=headers()).json["protocol"]
    ok = client.get(f"/api/support/complaints/{proto}", headers=headers())
    assert ok.status_code == 200 and ok.json["status"] == "new"
    assert client.get("/api/support/complaints/LPD-00000000-9999", headers=headers()).status_code == 404


def test_preflight_known_origin(client):
    r = client.options("/api/support/complaints", headers={"Origin": "https://loja.com"})
    assert r.headers["Access-Control-Allow-Origin"] == "https://loja.com"
    r = client.options("/api/support/complaints", headers={"Origin": "https://evil.com"})
    assert "Access-Control-Allow-Origin" not in r.headers

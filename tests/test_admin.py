import re

from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD, headers


def _csrf(client, url="/admin/login"):
    html = client.get(url).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def _login(client):
    return client.post(
        "/admin/login",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "csrf_token": _csrf(client)},
    )


def test_admin_routes_require_login(client):
    for path in ("/admin/", "/admin/complaints", "/admin/sites", "/admin/activity"):
        r = client.get(path)
        assert r.status_code == 302 and "/admin/login" in r.headers["Location"]


def test_login_success_and_failure(client):
    bad = client.post("/admin/login", data={"email": ADMIN_EMAIL, "password": "errada", "csrf_token": _csrf(client)})
    assert bad.status_code == 200 and "incorretos" in bad.get_data(as_text=True)
    assert _login(client).status_code == 302
    assert client.get("/admin/").status_code == 200


def test_login_requires_csrf(client):
    r = client.post("/admin/login", data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 400


def test_login_open_redirect_blocked(client):
    r = client.post(
        "/admin/login?next=//evil.com",
        data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "csrf_token": _csrf(client)},
    )
    assert r.headers["Location"].endswith("/admin/")


def test_login_is_rate_limited(client):
    token = _csrf(client)
    codes = [
        client.post("/admin/login", data={"email": "x@x.com", "password": "n", "csrf_token": token}).status_code
        for _ in range(6)
    ]
    assert codes[-1] == 429


def test_status_change_is_logged(client):
    proto = client.post(
        "/api/support/complaints",
        json={"description": "Erro ao finalizar a compra.", "page_url": "https://loja.com/c"},
        headers=headers(),
    ).json["protocol"]
    _login(client)
    page = client.get("/admin/complaints/1")
    assert proto in page.get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)).group(1)

    assert client.post("/admin/complaints/1/status", data={"status": "resolved"}).status_code == 400  # sem CSRF
    assert client.post("/admin/complaints/1/status", data={"status": "resolved", "csrf_token": token}).status_code == 302
    assert "Resolvida" in client.get("/admin/complaints/1").get_data(as_text=True)
    assert "complaint.status_changed" in client.get("/admin/activity").get_data(as_text=True)


def test_xss_is_escaped(client):
    client.post(
        "/api/support/complaints",
        json={"description": "<script>alert(1)</script> falha", "page_url": "https://loja.com/"},
        headers=headers(),
    )
    _login(client)
    html = client.get("/admin/complaints/1").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


def test_site_create_and_duplicate(client):
    _login(client)
    token = _csrf(client, "/admin/sites")
    ok = client.post("/admin/sites", data={"name": "Blog", "domain": "https://www.blog.com/x", "csrf_token": token})
    assert ok.status_code == 302
    assert "www.blog.com" in client.get("/admin/sites").get_data(as_text=True)
    client.post("/admin/sites", data={"name": "Blog2", "domain": "www.blog.com", "csrf_token": token})
    assert "já está conectado" in client.get("/admin/sites").get_data(as_text=True)

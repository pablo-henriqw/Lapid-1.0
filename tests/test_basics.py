def test_health(client):
    assert client.get("/healthz").json == {"status": "ok"}


def test_widget_served(client):
    r = client.get("/widget.js")
    assert r.status_code == 200 and b"attachShadow" in r.data


def test_demo_disabled_by_default(client):
    assert client.get("/demo").status_code == 404

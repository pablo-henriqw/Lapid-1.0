import pytest
from werkzeug.security import generate_password_hash

from backend.app import create_app
from backend.extensions import db
from backend.models import Site

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "senha-de-teste-123"


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SECRET_KEY": "test",
            "ADMIN_EMAIL": ADMIN_EMAIL,
            "ADMIN_PASSWORD_HASH": generate_password_hash(ADMIN_PASSWORD),
            "ENABLE_DEMO": False,
        }
    )
    with app.app_context():
        db.session.add(Site(name="Loja", domain="loja.com", api_key="lpd_testkey"))
        db.session.commit()
        yield app
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


def headers(origin="https://loja.com", key="lpd_testkey"):
    h = {"X-Lapid-Key": key}
    if origin:
        h["Origin"] = origin
    return h

import logging
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

from . import cli, filters
from .config import BASE_DIR, Config
from .extensions import db
from .security import RateLimiter, csrf_token


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "frontend" / "templates"),
        static_folder=str(BASE_DIR / "frontend" / "static"),
        instance_path=str(BASE_DIR / "instance"),
    )
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    Path(app.instance_path).mkdir(exist_ok=True)

    if app.config.get("SECRET_KEY_IS_EPHEMERAL") and not app.testing:
        logging.getLogger(__name__).warning(
            "SECRET_KEY não definida: sessões serão invalidadas a cada reinício. Defina no .env."
        )
    if app.config["PROXY_COUNT"] > 0:
        n = app.config["PROXY_COUNT"]
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=n, x_proto=n, x_host=n)

    db.init_app(app)
    app.extensions["limiter"] = RateLimiter()
    app.jinja_env.globals["csrf_token"] = csrf_token
    filters.register(app)
    cli.register(app)

    from .routes import admin, public, support

    app.register_blueprint(public.bp)
    app.register_blueprint(support.bp)
    app.register_blueprint(admin.bp)

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if request.path.startswith("/admin"):
            resp.headers.setdefault("X-Frame-Options", "DENY")
        return resp

    @app.errorhandler(413)
    def _too_large(_):
        return jsonify(error="payload_too_large", message="Requisição grande demais."), 413

    with app.app_context():
        db.create_all()  # Etapa 1: sem migrações. Alembic entra quando migrarmos para PostgreSQL.

    return app

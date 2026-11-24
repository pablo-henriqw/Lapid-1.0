from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, send_from_directory, url_for

from ..config import BASE_DIR
from ..models import Site

bp = Blueprint("public", __name__)


@bp.get("/")
def index():
    return redirect(url_for("admin.overview"))


@bp.get("/healthz")
def healthz():
    return jsonify(status="ok")


@bp.get("/widget.js")
def widget():
    resp = send_from_directory(BASE_DIR / "widget", "lapid-widget.js", mimetype="application/javascript")
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@bp.get("/demo")
def demo():
    if not current_app.config["ENABLE_DEMO"]:
        abort(404)
    site = Site.query.filter_by(is_active=True).order_by(Site.id).first()
    return render_template("demo.html", site=site)

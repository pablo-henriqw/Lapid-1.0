"""Dashboard administrativo (renderizado no servidor)."""
import hmac
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   session, url_for)
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash

from ..extensions import db
from ..models import STATUSES, ActivityLog, Complaint, Site, utcnow
from ..security import client_ip, csrf_valid, limiter, safe_next
from ..services.activity import log_activity
from ..validators import clean_text, is_valid_domain, normalize_domain

bp = Blueprint("admin", __name__, url_prefix="/admin")

PER_PAGE = 15


@bp.before_request
def _guard():
    if request.method == "POST" and not csrf_valid():
        abort(400, "Token CSRF inválido. Recarregue a página.")
    if request.endpoint != "admin.login" and not session.get("admin"):
        return redirect(url_for("admin.login", next=request.path))


@bp.after_request
def _headers(resp):
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
    )
    return resp


# ---------- Autenticação ----------
@bp.route("/login", methods=["GET", "POST"])
def login():
    cfg = current_app.config
    configured = bool(cfg["ADMIN_EMAIL"] and cfg["ADMIN_PASSWORD_HASH"])
    if session.get("admin"):
        return redirect(url_for("admin.overview"))

    if request.method == "POST":
        if not limiter().allow(f"login:{client_ip()}", 5, 300):
            flash("Muitas tentativas. Aguarde alguns minutos.", "error")
            return render_template("login.html", configured=configured), 429

        email = clean_text(request.form.get("email"), 254).lower()
        password = request.form.get("password", "")[:200]
        # Ambas as verificações sempre executam (evita vazar qual campo errou pelo tempo de resposta).
        email_ok = hmac.compare_digest(email, cfg["ADMIN_EMAIL"].lower())
        pass_ok = bool(cfg["ADMIN_PASSWORD_HASH"]) and check_password_hash(cfg["ADMIN_PASSWORD_HASH"], password)

        if configured and email_ok and pass_ok:
            session.clear()  # evita fixação de sessão
            session["admin"] = email
            session.permanent = True
            log_activity("admin.login", actor=email)
            db.session.commit()
            return redirect(safe_next(request.args.get("next", "")))

        log_activity("admin.login_failed", details=f"IP {client_ip()}", actor="anonymous")
        db.session.commit()
        flash("E-mail ou senha incorretos.", "error")

    return render_template("login.html", configured=configured)


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


# ---------- Visão geral ----------
@bp.get("/")
def overview():
    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    by_status = dict(db.session.query(Complaint.status, func.count()).group_by(Complaint.status).all())

    today = datetime.now(tz).date()
    first_day = today - timedelta(days=13)
    start_utc = datetime.combine(first_day, time.min, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    rows = db.session.query(Complaint.created_at).filter(Complaint.created_at >= start_utc).all()
    per_day = Counter(r[0].replace(tzinfo=timezone.utc).astimezone(tz).date() for r in rows)
    peak = max(per_day.values(), default=0)

    bars = []
    for i in range(14):
        d: date = first_day + timedelta(days=i)
        n = per_day.get(d, 0)
        h = max(3, round(n / peak * 92)) if peak else 3
        bars.append({"x": i * 28, "y": 100 - h, "h": h, "n": n, "label": f"{d:%d/%m}", "day": f"{d:%d}"})

    return render_template(
        "overview.html",
        stats={
            "total": sum(by_status.values()),
            "new": by_status.get("new", 0),
            "in_review": by_status.get("in_review", 0),
            "resolved": by_status.get("resolved", 0),
            "last14": sum(per_day.values()),
        },
        bars=bars,
        recent=Complaint.query.order_by(Complaint.created_at.desc()).limit(6).all(),
        sites_active=Site.query.filter_by(is_active=True).count(),
    )


# ---------- Reclamações ----------
@bp.get("/complaints")
def complaints():
    q = Complaint.query
    status = request.args.get("status", "")
    site_id = request.args.get("site", type=int)
    term = clean_text(request.args.get("q"), 100)
    if status in STATUSES:
        q = q.filter(Complaint.status == status)
    if site_id:
        q = q.filter(Complaint.site_id == site_id)
    if term:
        like = f"%{term}%"
        q = q.filter(Complaint.description.ilike(like) | Complaint.protocol.ilike(like))
    page = q.order_by(Complaint.created_at.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=PER_PAGE, error_out=False
    )
    return render_template(
        "complaints.html", page=page, statuses=STATUSES, sites=Site.query.order_by(Site.name).all(),
        f={"status": status, "site": site_id, "q": term},
    )


@bp.get("/complaints/<int:cid>")
def complaint_detail(cid):
    c = db.get_or_404(Complaint, cid)
    history = (
        ActivityLog.query.filter_by(entity="complaint", entity_id=c.id)
        .order_by(ActivityLog.created_at.desc())
        .all()
    )
    return render_template("complaint_detail.html", c=c, history=history, statuses=STATUSES)


@bp.post("/complaints/<int:cid>/status")
def complaint_status(cid):
    c = db.get_or_404(Complaint, cid)
    new = request.form.get("status", "")
    if new not in STATUSES:
        abort(400)
    if new != c.status:
        old, c.status, c.updated_at = c.status, new, utcnow()
        log_activity(
            "complaint.status_changed", "complaint", c.id,
            f"{c.protocol}: {STATUSES[old]} → {STATUSES[new]}", actor=session["admin"],
        )
        db.session.commit()
        flash(f"Situação alterada para “{STATUSES[new]}”.", "ok")
    return redirect(url_for("admin.complaint_detail", cid=c.id))


# ---------- Sites ----------
@bp.get("/sites")
def sites():
    rows = (
        db.session.query(Site, func.count(Complaint.id))
        .outerjoin(Complaint, Complaint.site_id == Site.id)
        .group_by(Site.id)
        .order_by(Site.name)
        .all()
    )
    return render_template("sites.html", rows=rows, base_url=request.host_url.rstrip("/"))


@bp.post("/sites")
def site_create():
    name = clean_text(request.form.get("name"), 120)
    domain = normalize_domain(request.form.get("domain", ""))
    if len(name) < 2:
        flash("Informe o nome do site.", "error")
    elif not is_valid_domain(domain):
        flash("Domínio inválido. Exemplo: meusite.com.br", "error")
    else:
        site = Site(name=name, domain=domain)
        db.session.add(site)
        try:
            db.session.flush()
            log_activity("site.created", "site", site.id, f"{name} ({domain})", actor=session["admin"])
            db.session.commit()
            flash(f"Site “{name}” conectado.", "ok")
        except IntegrityError:
            db.session.rollback()
            flash("Este domínio já está conectado.", "error")
    return redirect(url_for("admin.sites"))


@bp.post("/sites/<int:sid>/toggle")
def site_toggle(sid):
    site = db.get_or_404(Site, sid)
    site.is_active = not site.is_active
    log_activity(
        "site.activated" if site.is_active else "site.deactivated", "site", site.id, site.name,
        actor=session["admin"],
    )
    db.session.commit()
    return redirect(url_for("admin.sites"))


# ---------- Atividade ----------
@bp.get("/activity")
def activity():
    page = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=25, error_out=False
    )
    return render_template("activity.html", page=page)

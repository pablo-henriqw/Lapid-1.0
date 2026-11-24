"""API pública consumida pelo widget (autenticada pela chave do site)."""
from flask import Blueprint, current_app, jsonify, request

from ..models import Complaint, Site
from ..security import client_ip, limiter, origin_allowed, origin_is_known
from ..services.complaints import create_complaint
from ..validators import validate_complaint

bp = Blueprint("support", __name__, url_prefix="/api/support")


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


@bp.errorhandler(ApiError)
def _api_error(e):
    return jsonify(error=e.code, message=e.message), e.status


@bp.after_request
def _cors(resp):
    origin = request.headers.get("Origin")
    if origin and origin_is_known(origin):
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Lapid-Key"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Max-Age"] = "600"
    return resp


def _authenticate() -> Site:
    key = request.headers.get("X-Lapid-Key", "").strip()
    if not key:
        raise ApiError(401, "missing_key", "Chave do site ausente.")
    site = Site.query.filter_by(api_key=key, is_active=True).first()
    if not site:
        raise ApiError(401, "invalid_key", "Chave do site inválida.")
    origin = request.headers.get("Origin")
    if origin and not origin_allowed(site, origin):
        raise ApiError(403, "origin_not_allowed", "Este site não está autorizado a usar esta chave.")
    return site


def _throttle(bucket: str, limit: int, window: int):
    if not limiter().allow(f"{bucket}:{client_ip()}", limit, window):
        raise ApiError(429, "rate_limited", "Muitas solicitações. Tente novamente em alguns minutos.")


def _serialize(c: Complaint) -> dict:
    return {
        "protocol": c.protocol,
        "status": c.status,
        "status_label": c.status_label,
        "created_at": c.created_at.isoformat() + "Z",
    }


@bp.post("/complaints")
def create():
    site = _authenticate()
    _throttle("complaint", 5, 600)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "Corpo da requisição inválido.")

    cleaned, errors = validate_complaint(
        data, current_app.config["COMPLAINT_MIN_LEN"], current_app.config["COMPLAINT_MAX_LEN"]
    )
    if errors:
        return jsonify(error="validation_error", fields=errors), 422

    complaint = create_complaint(site, user_agent=request.headers.get("User-Agent"), **cleaned)
    return jsonify(_serialize(complaint)), 201


@bp.get("/complaints/<protocol>")
def status(protocol):
    site = _authenticate()
    _throttle("status", 60, 60)
    complaint = Complaint.query.filter_by(protocol=protocol[:24], site_id=site.id).first()
    if not complaint:
        raise ApiError(404, "not_found", "Protocolo não encontrado.")
    return jsonify(_serialize(complaint))

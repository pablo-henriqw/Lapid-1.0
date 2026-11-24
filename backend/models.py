import secrets
from datetime import datetime, timezone

from .extensions import db


def utcnow() -> datetime:
    """Datetime UTC sem tzinfo (padrão de armazenamento do projeto)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


STATUSES = {
    "new": "Nova",
    "in_review": "Em análise",
    "resolved": "Resolvida",
    "dismissed": "Descartada",
}


def _new_key() -> str:
    return "lpd_" + secrets.token_urlsafe(24)


class Site(db.Model):
    __tablename__ = "sites"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    domain = db.Column(db.String(255), unique=True, nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False, default=_new_key)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    complaints = db.relationship("Complaint", back_populates="site", lazy="dynamic")


class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    protocol = db.Column(db.String(24), unique=True, nullable=False, index=True)
    site_id = db.Column(db.Integer, db.ForeignKey("sites.id"), nullable=False, index=True)
    page_url = db.Column(db.String(2048), nullable=False)
    description = db.Column(db.Text, nullable=False)
    contact_email = db.Column(db.String(254))
    user_agent = db.Column(db.String(300))
    status = db.Column(db.String(20), nullable=False, default="new", index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    site = db.relationship("Site", back_populates="complaints")

    @property
    def status_label(self) -> str:
        return STATUSES.get(self.status, self.status)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(60), nullable=False, index=True)
    entity = db.Column(db.String(40))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.String(500))
    actor = db.Column(db.String(120), nullable=False, default="system")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

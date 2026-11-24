from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Complaint
from .activity import log_activity


def create_complaint(site, description, page_url, contact_email, user_agent):
    """Cria a reclamação com protocolo LPD-AAAAMMDD-NNNN (sequência diária)."""
    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    prefix = f"LPD-{datetime.now(tz):%Y%m%d}-"
    base = (
        db.session.query(func.count(Complaint.id)).filter(Complaint.protocol.like(prefix + "%")).scalar()
    )
    site_id, site_name = site.id, site.name

    for attempt in range(5):  # tenta de novo se dois relatos colidirem no mesmo número
        complaint = Complaint(
            protocol=f"{prefix}{base + 1 + attempt:04d}",
            site_id=site_id,
            page_url=page_url,
            description=description,
            contact_email=contact_email,
            user_agent=(user_agent or "")[:300] or None,
        )
        db.session.add(complaint)
        try:
            db.session.flush()
            log_activity(
                "complaint.created",
                "complaint",
                complaint.id,
                f"{complaint.protocol} em {site_name}",
                actor="widget",
            )
            db.session.commit()
            return complaint
        except IntegrityError:
            db.session.rollback()
    raise RuntimeError("Não foi possível gerar um protocolo único.")

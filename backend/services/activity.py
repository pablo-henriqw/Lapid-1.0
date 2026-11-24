from ..extensions import db
from ..models import ActivityLog


def log_activity(action, entity=None, entity_id=None, details=None, actor="system"):
    """Adiciona um registro ao histórico. O commit fica com quem chama."""
    db.session.add(
        ActivityLog(
            action=action,
            entity=entity,
            entity_id=entity_id,
            details=(details or "")[:500] or None,
            actor=actor,
        )
    )

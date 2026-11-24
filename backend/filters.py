from datetime import timezone
from zoneinfo import ZoneInfo

from flask import current_app


def localtime(value, fmt="%d/%m/%Y %H:%M"):
    if not value:
        return "—"
    tz = ZoneInfo(current_app.config["APP_TIMEZONE"])
    return value.replace(tzinfo=timezone.utc).astimezone(tz).strftime(fmt)


def register(app):
    app.jinja_env.filters["localtime"] = localtime

import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from urllib.parse import urlparse

from flask import current_app, redirect, request, session, url_for

from .models import Site


class RateLimiter:
    """Limitador em memória (suficiente para 1 processo; trocar por Redis ao escalar)."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


def limiter() -> RateLimiter:
    return current_app.extensions["limiter"]


def client_ip() -> str:
    return request.remote_addr or "unknown"


# ---------- Origem (widget) ----------
def _hostname(origin: str):
    try:
        return urlparse(origin).hostname
    except ValueError:
        return None


def _same_origin_demo(host: str) -> bool:
    return bool(current_app.config.get("ENABLE_DEMO")) and host == request.host.split(":")[0]


def host_matches(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def origin_allowed(site: Site, origin: str) -> bool:
    host = _hostname(origin)
    return bool(host) and (host_matches(host, site.domain) or _same_origin_demo(host))


def origin_is_known(origin: str) -> bool:
    host = _hostname(origin)
    if not host:
        return False
    if _same_origin_demo(host):
        return True
    return any(host_matches(host, s.domain) for s in Site.query.filter_by(is_active=True))


# ---------- Admin ----------
def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def csrf_valid() -> bool:
    sent = request.form.get("csrf_token", "")
    return bool(sent) and hmac.compare_digest(sent, session.get("csrf_token", ""))


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def safe_next(target: str) -> str:
    if target and target.startswith("/admin") and not target.startswith("//"):
        return target
    return url_for("admin.overview")

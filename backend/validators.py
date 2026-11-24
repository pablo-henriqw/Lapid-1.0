import re
from urllib.parse import urlparse

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DOMAIN = re.compile(r"^(localhost|([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,})$")


def clean_text(value, max_len: int) -> str:
    if not isinstance(value, str):
        return ""
    return _CONTROL.sub("", value).strip()[:max_len]


def normalize_domain(raw: str) -> str:
    """Aceita 'https://www.site.com/x' ou 'site.com:8080' e devolve 'www.site.com'/'site.com'."""
    raw = (raw or "").strip().lower()
    if "://" not in raw:
        raw = "//" + raw
    return (urlparse(raw).hostname or "").strip(".")


def is_valid_domain(domain: str) -> bool:
    return bool(_DOMAIN.match(domain)) and len(domain) <= 255


def validate_complaint(data: dict, min_len: int, max_len: int):
    errors, cleaned = {}, {}

    description = clean_text(data.get("description"), max_len + 1)
    if len(description) < min_len:
        errors["description"] = f"Descreva o problema com pelo menos {min_len} caracteres."
    elif len(description) > max_len:
        errors["description"] = f"A descrição deve ter no máximo {max_len} caracteres."
    cleaned["description"] = description

    page_url = clean_text(data.get("page_url"), 2049)
    parsed = urlparse(page_url)
    if not page_url or parsed.scheme not in ("http", "https") or not parsed.netloc or len(page_url) > 2048:
        errors["page_url"] = "URL da página inválida."
    cleaned["page_url"] = page_url

    email = clean_text(data.get("contact_email"), 255)
    if email and (len(email) > 254 or not _EMAIL.match(email)):
        errors["contact_email"] = "E-mail inválido."
    cleaned["contact_email"] = email or None

    return cleaned, errors

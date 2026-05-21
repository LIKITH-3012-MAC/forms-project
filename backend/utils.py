import html
import secrets
import string
import datetime
from typing import Any

def get_ist_time() -> datetime.datetime:
    """Returns the current time in IST (UTC +5:30)."""
    return datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)

def generate_secure_token() -> str:
    """Generates a secure url-safe token for edit/view/status links."""
    return secrets.token_urlsafe(32)

def generate_registration_id(prefix: str = "REG") -> str:
    """Generates a unique registration ID like REG-2026-X8Y9Z."""
    year = datetime.datetime.now().year
    random_str = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"{prefix}-{year}-{random_str}"

def escape_html(value: Any) -> str:
    """Escapes HTML special characters to prevent XSS vulnerability in rendered pages."""
    if value is None:
        return ""
    return html.escape(str(value))

def format_datetime(dt: Any) -> str:
    """Formats a datetime object to a friendly string."""
    if not dt:
        return "-"
    return dt.strftime("%b %d, %Y %I:%M %p")

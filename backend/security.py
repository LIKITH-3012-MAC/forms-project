from typing import Optional
from itsdangerous import URLSafeSerializer, BadSignature
import bcrypt
import config

# Create serializer using SECRET_KEY from config
serializer = URLSafeSerializer(config.SECRET_KEY)

def sign_session(data: str) -> str:
    """Signs the session data (e.g., admin identifier) to be set in a cookie."""
    return serializer.dumps(data)

def verify_session(signed_data: str) -> Optional[str]:
    """Verifies and decodes the signed session data. Returns None if invalid."""
    if not signed_data:
        return None
    try:
        return serializer.loads(signed_data)
    except BadSignature:
        return None

def hash_password(password: str) -> str:
    """Hashes a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a hashed bcrypt password."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

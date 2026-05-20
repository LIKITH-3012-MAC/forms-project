from typing import Optional
from itsdangerous import URLSafeSerializer, BadSignature
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

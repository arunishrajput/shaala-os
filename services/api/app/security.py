import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def qr_token_for(admission_no: str) -> str:
    """Shared by seed.py (initial students) and the admission_form commit path
    (Phase 3) so every student's QR token is derived the same, stable way."""
    key = settings.jwt_secret.encode() or b"dev-only-fixed-key"
    return hmac.new(key, admission_no.encode(), hashlib.sha256).hexdigest()[:20]


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(subject: dict[str, Any]) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {**subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None

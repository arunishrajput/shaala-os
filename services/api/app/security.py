import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def qr_token_for(admission_no: str) -> str:
    """Shared by seed.py (initial students) and the admission_form commit path
    (Phase 3) so every student's QR token is derived the same, stable way."""
    # Use the configured secret — never fall back to a hardcoded key.
    # config.py's startup guard already ensured the secret is non-empty.
    key = settings.jwt_secret.encode()
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


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """FastAPI dependency — inject into every route that requires a logged-in user.

    Usage in a router::

        @router.get("/some-endpoint")
        def handler(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
            ...

    Or once at router level (applies to all routes in the file)::

        router = APIRouter(..., dependencies=[Depends(get_current_user)])
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

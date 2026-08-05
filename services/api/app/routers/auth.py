from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.db.session import get_db
from app.schemas import LoginRequest, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Fixed demo accounts seeded by seed.py — this is the "auth beyond JWT + three demo
# logins" boundary from CLAUDE.md, on purpose.
DEMO_EMAILS: dict[UserRole, str] = {
    UserRole.admin: "admin@shaala.demo",
    UserRole.teacher: "teacher@shaala.demo",
    UserRole.parent: "parent@shaala.demo",
}


def _token_for_user(user: User) -> TokenResponse:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
        linked_id=user.linked_id,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_for_user(user)


@router.post("/demo-login", response_model=TokenResponse)
def demo_login(role: UserRole, db: Session = Depends(get_db)) -> TokenResponse:
    email = DEMO_EMAILS[role]
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f"Demo user for role={role.value} not seeded — run `make seed`",
        )
    return _token_for_user(user)

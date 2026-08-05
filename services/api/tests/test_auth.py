from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.models import User, UserRole
from app.db.session import SessionLocal
from app.main import app
from app.security import hash_password

client = TestClient(app)

TEST_EMAIL = "pytest-user@shaala.demo"


def _make_user() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.email == TEST_EMAIL))
        db.add(
            User(
                email=TEST_EMAIL,
                password_hash=hash_password("pytest-pass"),
                role=UserRole.admin,
                linked_id=None,
            )
        )
        db.commit()
    finally:
        db.close()


def _delete_user() -> None:
    db = SessionLocal()
    try:
        db.execute(delete(User).where(User.email == TEST_EMAIL))
        db.commit()
    finally:
        db.close()


def test_login_success() -> None:
    _make_user()
    try:
        resp = client.post("/auth/login", json={"email": TEST_EMAIL, "password": "pytest-pass"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == "admin"
        assert body["access_token"]
    finally:
        _delete_user()


def test_login_wrong_password() -> None:
    _make_user()
    try:
        resp = client.post("/auth/login", json={"email": TEST_EMAIL, "password": "wrong"})
        assert resp.status_code == 401
    finally:
        _delete_user()

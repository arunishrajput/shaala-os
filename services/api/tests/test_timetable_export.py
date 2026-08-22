"""Timetable PDF export tests (GET /timetable/export.pdf).

Exercises the three main paths: no active timetable (still returns a PDF),
class view (one page per class), and teacher view (one page per teacher).
Follows the same fixture / seeding pattern as the rest of the test suite.
"""

import pytest
from fastapi.testclient import TestClient

from app.db import seed as seed_module
from app.db.session import SessionLocal
from app.main import app
from app.services.timetable.solver import generate_timetable

client = TestClient(app)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth_header() -> dict:
    """Log in as the seeded admin and return a Bearer header dict."""
    resp = client.post("/auth/demo-login", params={"role": "admin"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def db():
    seed_module.main()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def auth(db):  # noqa: ARG001  — db fixture ensures seed ran first
    return _auth_header()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_export_returns_pdf_when_no_timetable(auth):
    """Even with no active timetable, the endpoint returns a valid PDF (not a 500)."""
    resp = client.get("/timetable/export.pdf", headers=auth)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    # All PDFs start with the PDF magic bytes
    assert resp.content[:4] == b"%PDF"


def test_export_class_view_returns_pdf(db, auth):
    """Class-view export produces a PDF once a timetable has been generated."""
    generate_timetable(db)

    resp = client.get("/timetable/export.pdf", params={"view": "class"}, headers=auth)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_export_teacher_view_returns_pdf(db, auth):
    """Teacher-view export works after timetable generation."""
    resp = client.get("/timetable/export.pdf", params={"view": "teacher"}, headers=auth)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_export_single_class_by_id(db, auth):
    """?class_id=X returns a PDF filtered to that one class."""
    from sqlalchemy import select
    from app.db.models import ClassSection
    section = db.scalar(select(ClassSection).order_by(ClassSection.id))
    assert section is not None

    resp = client.get(
        "/timetable/export.pdf",
        params={"view": "class", "class_id": section.id},
        headers=auth,
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_export_single_teacher_by_id(db, auth):
    """?teacher_id=X returns a PDF filtered to that one teacher."""
    from sqlalchemy import select
    from app.db.models import Teacher
    teacher = db.scalar(select(Teacher).order_by(Teacher.id))
    assert teacher is not None

    resp = client.get(
        "/timetable/export.pdf",
        params={"view": "teacher", "teacher_id": teacher.id},
        headers=auth,
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


def test_export_requires_auth():
    """Endpoint is protected — no token means 401."""
    resp = client.get("/timetable/export.pdf")
    assert resp.status_code == 401


def test_export_invalid_view_param_defaults_to_class(db, auth):
    """An unknown ?view= value falls back to class view without erroring."""
    resp = client.get(
        "/timetable/export.pdf",
        params={"view": "invalid"},
        headers=auth,
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"

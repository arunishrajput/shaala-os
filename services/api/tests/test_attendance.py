"""QR kiosk, manual roll call, and ID-card PDF generation (PROMPT.md §6.4A/C)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import DEMO_ANCHOR_DATE
from app.db import seed as seed_module
from app.db.models import Student
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    seed_module.main()
    session = SessionLocal()
    yield session
    session.close()


def _a_student(db) -> Student:
    return db.scalar(select(Student).order_by(Student.id))


def test_scan_marks_present_and_is_idempotent(db):
    student = _a_student(db)
    first = client.post("/attendance/scan", json={"qr_token": student.qr_token})
    assert first.status_code == 200
    assert first.json()["status"] == "marked"
    assert first.json()["record"]["method"] == "qr"

    second = client.post("/attendance/scan", json={"qr_token": student.qr_token})
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"


def test_scan_with_unknown_token_is_reported_not_errored():
    resp = client.post("/attendance/scan", json={"qr_token": "not-a-real-token"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "unknown"


def test_manual_roll_call_marks_and_updates_status(db):
    student = db.scalars(select(Student).order_by(Student.id)).all()[1]
    resp = client.post("/attendance/manual", json={"student_id": student.id, "status": "present"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "present"
    assert resp.json()["method"] == "manual"

    updated = client.post("/attendance/manual", json={"student_id": student.id, "status": "late"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "late"
    # Same day, same student -- an update, not a second record.
    assert updated.json()["id"] == resp.json()["id"]


def test_attendance_today_reflects_marks(db):
    resp = client.get("/attendance/today")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == DEMO_ANCHOR_DATE.isoformat()
    assert body["count"] >= 2


def test_student_summary_computes_a_percentage(db):
    student = _a_student(db)
    resp = client.get(f"/attendance/student/{student.id}/summary", params={"days": 90})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_records"] > 0
    assert 0 <= body["attendance_pct"] <= 100


def test_group_photo_is_a_loud_stub():
    resp = client.post("/attendance/group-photo")
    assert resp.status_code == 501


def test_id_cards_pdf_is_generated(db):
    resp = client.get("/students/id-cards.pdf", params={"class_id": 1})
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 1000

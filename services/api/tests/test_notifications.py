"""The notification Outbox (PROMPT.md §6.3): drafted, never sent, on two
triggers -- the low_attendance_trend card's "Draft parent messages" and a
successful substitute assignment ("teachers notified").
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import seed as seed_module
from app.db.models import ActionItem, ActionStatus, Notification, Teacher
from app.db.session import SessionLocal
from app.main import app
from app.services.signals import rules  # noqa: F401
from app.services.signals.registry import run_signals
from app.services.timetable.solver import generate_timetable

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    seed_module.main()
    session = SessionLocal()
    generate_timetable(session, label="notifications test")
    run_signals(session)
    yield session
    session.close()


def test_draft_messages_creates_notifications_and_resolves_the_card(db):
    item = db.scalar(
        select(ActionItem).where(
            ActionItem.kind == "low_attendance_trend", ActionItem.status == ActionStatus.open
        )
    )
    assert item is not None, "expected the seeded attendance history to trip this signal"
    student_count = len(item.payload["student_ids"])

    resp = client.post(f"/actions/{item.id}/draft-messages")
    assert resp.status_code == 200
    body = resp.json()
    assert body["drafted"] == student_count
    assert body["action"]["status"] == "resolved"

    notifications = client.get("/notifications", params={"limit": 100}).json()
    assert len(notifications) >= student_count
    assert all(n["status"] == "draft" for n in notifications)


def test_draft_messages_rejects_the_wrong_kind(db):
    other = db.scalar(
        select(ActionItem).where(ActionItem.kind != "low_attendance_trend")
    )
    if other is None:
        pytest.skip("no non-attendance ActionItem currently open to test against")
    resp = client.post(f"/actions/{other.id}/draft-messages")
    assert resp.status_code == 400


def test_substitute_assignment_drafts_a_notice_to_the_new_teacher(db):
    rao = db.scalar(select(Teacher).where(Teacher.name == "Kavita Rao"))
    absence = client.post("/timetable/absence", json={"teacher_id": rao.id}).json()
    period = absence["uncovered_periods"][0]
    candidate = period["candidates"][0]

    before = client.get("/notifications", params={"limit": 100}).json()

    resp = client.post(
        "/timetable/substitute",
        json={
            "absence_id": absence["absence_id"],
            "class_id": period["class_id"],
            "slot_id": period["slot_id"],
            "teacher_id": candidate["teacher_id"],
        },
    )
    assert resp.status_code == 200

    after = client.get("/notifications", params={"limit": 100}).json()
    assert len(after) == len(before) + 1
    newest = after[0]
    assert newest["to_name"] == candidate["teacher_name"]
    assert newest["status"] == "draft"

    db_notification = db.get(Notification, newest["id"])
    assert db_notification is not None

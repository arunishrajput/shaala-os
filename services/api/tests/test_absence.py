"""Substitute engine end to end (PROMPT.md §6.2 point 3, §9 Phase 4): mark a
teacher absent, assign a substitute, watch the absence and its Action Center
card resolve. The underlying algorithm is tested in test_solver.py; this
covers the HTTP wiring (POST /timetable/absence, POST /timetable/substitute)
and the TeacherAbsence.resolved / ActionItem reconciliation on top of it.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import DEMO_ANCHOR_DATE
from app.db import seed as seed_module
from app.db.models import ActionItem, ActionStatus, Teacher, TeacherAbsence
from app.db.session import SessionLocal
from app.main import app
from app.services.timetable.solver import generate_timetable

client = TestClient(app)


@pytest.fixture(scope="module")
def db():
    seed_module.main()
    session = SessionLocal()
    generate_timetable(session, label="absence test")
    yield session
    session.close()


def _rao(db) -> Teacher:
    return db.scalar(select(Teacher).where(Teacher.name == "Kavita Rao"))


def test_mark_absence_creates_a_teacher_absence_and_lists_uncovered_periods(db):
    rao = _rao(db)
    resp = client.post("/timetable/absence", json={"teacher_id": rao.id})
    assert resp.status_code == 200
    body = resp.json()
    assert body["teacher_id"] == rao.id
    assert body["date"] == DEMO_ANCHOR_DATE.isoformat()
    assert body["uncovered_periods"], "expected Kavita Rao to teach on the anchor weekday"
    for period in body["uncovered_periods"]:
        assert period["candidates"]

    absence = db.get(TeacherAbsence, body["absence_id"])
    assert absence.resolved is False


def test_mark_absence_is_idempotent_for_the_same_open_absence(db):
    rao = _rao(db)
    first = client.post("/timetable/absence", json={"teacher_id": rao.id}).json()
    second = client.post("/timetable/absence", json={"teacher_id": rao.id}).json()
    assert first["absence_id"] == second["absence_id"]


def test_substitute_covers_a_period_and_resolves_absence_once_all_covered(db):
    rao = _rao(db)
    absence_resp = client.post("/timetable/absence", json={"teacher_id": rao.id}).json()
    absence_id = absence_resp["absence_id"]
    periods = absence_resp["uncovered_periods"]

    for period in periods:
        candidate = period["candidates"][0]
        resp = client.post(
            "/timetable/substitute",
            json={
                "absence_id": absence_id,
                "class_id": period["class_id"],
                "slot_id": period["slot_id"],
                "teacher_id": candidate["teacher_id"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["entry"]["is_substitution"] is True
        assert body["entry"]["teacher_id"] == candidate["teacher_id"]

    assert body["absence_resolved"] is True
    assert body["uncovered_remaining"] == 0

    db.expire_all()
    absence = db.get(TeacherAbsence, absence_id)
    assert absence.resolved is True

    action = db.scalar(
        select(ActionItem).where(
            ActionItem.kind == "uncovered_classes",
            ActionItem.payload["_key"].astext == f"absence:{absence_id}",
        )
    )
    assert action is None or action.status != ActionStatus.open

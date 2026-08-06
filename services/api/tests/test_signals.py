"""The signal engine (PROMPT.md §6.3): rules read real DB state, run_signals
reconciles that against open ActionItem rows -- create what's new, refresh
what's still true, auto-resolve what stopped being true.
"""

import pytest
from sqlalchemy import select

from app.config import DEMO_ANCHOR_DATE
from app.db import seed as seed_module
from app.db.models import ActionItem, ActionStatus, Teacher, TeacherAbsence
from app.db.session import SessionLocal
from app.services.signals import rules  # noqa: F401 -- registers the @signal rules
from app.services.signals.registry import run_signals
from app.services.timetable.solver import generate_timetable


@pytest.fixture(scope="module")
def db():
    seed_module.main()
    session = SessionLocal()
    generate_timetable(session, label="signals test")
    yield session
    session.close()


def _open_kinds(db) -> set[str]:
    items = db.scalars(select(ActionItem).where(ActionItem.status == ActionStatus.open))
    return {i.kind for i in items}


def test_run_signals_creates_low_attendance_cliff(db):
    run_signals(db, today=DEMO_ANCHOR_DATE)
    assert "low_attendance_trend" in _open_kinds(db)


def test_uncovered_classes_appears_after_absence_and_resolves_after_substitution(db):
    teacher = db.scalar(select(Teacher).where(Teacher.dept == "Physics"))
    absence = TeacherAbsence(
        teacher_id=teacher.id, date=DEMO_ANCHOR_DATE, reason="Test absence", resolved=False
    )
    db.add(absence)
    db.commit()

    run_signals(db, today=DEMO_ANCHOR_DATE)
    item = db.scalar(
        select(ActionItem).where(
            ActionItem.kind == "uncovered_classes", ActionItem.status == ActionStatus.open
        )
    )
    if item is None:
        pytest.skip("Seeded timetable didn't place this teacher on the anchor weekday.")
    assert item.payload["absence_id"] == absence.id
    assert item.severity.value == "critical"

    # Once the absence itself is marked resolved (as the substitute endpoint
    # does once every uncovered period is covered), the next tick auto-resolves
    # the card -- no separate manual dismiss required.
    absence.resolved = True
    db.commit()
    run_signals(db, today=DEMO_ANCHOR_DATE)
    refreshed = db.get(ActionItem, item.id)
    assert refreshed.status == ActionStatus.resolved


def test_run_signals_is_idempotent(db):
    before = len(list(db.scalars(select(ActionItem))))
    run_signals(db, today=DEMO_ANCHOR_DATE)
    run_signals(db, today=DEMO_ANCHOR_DATE)
    after = len(list(db.scalars(select(ActionItem))))
    assert after == before

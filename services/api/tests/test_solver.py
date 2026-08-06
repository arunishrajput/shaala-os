"""The 5 assertions PROMPT.md §6.2 calls out as the tests that matter, plus the
Phase 2 gate's timing requirement (§9): solver output has zero hard-constraint
violations on the seed data, every (class, subject) hits its exact weekly
quota, no teacher exceeds daily/weekly caps, a forced-infeasible input returns
a structured "infeasible + why" response rather than crashing, and
substitution never introduces a new conflict.
"""

import time
from collections import defaultdict

import pytest
from sqlalchemy import select

from app.db import seed as seed_module
from app.db.models import (
    Assignment,
    Room,
    RoomType,
    Subject,
    Teacher,
    TimeSlot,
    TimetableEntry,
)
from app.db.session import SessionLocal
from app.services.timetable.solver import generate_timetable
from app.services.timetable.substitute import apply_substitution, find_substitutes


@pytest.fixture(scope="module")
def db():
    seed_module.main()  # fixed-seed, deterministic (see seed.py)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def generated(db):
    start = time.perf_counter()
    result = generate_timetable(db, label="pytest run")
    elapsed = time.perf_counter() - start
    assert result["feasible"], f"expected the seed data to be solvable: {result}"
    return result, elapsed


def _entries(db, version_id: int) -> list[TimetableEntry]:
    return list(db.scalars(select(TimetableEntry).where(TimetableEntry.version_id == version_id)))


def _assert_no_double_booking(entries: list[TimetableEntry]) -> None:
    teacher_slots: set[tuple[int, int]] = set()
    room_slots: set[tuple[int, int]] = set()
    class_slots: set[tuple[int, int]] = set()
    for e in entries:
        t_key = (e.teacher_id, e.slot_id)
        r_key = (e.room_id, e.slot_id)
        c_key = (e.class_id, e.slot_id)
        msg = f"teacher {e.teacher_id} double-booked at slot {e.slot_id}"
        assert t_key not in teacher_slots, msg
        assert r_key not in room_slots, f"room {e.room_id} double-booked at slot {e.slot_id}"
        assert c_key not in class_slots, f"class {e.class_id} double-booked at slot {e.slot_id}"
        teacher_slots.add(t_key)
        room_slots.add(r_key)
        class_slots.add(c_key)


def test_generates_within_time_budget(generated):
    _, elapsed = generated
    assert elapsed < 10.0, f"generate_timetable took {elapsed}s, gate requires < 10s"


def test_zero_hard_constraint_violations(db, generated):
    result, _ = generated
    entries = _entries(db, result["version_id"])
    _assert_no_double_booking(entries)

    subjects = {s.id: s for s in db.scalars(select(Subject))}
    rooms = {r.id: r for r in db.scalars(select(Room))}
    slots = {s.id: s for s in db.scalars(select(TimeSlot))}

    for e in entries:
        if subjects[e.subject_id].needs_lab:
            assert rooms[e.room_id].type == RoomType.lab, (
                f"entry {e.id}: {subjects[e.subject_id].name} needs a lab, got "
                f"{rooms[e.room_id].type}"
            )
        assert not slots[e.slot_id].is_break, f"entry {e.id} scheduled in a break slot"


def test_exact_weekly_quota_per_assignment(db, generated):
    result, _ = generated
    entries = _entries(db, result["version_id"])
    subjects = {s.id: s for s in db.scalars(select(Subject))}

    counts: dict[tuple[int, int, int], int] = defaultdict(int)
    for e in entries:
        counts[(e.class_id, e.subject_id, e.teacher_id)] += 1

    for a in db.scalars(select(Assignment)):
        expected = subjects[a.subject_id].weekly_periods
        actual = counts.get((a.class_id, a.subject_id, a.teacher_id), 0)
        assert actual == expected, f"assignment {a.id} got {actual} periods, wanted {expected}"


def test_no_teacher_exceeds_caps(db, generated):
    result, _ = generated
    entries = _entries(db, result["version_id"])
    teachers = {t.id: t for t in db.scalars(select(Teacher))}
    slots = {s.id: s for s in db.scalars(select(TimeSlot))}

    weekly: dict[int, int] = defaultdict(int)
    daily: dict[tuple[int, int], int] = defaultdict(int)
    for e in entries:
        weekly[e.teacher_id] += 1
        daily[(e.teacher_id, slots[e.slot_id].day)] += 1

    for teacher_id, count in weekly.items():
        assert count <= teachers[teacher_id].max_periods_per_week, (
            f"{teachers[teacher_id].name}: {count} > weekly cap "
            f"{teachers[teacher_id].max_periods_per_week}"
        )
    for (teacher_id, _day), count in daily.items():
        assert count <= teachers[teacher_id].max_periods_per_day, (
            f"{teachers[teacher_id].name}: {count} > daily cap "
            f"{teachers[teacher_id].max_periods_per_day}"
        )


def test_forced_infeasible_returns_structured_response(db, generated):
    overloaded = db.scalar(select(Teacher).where(Teacher.max_periods_per_week > 10))
    original_cap = overloaded.max_periods_per_week
    overloaded.max_periods_per_week = 1
    db.commit()
    try:
        result = generate_timetable(db, label="forced infeasible")
        assert result["feasible"] is False
        assert result["status"] == "INFEASIBLE"
        assert result["reasons"], "expected a non-empty 'why' explanation"
        assert any(overloaded.name in r for r in result["reasons"])
    finally:
        overloaded.max_periods_per_week = original_cap
        db.commit()


def test_substitution_never_introduces_new_conflict(db, generated):
    result, _ = generated
    rao = db.scalar(select(Teacher).where(Teacher.name == "Kavita Rao"))
    subs = find_substitutes(db, rao.id)
    assert subs["uncovered_periods"], "expected Kavita Rao to have scheduled periods"

    period = subs["uncovered_periods"][0]
    assert period["candidates"], "expected at least one substitute candidate"
    chosen = period["candidates"][0]

    new_version = apply_substitution(
        db, period["entry_id"], chosen["teacher_id"], label="pytest substitution"
    )
    entries = _entries(db, new_version.id)
    assert len(entries) == len(_entries(db, result["version_id"])), (
        "substitution should not add or drop entries, only reassign one teacher"
    )

    _assert_no_double_booking(entries)

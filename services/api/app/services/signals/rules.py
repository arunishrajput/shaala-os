"""The six signal rules (PROMPT.md §6.3's example card stack). Each is a pure
function of DB state -> list[Detection]; `registry.run_signals` handles
create/refresh/auto-resolve. Import this module once (see main.py) so the
`@signal` decorators register before the first `run_signals` call.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AttendanceRecord,
    AttendanceStatus,
    Document,
    DocumentStatus,
    Student,
    TeacherAbsence,
    TimetableEntry,
)
from app.services.signals.registry import Detection, signal
from app.services.staffing.forecast import forecast as staffing_forecast
from app.services.timetable.explain import active_version, slot_label
from app.services.timetable.solver import load_solve_input

ATTENDANCE_CLIFF = 0.75
MIN_RECORDS_FOR_CLIFF = 3
FREE_PERIODS_THRESHOLD = 3
SHORTFALL_THRESHOLD = 1.5


@signal(kind="uncovered_classes", severity="critical")
def detect_uncovered_classes(db: Session, today: date) -> list[Detection]:
    version = active_version(db)
    if version is None:
        return []
    absences = list(
        db.scalars(
            select(TeacherAbsence).where(
                TeacherAbsence.date == today, TeacherAbsence.resolved.is_(False)
            )
        )
    )
    if not absences:
        return []

    si = load_solve_input(db)
    weekday = today.weekday()
    detections = []
    for absence in absences:
        teacher = si.teachers_by_id.get(absence.teacher_id)
        if teacher is None:
            continue
        entries = list(
            db.scalars(
                select(TimetableEntry).where(
                    TimetableEntry.version_id == version.id,
                    TimetableEntry.teacher_id == absence.teacher_id,
                )
            )
        )
        today_entries = [e for e in entries if si.slots_by_id[e.slot_id].day == weekday]
        if not today_entries:
            continue
        classes = sorted(
            {
                f"{si.sections_by_id[e.class_id].grade}-{si.sections_by_id[e.class_id].section}"
                for e in today_entries
            }
        )
        n = len(today_entries)
        detections.append(
            Detection(
                key=f"absence:{absence.id}",
                title=f"{n} class{'es' if n != 1 else ''} uncovered today — {teacher.name} absent",
                body=f"{teacher.name} is absent and teaches {', '.join(classes)} today.",
                payload={
                    "absence_id": absence.id,
                    "teacher_id": absence.teacher_id,
                    "entry_ids": [e.id for e in today_entries],
                },
                primary_action="Assign substitutes",
            )
        )
    return detections


@signal(kind="low_attendance_trend", severity="critical")
def detect_low_attendance_cliff(db: Session, today: date) -> list[Detection]:
    window_start = today - timedelta(days=6)
    stmt = select(AttendanceRecord.student_id, AttendanceRecord.status).where(
        AttendanceRecord.date >= window_start, AttendanceRecord.date <= today
    )
    totals: dict[int, int] = {}
    presents: dict[int, int] = {}
    for student_id, status in db.execute(stmt):
        totals[student_id] = totals.get(student_id, 0) + 1
        if status != AttendanceStatus.absent:
            presents[student_id] = presents.get(student_id, 0) + 1

    at_risk = [
        sid
        for sid, total in totals.items()
        if total >= MIN_RECORDS_FOR_CLIFF and (presents.get(sid, 0) / total) < ATTENDANCE_CLIFF
    ]
    if not at_risk:
        return []

    students = {s.id: s for s in db.scalars(select(Student).where(Student.id.in_(at_risk)))}
    names = [students[sid].name for sid in at_risk if sid in students]
    n = len(at_risk)
    shown = ", ".join(names[:4]) + ("…" if len(names) > 4 else "")
    return [
        Detection(
            key="cliff",
            title=f"{n} student{'s' if n != 1 else ''} drop below 75% this week",
            body=f"{shown} fell under 75% attendance in the last 7 days.",
            payload={"student_ids": at_risk},
            primary_action="Draft parent messages",
        )
    ]


@signal(kind="documents_need_review", severity="warning")
def detect_documents_need_review(db: Session, today: date) -> list[Detection]:
    docs = list(db.scalars(select(Document).where(Document.status == DocumentStatus.needs_review)))
    if not docs:
        return []
    n = len(docs)
    return [
        Detection(
            key="pending",
            title=f"{n} scanned form{'s' if n != 1 else ''} need review",
            body=(
                f"{n} uploaded document{'s' if n != 1 else ''} have low-confidence "
                "fields awaiting review."
            ),
            payload={"document_ids": [d.id for d in docs]},
            primary_action="Review now",
        )
    ]


@signal(kind="staffing_shortfall", severity="warning")
def detect_staffing_shortfall(db: Session, today: date) -> list[Detection]:
    result = staffing_forecast(db, days=7, as_of=today)
    detections = []
    for dept in result["departments"]:
        peak = max(dept["days"], key=lambda d: d["expected_absences"], default=None)
        if peak is None or peak["expected_absences"] < SHORTFALL_THRESHOLD:
            continue
        day_label = date.fromisoformat(peak["date"]).strftime("%A")
        count = round(peak["expected_absences"])
        detections.append(
            Detection(
                key=f"{dept['department']}:{peak['date']}",
                title=(
                    f"{dept['department']} will be {count} "
                    f"teacher{'s' if count != 1 else ''} short on {day_label}"
                ),
                body=dept["recommendation"]
                or f"Forecast shows elevated absence risk in {dept['department']} on {day_label}.",
                payload={"department": dept["department"], "date": peak["date"]},
                primary_action="View forecast",
            )
        )
    return detections


@signal(kind="room_conflict", severity="info")
def detect_room_conflicts(db: Session, today: date) -> list[Detection]:
    version = active_version(db)
    if version is None:
        return []
    si = load_solve_input(db)
    entries = list(
        db.scalars(select(TimetableEntry).where(TimetableEntry.version_id == version.id))
    )

    by_room_slot: dict[tuple[int, int], list[TimetableEntry]] = {}
    for e in entries:
        by_room_slot.setdefault((e.room_id, e.slot_id), []).append(e)

    detections = []
    for (room_id, slot_id), group in by_room_slot.items():
        if len(group) < 2:
            continue
        room = si.rooms_by_id[room_id]
        slot = si.slots_by_id[slot_id]
        classes = sorted(
            f"{si.sections_by_id[e.class_id].grade}-{si.sections_by_id[e.class_id].section}"
            for e in group
        )
        detections.append(
            Detection(
                key=f"{room_id}:{slot_id}",
                title=f"{room.name} double-booked {slot_label(slot)}",
                body=(
                    f"{' and '.join(classes)} are both scheduled in "
                    f"{room.name} at {slot_label(slot)}."
                ),
                payload={
                    "room_id": room_id,
                    "slot_id": slot_id,
                    "class_ids": [e.class_id for e in group],
                },
                primary_action="Resolve",
            )
        )
    return detections


@signal(kind="free_periods", severity="info")
def detect_free_periods(db: Session, today: date) -> list[Detection]:
    """Flags a class with *more* free periods than its peers, not just "some
    free periods" -- every class here structurally has the same baseline
    slack (subject weekly_periods sum to fewer than the week's non-break
    slots, by design, for every section equally), so an absolute threshold
    fired identically for all 12 classes every time and turned this into
    dashboard noise instead of a signal. Only a class sitting above the
    baseline everyone shares is actually worth a principal's attention.
    """
    version = active_version(db)
    if version is None:
        return []
    si = load_solve_input(db)
    entries = list(
        db.scalars(select(TimetableEntry).where(TimetableEntry.version_id == version.id))
    )

    booked: dict[int, set[int]] = {}
    for e in entries:
        booked.setdefault(e.class_id, set()).add(e.slot_id)
    non_break_slot_ids = {s.id for s in si.slots if not s.is_break}

    free_counts = {
        section.id: len(non_break_slot_ids - booked.get(section.id, set()))
        for section in si.sections
    }
    if not free_counts:
        return []
    baseline = min(free_counts.values())

    detections = []
    for section in si.sections:
        free_count = free_counts[section.id]
        excess = free_count - baseline
        if excess >= FREE_PERIODS_THRESHOLD:
            label = f"{section.grade}-{section.section}"
            detections.append(
                Detection(
                    key=f"class:{section.id}",
                    title=f"{label} has {free_count} free periods this week",
                    body=(
                        f"{label}'s active timetable leaves {free_count} periods "
                        f"unscheduled this week -- {excess} more than other classes."
                    ),
                    payload={"class_id": section.id, "free_count": free_count},
                    primary_action="View timetable",
                )
            )
    return detections

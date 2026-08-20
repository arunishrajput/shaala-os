from datetime import date as date_

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEMO_ANCHOR_DATE
from app.db.models import RoomType, Teacher, TeacherAbsence, TimeSlot, TimetableEntry
from app.db.session import get_db
from app.limiter import limiter
from app.security import get_current_user
from app.services.notifications import draft_substitute_notice
from app.services.signals.registry import run_signals
from app.services.timetable.explain import (
    active_version,
    clear_cache,
    explain_entry,
    find_alternatives,
    slot_label,
)
from app.services.timetable.solver import SolveInput, generate_timetable, load_solve_input
from app.services.timetable.substitute import apply_substitution, find_substitutes
from app.ws.manager import manager

router = APIRouter(
    prefix="/timetable", tags=["timetable"], dependencies=[Depends(get_current_user)]
)


class GenerateRequest(BaseModel):
    weights: dict[str, float] | None = None
    label: str = "Generated timetable"


class MoveRequest(BaseModel):
    entry_id: int
    room_id: int
    slot_id: int


@router.post("/generate")
@limiter.limit("2/minute")  # CP-SAT solver runs up to 8 s; limit concurrent calls
def generate(request: Request, payload: GenerateRequest, db: Session = Depends(get_db)) -> dict:
    return generate_timetable(db, weights=payload.weights, label=payload.label)


@router.get("/slots")
def list_slots(db: Session = Depends(get_db)) -> list[dict]:
    """Every non-break slot (id, day, period, label) — the grid UI needs this to
    know which slot_id a given (day, period) cell maps to even when it's empty."""
    stmt = (
        select(TimeSlot)
        .where(TimeSlot.is_break.is_(False))
        .order_by(TimeSlot.day, TimeSlot.period)
    )
    slots = list(db.scalars(stmt))
    return [
        {"id": s.id, "day": s.day, "period": s.period, "label": slot_label(s)}
        for s in slots
    ]


def _entry_out(entry: TimetableEntry, si: SolveInput) -> dict:
    section = si.sections_by_id[entry.class_id]
    subject = si.subjects_by_id[entry.subject_id]
    teacher = si.teachers_by_id[entry.teacher_id]
    room = si.rooms_by_id[entry.room_id]
    slot = si.slots_by_id[entry.slot_id]
    return {
        "id": entry.id,
        "class_id": entry.class_id,
        "class_label": f"{section.grade}-{section.section}",
        "subject_id": entry.subject_id,
        "subject_name": subject.name,
        "teacher_id": entry.teacher_id,
        "teacher_name": teacher.name,
        "room_id": entry.room_id,
        "room_name": room.name,
        "slot_id": entry.slot_id,
        "day": slot.day,
        "period": slot.period,
        "slot_label": slot_label(slot),
        "is_substitution": entry.is_substitution,
    }


@router.get("/active")
def get_active(
    class_id: int | None = None,
    teacher_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    version = active_version(db)
    if version is None:
        return {"version_id": None, "entries": []}

    si = load_solve_input(db)
    stmt = select(TimetableEntry).where(TimetableEntry.version_id == version.id)
    if class_id is not None:
        stmt = stmt.where(TimetableEntry.class_id == class_id)
    if teacher_id is not None:
        stmt = stmt.where(TimetableEntry.teacher_id == teacher_id)
    entries = list(db.scalars(stmt))

    return {
        "version_id": version.id,
        "label": version.label,
        "solver_stats": version.solver_stats,
        "entries": [_entry_out(e, si) for e in entries],
    }


@router.get("/explain/{entry_id}")
def explain(entry_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return explain_entry(db, entry_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


def _conflicts_for_move(
    db: Session, si: SolveInput, entry: TimetableEntry, room_id: int, slot_id: int
) -> list[str]:
    entries = [
        e
        for e in db.scalars(
            select(TimetableEntry).where(TimetableEntry.version_id == entry.version_id)
        )
        if e.id != entry.id
    ]
    subject = si.subjects_by_id[entry.subject_id]
    teacher = si.teachers_by_id[entry.teacher_id]
    section = si.sections_by_id[entry.class_id]
    room = si.rooms_by_id.get(room_id)
    slot = si.slots_by_id.get(slot_id)

    if room is None:
        return ["No such room."]
    if slot is None:
        return ["No such time slot."]

    conflicts: list[str] = []
    if slot.is_break:
        conflicts.append("That slot is a break — nothing can be scheduled there.")
    if subject.needs_lab and room.type != RoomType.lab:
        conflicts.append(f"{subject.name} needs a lab room — {room.name} is a {room.type.value}.")
    if room.capacity < section.strength:
        conflicts.append(
            f"{room.name} seats {room.capacity}; "
            f"{section.grade}-{section.section} has {section.strength}."
        )
    if slot_id in (teacher.unavailable_slots or []):
        conflicts.append(f"{teacher.name} is unavailable at {slot_label(slot)}.")
    if any(e.teacher_id == entry.teacher_id and e.slot_id == slot_id for e in entries):
        conflicts.append(f"{teacher.name} is already teaching at {slot_label(slot)}.")
    if any(e.room_id == room_id and e.slot_id == slot_id for e in entries):
        conflicts.append(f"{room.name} is already booked at {slot_label(slot)}.")
    if any(e.class_id == entry.class_id and e.slot_id == slot_id for e in entries):
        conflicts.append(
            f"{section.grade}-{section.section} already has a class at {slot_label(slot)}."
        )

    same_day_count = sum(
        1
        for e in entries
        if e.teacher_id == entry.teacher_id and si.slots_by_id[e.slot_id].day == slot.day
    )
    if same_day_count >= teacher.max_periods_per_day:
        conflicts.append(
            f"{teacher.name} would exceed their daily cap of {teacher.max_periods_per_day}."
        )

    return conflicts


@router.post("/validate-move")
def validate_move(payload: MoveRequest, db: Session = Depends(get_db)) -> dict:
    entry = db.get(TimetableEntry, payload.entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No such timetable entry.")
    si = load_solve_input(db)
    conflicts = _conflicts_for_move(db, si, entry, payload.room_id, payload.slot_id)
    alternatives = []
    if conflicts:
        alternatives = [
            {
                "room": alt.room_name,
                "slot": alt.slot_label,
                "cost_delta": alt.cost_delta,
                "reasons": alt.reasons,
            }
            for alt in find_alternatives(db, si, entry, limit=3)
        ]
    return {"ok": not conflicts, "conflicts": conflicts, "alternatives": alternatives}


@router.post("/move")
def move(payload: MoveRequest, db: Session = Depends(get_db)) -> dict:
    entry = db.get(TimetableEntry, payload.entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="No such timetable entry.")
    si = load_solve_input(db)
    conflicts = _conflicts_for_move(db, si, entry, payload.room_id, payload.slot_id)
    if conflicts:
        raise HTTPException(status_code=409, detail={"conflicts": conflicts})

    entry.room_id = payload.room_id
    entry.slot_id = payload.slot_id
    db.commit()

    # A move can change other cells' idle-gap/balance context too — safest to
    # drop the whole explain cache rather than track exactly which entries it
    # could have staled.
    clear_cache()

    return _entry_out(entry, load_solve_input(db))


class AbsenceRequest(BaseModel):
    teacher_id: int
    date: date_ | None = None
    reason: str = "Marked absent"


class SubstituteRequest(BaseModel):
    absence_id: int
    # Identified by (class_id, slot_id), not entry_id: each substitution clones
    # the whole active version, so entry_ids from an uncovered_periods listing
    # fetched before an earlier substitution in the same batch are already
    # stale by the time a later one in the same batch is applied. class_id +
    # slot_id name the same grid cell across every version.
    class_id: int
    slot_id: int
    teacher_id: int


def _uncovered_remaining(db: Session, absence: TeacherAbsence) -> int:
    version = active_version(db)
    if version is None:
        return 0
    si = load_solve_input(db)
    weekday = absence.date.weekday()
    stmt = select(TimetableEntry).where(
        TimetableEntry.version_id == version.id,
        TimetableEntry.teacher_id == absence.teacher_id,
    )
    return sum(1 for e in db.scalars(stmt) if si.slots_by_id[e.slot_id].day == weekday)


@router.post("/absence")
async def mark_absence(payload: AbsenceRequest, db: Session = Depends(get_db)) -> dict:
    """The "mark Mrs. Rao absent" moment (PROMPT.md §1, §6.2 point 3). Idempotent
    per (teacher, date): calling it again for the same still-open absence just
    returns the current uncovered periods, so a client can safely re-poll.
    """
    teacher = db.get(Teacher, payload.teacher_id)
    if teacher is None:
        raise HTTPException(status_code=404, detail="No such teacher.")
    absence_date = payload.date or DEMO_ANCHOR_DATE

    absence = db.scalar(
        select(TeacherAbsence).where(
            TeacherAbsence.teacher_id == payload.teacher_id,
            TeacherAbsence.date == absence_date,
            TeacherAbsence.resolved.is_(False),
        )
    )
    if absence is None:
        absence = TeacherAbsence(
            teacher_id=payload.teacher_id,
            date=absence_date,
            reason=payload.reason,
            resolved=False,
        )
        db.add(absence)
        db.commit()

    result = find_substitutes(db, payload.teacher_id, weekday=absence_date.weekday())
    run_signals(db)
    await manager.broadcast("actions.updated", {})
    return {
        "absence_id": absence.id,
        "teacher_id": payload.teacher_id,
        "teacher_name": result.get("teacher_name", teacher.name),
        "date": absence_date.isoformat(),
        "uncovered_periods": result["uncovered_periods"],
    }


@router.post("/substitute")
async def substitute(payload: SubstituteRequest, db: Session = Depends(get_db)) -> dict:
    absence = db.get(TeacherAbsence, payload.absence_id)
    if absence is None:
        raise HTTPException(status_code=404, detail="No such absence.")

    version = active_version(db)
    if version is None:
        raise HTTPException(status_code=404, detail="No active timetable.")
    original_entry = db.scalar(
        select(TimetableEntry).where(
            TimetableEntry.version_id == version.id,
            TimetableEntry.class_id == payload.class_id,
            TimetableEntry.slot_id == payload.slot_id,
        )
    )
    if original_entry is None:
        raise HTTPException(
            status_code=404, detail="No timetable entry at that class/slot in the active version."
        )
    class_id, slot_id = payload.class_id, payload.slot_id

    try:
        new_version = apply_substitution(
            db, original_entry.id, payload.teacher_id, label=f"Substitute — {absence.reason}"
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    clear_cache()

    remaining = _uncovered_remaining(db, absence)
    if remaining == 0:
        absence.resolved = True
        db.commit()

    si = load_solve_input(db)
    new_entry = db.scalar(
        select(TimetableEntry).where(
            TimetableEntry.version_id == new_version.id,
            TimetableEntry.class_id == class_id,
            TimetableEntry.slot_id == slot_id,
        )
    )
    if new_entry is None:
        raise HTTPException(
            status_code=500, detail="Substitution applied but the new entry could not be found."
        )
    entry_out = _entry_out(new_entry, si)

    absent_teacher = si.teachers_by_id.get(absence.teacher_id)
    new_teacher = si.teachers_by_id[payload.teacher_id]
    draft_substitute_notice(
        db,
        teacher_name=new_teacher.name,
        teacher_phone=new_teacher.phone,
        class_label=entry_out["class_label"],
        subject_name=entry_out["subject_name"],
        slot_label=entry_out["slot_label"],
        absent_teacher_name=absent_teacher.name if absent_teacher else "the absent teacher",
    )
    db.commit()

    run_signals(db)
    await manager.broadcast("timetable.substituted", entry_out)
    await manager.broadcast("actions.updated", {})
    await manager.broadcast("notifications.updated", {})
    return {
        "absence_id": absence.id,
        "absence_resolved": absence.resolved,
        "uncovered_remaining": remaining,
        "entry": entry_out,
    }

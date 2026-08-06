from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RoomType, TimeSlot, TimetableEntry
from app.db.session import get_db
from app.services.timetable.explain import (
    active_version,
    clear_cache,
    explain_entry,
    find_alternatives,
    slot_label,
)
from app.services.timetable.solver import SolveInput, generate_timetable, load_solve_input

router = APIRouter(prefix="/timetable", tags=["timetable"])


class GenerateRequest(BaseModel):
    weights: dict[str, float] | None = None
    label: str = "Generated timetable"


class MoveRequest(BaseModel):
    entry_id: int
    room_id: int
    slot_id: int


@router.post("/generate")
def generate(payload: GenerateRequest, db: Session = Depends(get_db)) -> dict:
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

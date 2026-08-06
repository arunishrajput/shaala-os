"""Explain-any-cell (PROMPT.md §6.2 point 1): rules-based reason strings plus a
real re-solve with that exact placement forbidden, diffing the objective.
Cached per entry, since the re-solve is the expensive part.

The ranked-alternatives finder in here is deliberately shared with
`validate_move` (§6.2 point 2) — both need "which other (room, slot) could this
class/subject/teacher use right now, and what would it cost" and there's no
reason to compute that twice.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TimeSlot, TimetableEntry, TimetableVersion
from app.services.timetable.solver import (
    DEFAULT_WEIGHTS,
    SolveInput,
    candidate_rooms,
    candidate_slots,
    load_solve_input,
)

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

_explain_cache: dict[int, dict] = {}


def slot_label(slot: TimeSlot) -> str:
    return f"{DAY_NAMES[slot.day]} P{slot.period}"


def active_version(db: Session) -> TimetableVersion | None:
    return db.scalar(select(TimetableVersion).where(TimetableVersion.is_active))


def _entries_for_version(db: Session, version_id: int) -> list[TimetableEntry]:
    return list(db.scalars(select(TimetableEntry).where(TimetableEntry.version_id == version_id)))


@dataclass
class Alternative:
    room_id: int
    room_name: str
    slot_id: int
    slot_label: str
    cost_delta: float
    reasons: list[str]


def _teacher_day_counts(
    entries: list[TimetableEntry], slots_by_id: dict[int, TimeSlot], teacher_id: int
) -> dict[int, list[int]]:
    by_day: dict[int, list[int]] = {}
    for e in entries:
        if e.teacher_id != teacher_id:
            continue
        slot = slots_by_id[e.slot_id]
        by_day.setdefault(slot.day, []).append(slot.period)
    for periods in by_day.values():
        periods.sort()
    return by_day


def _idle_for_day(periods: list[int], day_periods: list[int]) -> int:
    if not periods:
        return 0
    idx = [day_periods.index(p) for p in periods]
    return (max(idx) - min(idx) + 1) - len(idx)


def _class_subject_day_count(
    entries: list[TimetableEntry],
    slots_by_id: dict[int, TimeSlot],
    class_id: int,
    subject_id: int,
    day: int,
) -> int:
    return sum(
        1
        for e in entries
        if e.class_id == class_id
        and e.subject_id == subject_id
        and slots_by_id[e.slot_id].day == day
    )


def estimate_move_cost(
    si: SolveInput,
    entries: list[TimetableEntry],
    entry: TimetableEntry,
    new_room_id: int,
    new_slot_id: int,
    weights: dict[str, float],
) -> tuple[float, list[str]]:
    """Fast, deterministic estimate of the soft-objective delta if `entry` moved
    to (new_room_id, new_slot_id), holding every other entry fixed. This is an
    approximation of solver.py's real objective for interactive use (explain
    panel, drag-and-drop) — see generate_timetable's full re-solve for the
    authoritative number.
    """
    subject = si.subjects_by_id[entry.subject_id]
    teacher = si.teachers_by_id[entry.teacher_id]
    old_slot = si.slots_by_id[entry.slot_id]
    new_slot = si.slots_by_id[new_slot_id]

    reasons: list[str] = []
    delta = 0.0

    if si.is_heavy(subject):
        old_late, new_late = old_slot.period > 4, new_slot.period > 4
        if new_late and not old_late:
            delta += weights["heavy_early"]
            reasons.append(f"{subject.name} is heavy — periods 6-8 cost +{weights['heavy_early']}")
        elif old_late and not new_late:
            delta -= weights["heavy_early"]
            heavy_w = weights["heavy_early"]
            reasons.append(f"{subject.name} moves back into periods 1-4 (-{heavy_w})")

    preferred = set(teacher.preferred_slots or [])
    if preferred:
        old_pref, new_pref = old_slot.id in preferred, new_slot.id in preferred
        if old_pref and not new_pref:
            delta += weights["preferred_slots"]
            pref_w = weights["preferred_slots"]
            reasons.append(f"moves {teacher.name} off a preferred slot (+{pref_w})")
        elif new_pref and not old_pref:
            delta -= weights["preferred_slots"]

    day_counts = _teacher_day_counts(entries, si.slots_by_id, teacher.id)
    all_day_periods = {
        d: sorted(s.period for s in day_slots) for d, day_slots in si.slots_by_day.items()
    }

    def total_idle(counts: dict[int, list[int]]) -> int:
        return sum(_idle_for_day(p, all_day_periods[d]) for d, p in counts.items())

    def spread(counts: dict[int, list[int]]) -> int:
        lens = [len(p) for p in counts.values()]
        return (max(lens) - min(lens)) if lens else 0

    before_idle, before_spread = total_idle(day_counts), spread(day_counts)

    sim = {d: list(p) for d, p in day_counts.items()}
    sim.setdefault(old_slot.day, [])
    if old_slot.period in sim[old_slot.day]:
        sim[old_slot.day].remove(old_slot.period)
    sim.setdefault(new_slot.day, [])
    sim[new_slot.day].append(new_slot.period)

    after_idle, after_spread = total_idle(sim), spread(sim)
    idle_delta = (after_idle - before_idle) * weights["idle_gaps"]
    balance_delta = (after_spread - before_spread) * weights["balance"]
    delta += idle_delta + balance_delta
    if idle_delta > 0:
        reasons.append(
            f"opens a {after_idle - before_idle}-period gap for {teacher.name} (+{int(idle_delta)})"
        )
    elif idle_delta < 0:
        reasons.append(
            f"closes a {before_idle - after_idle}-period gap for {teacher.name} "
            f"({int(idle_delta)})"
        )
    if balance_delta > 0:
        reasons.append(f"unbalances {teacher.name}'s week (+{int(balance_delta)})")
    elif balance_delta < 0:
        reasons.append(f"balances {teacher.name}'s week ({int(balance_delta)})")

    allowed = 2 if subject.is_double_period else 1
    new_day_count = _class_subject_day_count(
        entries, si.slots_by_id, entry.class_id, entry.subject_id, new_slot.day
    )
    if old_slot.day != new_slot.day and new_day_count + 1 > allowed:
        delta += weights["spread"]
        reasons.append(
            f"{subject.name} would repeat same-day beyond the double-period "
            f"allowance (+{weights['spread']})"
        )

    if not reasons:
        reasons.append("no meaningful soft-constraint impact")

    return delta, reasons


def find_alternatives(
    db: Session,
    si: SolveInput,
    entry: TimetableEntry,
    limit: int = 3,
    weights: dict[str, float] | None = None,
) -> list[Alternative]:
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}
    version = active_version(db)
    if version is None:
        return []
    entries = [e for e in _entries_for_version(db, version.id) if e.id != entry.id]

    subject = si.subjects_by_id[entry.subject_id]
    teacher = si.teachers_by_id[entry.teacher_id]
    section = si.sections_by_id[entry.class_id]

    teacher_busy = {(e.teacher_id, e.slot_id) for e in entries}
    room_busy = {(e.room_id, e.slot_id) for e in entries}
    class_busy = {(e.class_id, e.slot_id) for e in entries}

    alternatives: list[Alternative] = []
    for room in candidate_rooms(si, subject, section):
        for slot in candidate_slots(si, teacher):
            if room.id == entry.room_id and slot.id == entry.slot_id:
                continue
            if (teacher.id, slot.id) in teacher_busy:
                continue
            if (room.id, slot.id) in room_busy:
                continue
            if (section.id, slot.id) in class_busy:
                continue
            cost, reasons = estimate_move_cost(si, entries, entry, room.id, slot.id, weights)
            alternatives.append(
                Alternative(
                    room_id=room.id,
                    room_name=room.name,
                    slot_id=slot.id,
                    slot_label=slot_label(slot),
                    cost_delta=cost,
                    reasons=reasons,
                )
            )

    alternatives.sort(key=lambda alt: alt.cost_delta)
    return alternatives[:limit]


def _room_reason(si: SolveInput, entries: list[TimetableEntry], entry: TimetableEntry) -> str:
    subject = si.subjects_by_id[entry.subject_id]
    room = si.rooms_by_id[entry.room_id]
    section = si.sections_by_id[entry.class_id]
    if not subject.needs_lab:
        return f"{room.name} is a classroom with capacity for {section.strength} students."
    labs = [r for r in si.rooms if r.type == room.type]
    lab_ids = {r.id for r in labs}
    busy_labs = {e.room_id for e in entries if e.slot_id == entry.slot_id and e.room_id in lab_ids}
    return (
        f"{subject.name} needs a lab; {len(busy_labs)} of {len(labs)} labs are busy at "
        f"{slot_label(si.slots_by_id[entry.slot_id])}."
    )


def _teacher_reason(si: SolveInput, entries: list[TimetableEntry], entry: TimetableEntry) -> str:
    subject = si.subjects_by_id[entry.subject_id]
    teacher = si.teachers_by_id[entry.teacher_id]
    section = si.sections_by_id[entry.class_id]
    slot = si.slots_by_id[entry.slot_id]
    dept_teachers = [t for t in si.teachers if t.dept == teacher.dept and t.id != teacher.id]
    busy_here = [
        (t, e)
        for t in dept_teachers
        for e in entries
        if e.teacher_id == t.id and e.slot_id == entry.slot_id
    ]
    if not busy_here:
        return (
            f"{teacher.name} teaches {subject.name} to {section.grade}-{section.section}; "
            f"the rest of {teacher.dept} was free at {slot_label(slot)}."
        )
    other_t, other_e = busy_here[0]
    other_class = si.sections_by_id[other_e.class_id]
    return (
        f"{teacher.name} teaches this — {other_t.name} was the alternative but already has "
        f"{other_class.grade}-{other_class.section} at {slot_label(slot)}."
    )


def explain_entry(db: Session, entry_id: int) -> dict:
    if entry_id in _explain_cache:
        return _explain_cache[entry_id]

    entry = db.get(TimetableEntry, entry_id)
    if entry is None:
        raise ValueError(f"No timetable entry with id={entry_id}")

    si = load_solve_input(db)
    version = active_version(db)
    entries = _entries_for_version(db, version.id) if version else []

    subject = si.subjects_by_id[entry.subject_id]
    teacher = si.teachers_by_id[entry.teacher_id]
    room = si.rooms_by_id[entry.room_id]
    section = si.sections_by_id[entry.class_id]

    reasons = [
        _room_reason(si, entries, entry),
        _teacher_reason(si, entries, entry),
    ]

    alternatives = find_alternatives(db, si, entry, limit=3)
    if alternatives:
        best = alternatives[0]
        sign = "+" if best.cost_delta >= 0 else ""
        reasons.append(
            f"Best alternative: {best.slot_label} in {best.room_name} "
            f"({sign}{int(best.cost_delta)} cost)."
        )

    # The literal spec ask: re-solve with this exact placement forbidden, diff
    # the objective against the current version's stats. Expensive — this is
    # exactly what the cache above protects.
    resolve_diff = _resolve_forbidding(db, si, entry, version)

    result = {
        "entry_id": entry_id,
        "title": f"Why {subject.name} / {teacher.name} / {room.name}?",
        "class": f"{section.grade}-{section.section}",
        "slot": slot_label(si.slots_by_id[entry.slot_id]),
        "reasons": reasons,
        "alternatives": [
            {
                "room": alt.room_name,
                "slot": alt.slot_label,
                "cost_delta": alt.cost_delta,
                "reasons": alt.reasons,
            }
            for alt in alternatives
        ],
        "resolve_diff": resolve_diff,
    }
    _explain_cache[entry_id] = result
    return result


def _resolve_forbidding(
    db: Session, si: SolveInput, entry: TimetableEntry, version: TimetableVersion | None
) -> dict:
    from app.services.timetable.solver import solve

    assignment = next(
        (
            a
            for a in si.assignments
            if a.class_id == entry.class_id and a.subject_id == entry.subject_id
        ),
        None,
    )
    if assignment is None:
        return {"available": False, "note": "No matching assignment found."}
    forbidden = {(assignment.id, entry.room_id, entry.slot_id)}

    result = solve(si, forbidden=forbidden, time_limit=6.0)
    if not result.feasible:
        return {
            "available": False,
            "note": "Forbidding this exact cell makes the timetable infeasible.",
        }

    baseline_objective = (version.solver_stats or {}).get("objective_value") if version else None
    new_objective = result.stats.get("objective_value")
    if baseline_objective is None or new_objective is None:
        return {"available": True, "objective_delta": None}
    return {"available": True, "objective_delta": round(new_objective - baseline_objective, 1)}


def clear_cache() -> None:
    _explain_cache.clear()

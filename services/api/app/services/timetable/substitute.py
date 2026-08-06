"""The substitute repair algorithm (PROMPT.md §6.2 point 3): minimal-perturbation
repair — freeze everything else, re-assign only the absent teacher's periods.

Scope note: this module is the core algorithm and is what Phase 2's gate tests
("substitution never introduces a new conflict"). Wiring it into
`POST /timetable/absence` / `POST /timetable/substitute`, the Action Center, and
notification drafts is PROMPT.md §9 Phase 4 ("substitute engine end to end") —
deliberately not built here.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import TimetableEntry, TimetableVersion
from app.services.timetable.explain import active_version, slot_label
from app.services.timetable.solver import SolveInput, load_solve_input


@dataclass
class SubstituteCandidate:
    teacher_id: int
    teacher_name: str
    teaches_subject: bool
    weekly_load: int
    has_taught_class: bool
    reasons: list[str]


@dataclass
class UncoveredPeriod:
    entry_id: int
    class_id: int
    slot_id: int
    class_label: str
    subject: str
    slot: str
    candidates: list[SubstituteCandidate]


def _rank_candidates(
    si: SolveInput, entries: list[TimetableEntry], absent_teacher_id: int, entry: TimetableEntry
) -> list[SubstituteCandidate]:
    subject = si.subjects_by_id[entry.subject_id]
    busy_teacher_ids = {
        e.teacher_id
        for e in entries
        if e.slot_id == entry.slot_id and e.teacher_id != absent_teacher_id
    }

    candidates: list[SubstituteCandidate] = []
    for teacher in si.teachers:
        if teacher.id == absent_teacher_id or teacher.id in busy_teacher_ids:
            continue  # not free at that exact slot — a hard requirement, not a preference

        teaches_subject = subject.name in (teacher.subjects or []) or teacher.dept == subject.name
        weekly_load = sum(1 for e in entries if e.teacher_id == teacher.id)
        has_taught_class = any(
            a.teacher_id == teacher.id and a.class_id == entry.class_id for a in si.assignments
        )

        reasons = [f"free at {slot_label(si.slots_by_id[entry.slot_id])}"]
        reasons.append(
            f"{'teaches' if teaches_subject else 'does not teach'} {subject.name}"
        )
        reasons.append(f"{weekly_load} periods/week currently")
        if has_taught_class:
            reasons.append(f"has already taught {si.sections_by_id[entry.class_id].grade}"
                            f"-{si.sections_by_id[entry.class_id].section}")

        candidates.append(
            SubstituteCandidate(
                teacher_id=teacher.id,
                teacher_name=teacher.name,
                teaches_subject=teaches_subject,
                weekly_load=weekly_load,
                has_taught_class=has_taught_class,
                reasons=reasons,
            )
        )

    # Ranking priority, per PROMPT.md §6.2: free (already filtered above) >
    # teaches the subject > lowest weekly load > has taught this class.
    candidates.sort(key=lambda c: (not c.teaches_subject, c.weekly_load, not c.has_taught_class))
    return candidates[:3]


def find_substitutes(
    db: Session, absent_teacher_id: int, weekday: int | None = None
) -> dict:
    """`weekday` (0=Mon..5=Sat, matching TimeSlot.day) restricts "uncovered" to
    periods on that one day -- what a single-day TeacherAbsence actually needs
    covered. None (the default) returns every period that teacher has all
    week, which is what the Phase 2 gate test exercises directly without an
    absence date in the picture.
    """
    si = load_solve_input(db)
    version = active_version(db)
    if version is None:
        return {"teacher_id": absent_teacher_id, "uncovered_periods": []}

    entries = list(
        db.scalars(select(TimetableEntry).where(TimetableEntry.version_id == version.id))
    )
    teacher = si.teachers_by_id.get(absent_teacher_id)
    if teacher is None:
        raise ValueError(f"No teacher with id={absent_teacher_id}")

    uncovered: list[UncoveredPeriod] = []
    for entry in entries:
        if entry.teacher_id != absent_teacher_id:
            continue
        if weekday is not None and si.slots_by_id[entry.slot_id].day != weekday:
            continue
        section = si.sections_by_id[entry.class_id]
        subject = si.subjects_by_id[entry.subject_id]
        uncovered.append(
            UncoveredPeriod(
                entry_id=entry.id,
                class_id=entry.class_id,
                slot_id=entry.slot_id,
                class_label=f"{section.grade}-{section.section}",
                subject=subject.name,
                slot=slot_label(si.slots_by_id[entry.slot_id]),
                candidates=_rank_candidates(si, entries, absent_teacher_id, entry),
            )
        )

    return {
        "teacher_id": absent_teacher_id,
        "teacher_name": teacher.name,
        "uncovered_periods": [
            {
                "entry_id": u.entry_id,
                "class_id": u.class_id,
                "slot_id": u.slot_id,
                "class": u.class_label,
                "subject": u.subject,
                "slot": u.slot,
                "candidates": [
                    {
                        "teacher_id": c.teacher_id,
                        "teacher_name": c.teacher_name,
                        "reasons": c.reasons,
                    }
                    for c in u.candidates
                ],
            }
            for u in uncovered
        ],
    }


def apply_substitution(
    db: Session, entry_id: int, new_teacher_id: int, label: str
) -> TimetableVersion:
    """Minimal-perturbation repair: clone the active version, replacing only the
    one entry's teacher. Every other entry is untouched — that's what "freeze
    everything else" means here.
    """
    version = active_version(db)
    if version is None:
        raise ValueError("No active timetable version to repair.")

    entries = list(
        db.scalars(select(TimetableEntry).where(TimetableEntry.version_id == version.id))
    )
    target = next((e for e in entries if e.id == entry_id), None)
    if target is None:
        raise ValueError(f"No timetable entry with id={entry_id} in the active version.")

    conflict = next(
        (e for e in entries if e.teacher_id == new_teacher_id and e.slot_id == target.slot_id),
        None,
    )
    if conflict is not None:
        raise ValueError(
            f"teacher_id={new_teacher_id} is already teaching at this slot — not free."
        )

    db.execute(update(TimetableVersion).values(is_active=False))
    new_version = TimetableVersion(
        label=label,
        solver_stats={**(version.solver_stats or {}), "substituted_entry_id": entry_id},
        is_active=True,
    )
    db.add(new_version)
    db.flush()

    new_entries = []
    for e in entries:
        if e.id == entry_id:
            new_entries.append(
                TimetableEntry(
                    version_id=new_version.id,
                    class_id=e.class_id,
                    subject_id=e.subject_id,
                    teacher_id=new_teacher_id,
                    room_id=e.room_id,
                    slot_id=e.slot_id,
                    is_substitution=True,
                    original_teacher_id=e.teacher_id,
                )
            )
        else:
            new_entries.append(
                TimetableEntry(
                    version_id=new_version.id,
                    class_id=e.class_id,
                    subject_id=e.subject_id,
                    teacher_id=e.teacher_id,
                    room_id=e.room_id,
                    slot_id=e.slot_id,
                    is_substitution=e.is_substitution,
                    original_teacher_id=e.original_teacher_id,
                )
            )
    db.bulk_save_objects(new_entries)
    db.commit()
    return new_version

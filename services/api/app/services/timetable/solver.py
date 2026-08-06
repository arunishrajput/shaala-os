"""CP-SAT timetable solver (PROMPT.md §6.2).

Decision variables are over (Assignment x Room x TimeSlot), not the full
(class, subject, teacher, room, slot) product: `Assignment` already fixes which
teacher teaches which subject to which class (the school's roster, set ahead of
time) — the solver's job is only to decide *when* (slot) and *where* (room) each
of those fixed (class, subject, teacher) triples happens. This is a deliberate,
documented simplification of PROMPT.md's `x[class, subject, teacher, room, slot]`
notation; see docs/solver.md.
"""

from __future__ import annotations

import os
import time as time_module
from dataclasses import dataclass, field

from ortools.sat.python import cp_model
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import (
    Assignment,
    ClassSection,
    Room,
    RoomType,
    Subject,
    Teacher,
    TimeSlot,
    TimetableEntry,
    TimetableVersion,
)

DEFAULT_WEIGHTS = {
    "idle_gaps": 5,
    "spread": 8,
    "heavy_early": 3,
    "preferred_slots": 2,
    "balance": 4,
}

# A subject is "heavy" (should land in periods 1-4) if it carries a lot of the
# week — a documented, simple proxy since PROMPT.md doesn't define the term.
HEAVY_WEEKLY_PERIODS_THRESHOLD = 5

# Kept under the Phase 2 gate's 10s budget with margin for DB I/O. CP-SAT
# reliably reaches a zero-hard-violation FEASIBLE solution well inside this —
# see docs/solver.md for the quality-vs-time tradeoff at this budget.
TIME_LIMIT_SECONDS = 8.0


@dataclass
class SolveInput:
    sections: list[ClassSection]
    subjects: list[Subject]
    rooms: list[Room]
    slots: list[TimeSlot]
    teachers: list[Teacher]
    assignments: list[Assignment]

    sections_by_id: dict[int, ClassSection] = field(default_factory=dict)
    subjects_by_id: dict[int, Subject] = field(default_factory=dict)
    rooms_by_id: dict[int, Room] = field(default_factory=dict)
    slots_by_id: dict[int, TimeSlot] = field(default_factory=dict)
    teachers_by_id: dict[int, Teacher] = field(default_factory=dict)

    slots_by_day: dict[int, list[TimeSlot]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.sections_by_id = {s.id: s for s in self.sections}
        self.subjects_by_id = {s.id: s for s in self.subjects}
        self.rooms_by_id = {r.id: r for r in self.rooms}
        self.slots_by_id = {s.id: s for s in self.slots}
        self.teachers_by_id = {t.id: t for t in self.teachers}

        by_day: dict[int, list[TimeSlot]] = {}
        for s in sorted(self.slots, key=lambda s: (s.day, s.period)):
            by_day.setdefault(s.day, []).append(s)
        self.slots_by_day = by_day

    def is_heavy(self, subject: Subject) -> bool:
        return subject.weekly_periods >= HEAVY_WEEKLY_PERIODS_THRESHOLD


def load_solve_input(db: Session) -> SolveInput:
    sections = list(db.scalars(select(ClassSection)))
    subjects = list(db.scalars(select(Subject)))
    rooms = list(db.scalars(select(Room)))
    slots = list(db.scalars(select(TimeSlot).where(TimeSlot.is_break.is_(False))))
    teachers = list(db.scalars(select(Teacher)))
    assignments = list(db.scalars(select(Assignment)))
    return SolveInput(
        sections=sections,
        subjects=subjects,
        rooms=rooms,
        slots=slots,
        teachers=teachers,
        assignments=assignments,
    )


def candidate_rooms(si: SolveInput, subject: Subject, section: ClassSection) -> list[Room]:
    wanted_type = RoomType.lab if subject.needs_lab else RoomType.classroom
    return [r for r in si.rooms if r.type == wanted_type and r.capacity >= section.strength]


def candidate_slots(si: SolveInput, teacher: Teacher) -> list[TimeSlot]:
    unavailable = set(teacher.unavailable_slots or [])
    return [s for s in si.slots if s.id not in unavailable]


@dataclass
class ModelBuild:
    model: cp_model.CpModel
    x: dict[tuple[int, int, int], cp_model.IntVar]  # (assignment_id, room_id, slot_id) -> var
    vars_by_assignment: dict[int, list[cp_model.IntVar]]
    penalty_terms: list[cp_model.LinearExprT]
    penalty_breakdown: dict[str, list[cp_model.IntVar]]


def build_model(
    si: SolveInput,
    weights: dict[str, float],
    forbidden: set[tuple[int, int, int]] | None = None,
) -> ModelBuild:
    """Builds the CP-SAT model. `forbidden` fixes specific (assignment, room,
    slot) variables to 0 — this is what powers explain.py's "re-solve with this
    cell forbidden, diff the objective" feature without duplicating the model.
    """
    forbidden = forbidden or set()
    model = cp_model.CpModel()

    x: dict[tuple[int, int, int], cp_model.IntVar] = {}
    vars_by_assignment: dict[int, list[cp_model.IntVar]] = {}
    vars_by_teacher_slot: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    vars_by_room_slot: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    vars_by_class_slot: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    vars_by_teacher_day: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    vars_by_teacher: dict[int, list[cp_model.IntVar]] = {}
    vars_by_assignment_day: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    # (teacher_id, day, period) -> "is teacher busy at this exact period" bool
    teacher_period_used: dict[tuple[int, int, int], list[cp_model.IntVar]] = {}

    for a in si.assignments:
        subject = si.subjects_by_id[a.subject_id]
        section = si.sections_by_id[a.class_id]
        teacher = si.teachers_by_id[a.teacher_id]

        rooms = candidate_rooms(si, subject, section)
        slots = candidate_slots(si, teacher)

        for room in rooms:
            for slot in slots:
                key = (a.id, room.id, slot.id)
                if key in forbidden:
                    continue
                var = model.new_bool_var(f"x_a{a.id}_r{room.id}_s{slot.id}")
                x[key] = var
                vars_by_assignment.setdefault(a.id, []).append(var)
                vars_by_teacher_slot.setdefault((teacher.id, slot.id), []).append(var)
                vars_by_room_slot.setdefault((room.id, slot.id), []).append(var)
                vars_by_class_slot.setdefault((section.id, slot.id), []).append(var)
                vars_by_teacher_day.setdefault((teacher.id, slot.day), []).append(var)
                vars_by_teacher.setdefault(teacher.id, []).append(var)
                vars_by_assignment_day.setdefault((a.id, slot.day), []).append(var)
                teacher_period_used.setdefault((teacher.id, slot.day, slot.period), []).append(var)

    # --- Hard constraints ---

    # Each assignment gets exactly its subject's weekly_periods.
    for a in si.assignments:
        subject = si.subjects_by_id[a.subject_id]
        avars = vars_by_assignment.get(a.id, [])
        model.add(sum(avars) == subject.weekly_periods)

    # One teacher in one place per slot.
    for tvars in vars_by_teacher_slot.values():
        model.add(sum(tvars) <= 1)

    # One class per room per slot.
    for rvars in vars_by_room_slot.values():
        model.add(sum(rvars) <= 1)

    # One subject per class per slot (a class can't be in two places at once).
    for cvars in vars_by_class_slot.values():
        model.add(sum(cvars) <= 1)

    # Teacher daily cap.
    for (teacher_id, _day), tdvars in vars_by_teacher_day.items():
        teacher = si.teachers_by_id[teacher_id]
        model.add(sum(tdvars) <= teacher.max_periods_per_day)

    # Teacher weekly cap.
    for teacher_id, tvars in vars_by_teacher.items():
        teacher = si.teachers_by_id[teacher_id]
        model.add(sum(tvars) <= teacher.max_periods_per_week)

    # --- Soft constraints (weighted penalty objective) ---
    penalty_terms: list[cp_model.LinearExprT] = []
    penalty_breakdown: dict[str, list[cp_model.IntVar]] = {
        "spread": [],
        "heavy_early": [],
        "preferred_slots": [],
        "idle_gaps": [],
        "balance": [],
    }

    # Spread: no two same-subject periods in a day unless double (cap 2).
    for (a_id, _day), advars in vars_by_assignment_day.items():
        subject = si.subjects_by_id[next(a.subject_id for a in si.assignments if a.id == a_id)]
        allowed = 2 if subject.is_double_period else 1
        if len(advars) <= allowed:
            continue  # can never exceed `allowed`, no penalty var needed
        daily_count = model.new_int_var(0, len(advars), f"cnt_a{a_id}_{_day}")
        model.add(daily_count == sum(advars))
        excess = model.new_int_var(0, len(advars), f"excess_a{a_id}_{_day}")
        model.add_max_equality(excess, [daily_count - allowed, 0])
        penalty_terms.append(weights["spread"] * excess)
        penalty_breakdown["spread"].append(excess)

    # Heavy subjects in periods 1-4.
    assignment_subject = {a.id: si.subjects_by_id[a.subject_id] for a in si.assignments}
    for (a_id, room_id, slot_id), var in x.items():
        subject = assignment_subject[a_id]
        slot = si.slots_by_id[slot_id]
        if si.is_heavy(subject) and slot.period > 4:
            penalty_terms.append(weights["heavy_early"] * var)
            penalty_breakdown["heavy_early"].append(var)

    # Preferred slots (only meaningful for teachers who have any set).
    assignment_teacher = {a.id: a.teacher_id for a in si.assignments}
    for (a_id, room_id, slot_id), var in x.items():
        teacher = si.teachers_by_id[assignment_teacher[a_id]]
        preferred = set(teacher.preferred_slots or [])
        if preferred and slot_id not in preferred:
            penalty_terms.append(weights["preferred_slots"] * var)
            penalty_breakdown["preferred_slots"].append(var)

    # Idle gaps + workload balance, both derived from per-teacher-day period usage.
    for teacher in si.teachers:
        daily_counts: list[cp_model.IntVar] = []
        for day, day_slots in si.slots_by_day.items():
            # Compact index within the day (skips breaks) so a lunch break never
            # counts as an "idle gap".
            used_bools: list[cp_model.IntVar] = []
            for idx, slot in enumerate(day_slots):
                key = (teacher.id, day, slot.period)
                vars_here = teacher_period_used.get(key, [])
                if not vars_here:
                    used = model.new_constant(0)
                else:
                    used = model.new_bool_var(f"used_t{teacher.id}_d{day}_p{slot.period}")
                    model.add(sum(vars_here) == used)
                used_bools.append(used)

            n = len(day_slots)
            count_var = model.new_int_var(0, n, f"cnt_t{teacher.id}_d{day}")
            model.add(count_var == sum(used_bools))
            daily_counts.append(count_var)

            # min/max compact index actually used that day (BIG sentinel for "unused").
            big = n + 1
            min_contribs = []
            max_contribs = []
            for idx, used in enumerate(used_bools):
                mn = model.new_int_var(0, big, f"mn_t{teacher.id}_d{day}_i{idx}")
                model.add(mn == idx).only_enforce_if(used)
                model.add(mn == big).only_enforce_if(used.Not())
                min_contribs.append(mn)
                max_contribs.append(idx * used)

            first_idx = model.new_int_var(0, big, f"first_t{teacher.id}_d{day}")
            model.add_min_equality(first_idx, min_contribs)
            last_idx = model.new_int_var(0, n, f"last_t{teacher.id}_d{day}")
            model.add_max_equality(last_idx, max_contribs)

            span = model.new_int_var(0, n, f"span_t{teacher.id}_d{day}")
            # span = last - first + 1 when count > 0, else 0. When count==0,
            # first_idx == big and last_idx == 0, so clamp with max(...,0).
            raw_span = model.new_int_var(-big, n, f"rawspan_t{teacher.id}_d{day}")
            model.add(raw_span == last_idx - first_idx + 1)
            model.add_max_equality(span, [raw_span, 0])

            idle = model.new_int_var(0, n, f"idle_t{teacher.id}_d{day}")
            model.add(idle == span - count_var)
            penalty_terms.append(weights["idle_gaps"] * idle)
            penalty_breakdown["idle_gaps"].append(idle)

        max_daily = model.new_int_var(0, 8, f"maxd_t{teacher.id}")
        min_daily = model.new_int_var(0, 8, f"mind_t{teacher.id}")
        model.add_max_equality(max_daily, daily_counts)
        model.add_min_equality(min_daily, daily_counts)
        spread_t = model.new_int_var(0, 8, f"spreadt_t{teacher.id}")
        model.add(spread_t == max_daily - min_daily)
        penalty_terms.append(weights["balance"] * spread_t)
        penalty_breakdown["balance"].append(spread_t)

    model.minimize(sum(penalty_terms))

    return ModelBuild(
        model=model,
        x=x,
        vars_by_assignment=vars_by_assignment,
        penalty_terms=penalty_terms,
        penalty_breakdown=penalty_breakdown,
    )


def diagnose_infeasibility(si: SolveInput) -> list[str]:
    """Cheap, deterministic pre-checks for the two most common causes of
    infeasibility. Run before solving so a bad seed/config fails fast with a
    clear reason instead of burning the solver's time budget."""
    reasons: list[str] = []

    for a in si.assignments:
        subject = si.subjects_by_id[a.subject_id]
        section = si.sections_by_id[a.class_id]
        teacher = si.teachers_by_id[a.teacher_id]
        rooms = candidate_rooms(si, subject, section)
        slots = candidate_slots(si, teacher)
        if not rooms:
            reasons.append(
                f"No room fits {section.grade}-{section.section}/{subject.name}: "
                f"needs {'a lab' if subject.needs_lab else 'a classroom'} with "
                f"capacity >= {section.strength}."
            )
        if not slots:
            reasons.append(
                f"{teacher.name} has no available slots left "
                f"(all slots are in their unavailable_slots)."
            )
        if rooms and slots and len(rooms) * len(slots) < subject.weekly_periods:
            reasons.append(
                f"{section.grade}-{section.section}/{subject.name} needs "
                f"{subject.weekly_periods} periods/week but only "
                f"{len(rooms) * len(slots)} room-slot combinations are available."
            )

    weekly_load: dict[int, int] = {}
    for a in si.assignments:
        subject = si.subjects_by_id[a.subject_id]
        weekly_load[a.teacher_id] = weekly_load.get(a.teacher_id, 0) + subject.weekly_periods
    for teacher_id, load in weekly_load.items():
        teacher = si.teachers_by_id[teacher_id]
        if load > teacher.max_periods_per_week:
            reasons.append(
                f"{teacher.name} is assigned {load} periods/week but their cap is "
                f"{teacher.max_periods_per_week}."
            )

    return reasons


@dataclass
class SolveResult:
    status: str
    feasible: bool
    reasons: list[str]
    solution: dict[tuple[int, int, int], bool]
    stats: dict


def solve(
    si: SolveInput,
    weights: dict[str, float] | None = None,
    forbidden: set[tuple[int, int, int]] | None = None,
    time_limit: float = TIME_LIMIT_SECONDS,
) -> SolveResult:
    weights = {**DEFAULT_WEIGHTS, **(weights or {})}

    reasons = diagnose_infeasibility(si)
    if reasons:
        return SolveResult(
            status="INFEASIBLE",
            feasible=False,
            reasons=reasons,
            solution={},
            stats={"wall_time_s": 0.0, "reasons": reasons},
        )

    build = build_model(si, weights, forbidden=forbidden)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    # Match actual available cores — more workers than cores causes contention,
    # not speedup, and free-tier deploy containers may have very few (or
    # fractional) CPUs. os.cpu_count() can be None; fall back conservatively.
    solver.parameters.num_workers = max(1, min(os.cpu_count() or 4, 8))

    start = time_module.perf_counter()
    status = solver.solve(build.model)
    wall_time = time_module.perf_counter() - start

    status_name = solver.status_name(status)
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    if not feasible:
        return SolveResult(
            status=status_name,
            feasible=False,
            reasons=[
                "Solver could not find a feasible schedule within the time budget "
                "despite passing aggregate capacity checks — a combinatorial "
                "conflict exists across teacher/room/slot constraints."
            ],
            solution={},
            stats={
                "wall_time_s": round(wall_time, 3),
                "status": status_name,
                "num_branches": solver.num_branches,
                "num_workers": solver.parameters.num_workers,
                "cpu_count": os.cpu_count(),
            },
        )

    solution = {key: bool(solver.value(var)) for key, var in build.x.items()}
    breakdown = {
        name: sum(solver.value(v) for v in vars_)
        for name, vars_ in build.penalty_breakdown.items()
    }

    stats = {
        "status": status_name,
        "wall_time_s": round(wall_time, 3),
        "num_branches": solver.num_branches,
        "objective_value": solver.objective_value,
        "soft_violations": breakdown,
        "total_entries": sum(1 for v in solution.values() if v),
    }
    return SolveResult(
        status=status_name, feasible=True, reasons=[], solution=solution, stats=stats
    )


def persist_result(
    db: Session, si: SolveInput, result: SolveResult, label: str
) -> TimetableVersion:
    db.execute(update(TimetableVersion).values(is_active=False))

    version = TimetableVersion(label=label, solver_stats=result.stats, is_active=True)
    db.add(version)
    db.flush()

    entries = []
    for (a_id, room_id, slot_id), chosen in result.solution.items():
        if not chosen:
            continue
        assignment = next(a for a in si.assignments if a.id == a_id)
        entries.append(
            TimetableEntry(
                version_id=version.id,
                class_id=assignment.class_id,
                subject_id=assignment.subject_id,
                teacher_id=assignment.teacher_id,
                room_id=room_id,
                slot_id=slot_id,
                is_substitution=False,
                original_teacher_id=None,
            )
        )
    db.bulk_save_objects(entries)
    db.flush()
    return version


def generate_timetable(
    db: Session, weights: dict[str, float] | None = None, label: str = "Generated timetable"
) -> dict:
    si = load_solve_input(db)
    result = solve(si, weights=weights, time_limit=settings.solver_time_limit_s)

    if not result.feasible:
        return {
            "feasible": False,
            "status": result.status,
            "reasons": result.reasons,
            "stats": result.stats,
        }

    version = persist_result(db, si, result, label=label)
    db.commit()

    return {
        "feasible": True,
        "version_id": version.id,
        "status": result.status,
        "stats": result.stats,
    }

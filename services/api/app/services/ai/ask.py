"""Ask Shaala (PROMPT.md §6.6): natural language -> constrained JSON intent ->
a whitelist of hand-written query functions. The model never writes SQL --
that isn't just a README claim, it's the actual shape of this module: Gemini
(or, with no API key, a deterministic keyword matcher) only ever picks a
function *name* out of `_WHITELIST` and a small params dict. Every query
against the database lives in one of the hand-written functions below, most
of them the exact same pure functions the Action Center's signal rules
already use and already have tests for (services/signals/rules.py) -- so
"who's free Tuesday period 3" and the Action Center's "uncovered classes"
card are, deliberately, backed by identical, already-verified logic.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEMO_ANCHOR_DATE
from app.db.models import (
    AttendanceRecord,
    AttendanceStatus,
    ClassSection,
    Student,
    Teacher,
    TimeSlot,
    TimetableEntry,
)
from app.services.ai.gemini_text import GeminiTextError, call_gemini_json
from app.services.signals.rules import (
    detect_documents_need_review,
    detect_low_attendance_cliff,
    detect_room_conflicts,
    detect_staffing_shortfall,
    detect_uncovered_classes,
)
from app.services.timetable.explain import DAY_NAMES, active_version

logger = logging.getLogger(__name__)

_DAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "wed": 2,
    "weds": 2,
    "wednesday": 2,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "thursday": 3,
    "fri": 4,
    "friday": 4,
    "sat": 5,
    "saturday": 5,
}

ASK_PROMPT_TEMPLATE = """You translate a school principal's question into ONE function call \
from a fixed whitelist. You never write SQL or a database query yourself -- only pick a \
function name and its parameters.

Available functions:
- who_is_free(day: one of Mon/Tue/Wed/Thu/Fri/Sat, period: integer 1-8)
- attendance_rate(class_label: string like "10-A", or null for the whole school; \
days: integer, default 7)
- uncovered_classes_today()
- students_at_risk()
- staffing_shortfall(department: string or null)
- documents_pending()
- room_conflicts()

Return ONLY JSON: {{"intent": "<one function name above, or null if none fits>", "params": {{...}}}}

Question: {query}
"""


class AskError(Exception):
    """Raised by a whitelisted function when it can't answer -- bad params,
    no matching data. Caught by answer_query and turned into a plain-language
    answer, never a 500."""


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


# --- whitelisted query functions -------------------------------------------
# Every one of these has the same signature, (db, params, today) -> dict, so
# dispatch below never needs to special-case a function by identity.


def who_is_free(db: Session, params: dict, today: date) -> dict:
    day_raw = str(params.get("day") or "").strip().lower()
    weekday = _DAY_ALIASES.get(day_raw)
    period = _as_int(params.get("period"))
    if weekday is None or period is None:
        raise AskError("I need a day (Mon-Sat) and a period number to answer that.")

    slot = db.scalar(select(TimeSlot).where(TimeSlot.day == weekday, TimeSlot.period == period))
    if slot is None:
        raise AskError(f"There's no period {period} on {DAY_NAMES[weekday]}.")

    version = active_version(db)
    busy_teacher_ids: set[int] = set()
    if version is not None:
        busy_teacher_ids = {
            e.teacher_id
            for e in db.scalars(
                select(TimetableEntry).where(
                    TimetableEntry.version_id == version.id, TimetableEntry.slot_id == slot.id
                )
            )
        }

    free = [
        t
        for t in db.scalars(select(Teacher))
        if t.id not in busy_teacher_ids and slot.id not in t.unavailable_slots
    ]
    return {
        "day": DAY_NAMES[weekday],
        "period": period,
        "count": len(free),
        "free_teachers": [{"name": t.name, "dept": t.dept} for t in free],
    }


def attendance_rate(db: Session, params: dict, today: date) -> dict:
    days = _as_int(params.get("days")) or 7
    window_start = today - timedelta(days=days - 1)
    stmt = select(AttendanceRecord.status).where(
        AttendanceRecord.date >= window_start, AttendanceRecord.date <= today
    )

    class_label = params.get("class_label")
    if class_label:
        grade, _, section = str(class_label).partition("-")
        section_obj = db.scalar(
            select(ClassSection).where(
                ClassSection.grade == grade.strip(), ClassSection.section == section.strip().upper()
            )
        )
        if section_obj is None:
            raise AskError(f"I don't recognize the class '{class_label}'.")
        student_ids = list(db.scalars(select(Student.id).where(Student.class_id == section_obj.id)))
        stmt = stmt.where(AttendanceRecord.student_id.in_(student_ids))

    statuses = list(db.scalars(stmt))
    total = len(statuses)
    if total == 0:
        raise AskError("No attendance records found for that window.")
    present = sum(1 for s in statuses if s != AttendanceStatus.absent)
    return {
        "class_label": class_label,
        "days": days,
        "records": total,
        "rate_pct": round(present / total * 100, 1),
    }


def uncovered_classes_today(db: Session, params: dict, today: date) -> dict:
    detections = detect_uncovered_classes(db, today)
    return {
        "count": len(detections),
        "items": [{"title": d.title, "body": d.body} for d in detections],
    }


def students_at_risk(db: Session, params: dict, today: date) -> dict:
    detections = detect_low_attendance_cliff(db, today)
    return {
        "count": len(detections),
        "items": [{"title": d.title, "body": d.body} for d in detections],
    }


def staffing_shortfall(db: Session, params: dict, today: date) -> dict:
    detections = detect_staffing_shortfall(db, today)
    department = params.get("department")
    if department:
        detections = [
            d
            for d in detections
            if str(d.payload.get("department", "")).lower() == str(department).lower()
        ]
    return {
        "count": len(detections),
        "items": [{"title": d.title, "body": d.body} for d in detections],
    }


def documents_pending(db: Session, params: dict, today: date) -> dict:
    detections = detect_documents_need_review(db, today)
    return {
        "count": len(detections),
        "items": [{"title": d.title, "body": d.body} for d in detections],
    }


def room_conflicts(db: Session, params: dict, today: date) -> dict:
    detections = detect_room_conflicts(db, today)
    return {
        "count": len(detections),
        "items": [{"title": d.title, "body": d.body} for d in detections],
    }


_WHITELIST: dict[str, Callable[[Session, dict, date], dict]] = {
    "who_is_free": who_is_free,
    "attendance_rate": attendance_rate,
    "uncovered_classes_today": uncovered_classes_today,
    "students_at_risk": students_at_risk,
    "staffing_shortfall": staffing_shortfall,
    "documents_pending": documents_pending,
    "room_conflicts": room_conflicts,
}

_NO_RESULTS_ANSWER = {
    "uncovered_classes_today": "Every class is covered today.",
    "students_at_risk": "No students have dropped below the 75% attendance threshold this week.",
    "staffing_shortfall": "No department is projected short-staffed in the next 7 days.",
    "documents_pending": "No documents are waiting for review.",
    "room_conflicts": "No room double-bookings in the active timetable.",
}

_UNKNOWN_INTENT_ANSWER = (
    "I can only answer questions about substitute coverage, attendance, staffing "
    'forecasts, and document review. Try: "Who\'s free Tuesday period 3?"'
)


def _format_answer(intent: str, result: dict) -> str:
    if intent == "who_is_free":
        n = result["count"]
        if n == 0:
            return f"No one is free {result['day']} period {result['period']}."
        names = ", ".join(t["name"] for t in result["free_teachers"][:6])
        more = f", and {n - 6} more" if n > 6 else ""
        return (
            f"{n} teacher{'s' if n != 1 else ''} free {result['day']} "
            f"period {result['period']}: {names}{more}."
        )

    if intent == "attendance_rate":
        label = result["class_label"] or "the whole school"
        return (
            f"Attendance for {label} over the last {result['days']} days is "
            f"{result['rate_pct']}% ({result['records']} records)."
        )

    if intent in _NO_RESULTS_ANSWER:
        if result["count"] == 0:
            return _NO_RESULTS_ANSWER[intent]
        return " ".join(item["body"] for item in result["items"][:3])

    return "I couldn't work out how to answer that."


# --- intent parsing: Gemini, with a deterministic keyword fallback ---------

_PERIOD_RE = re.compile(r"period\s*(\d+)|\bp(\d+)\b", re.IGNORECASE)
_CLASS_RE = re.compile(r"\b(\d{1,2})\s*[-–]?\s*([A-Za-z])\b")


def _extract_day_and_period(q: str) -> tuple[str | None, int | None]:
    day = next((name for name in _DAY_ALIASES if re.search(rf"\b{name}\b", q)), None)
    m = _PERIOD_RE.search(q)
    period = int(m.group(1) or m.group(2)) if m else None
    return day, period


def _extract_class_label(q: str) -> str | None:
    m = _CLASS_RE.search(q)
    return f"{m.group(1)}-{m.group(2).upper()}" if m else None


def _extract_department(db: Session, q: str) -> str | None:
    for (dept,) in db.execute(select(Teacher.dept).distinct()):
        if dept.lower() in q:
            return dept
    return None


def _parse_intent_fallback(db: Session, query: str) -> dict:
    q = query.lower()
    if "free" in q and ("period" in q or re.search(r"\bp\d+\b", q)):
        day, period = _extract_day_and_period(q)
        return {"intent": "who_is_free", "params": {"day": day, "period": period}}
    if "attend" in q:
        return {
            "intent": "attendance_rate",
            "params": {"class_label": _extract_class_label(q), "days": 7},
        }
    if "uncovered" in q:
        return {"intent": "uncovered_classes_today", "params": {}}
    if "at risk" in q or "below 75" in q or "dropping" in q or "cliff" in q:
        return {"intent": "students_at_risk", "params": {}}
    if "short" in q or "substitute" in q or "pre-clear" in q or "preclear" in q:
        return {
            "intent": "staffing_shortfall",
            "params": {"department": _extract_department(db, q)},
        }
    if "document" in q or "review" in q:
        return {"intent": "documents_pending", "params": {}}
    if "conflict" in q or "double" in q:
        return {"intent": "room_conflicts", "params": {}}
    return {"intent": None, "params": {}}


def _parse_intent_via_gemini(query: str) -> dict:
    result = call_gemini_json(ASK_PROMPT_TEMPLATE.format(query=query))
    intent = result.get("intent")
    params = result.get("params")
    return {"intent": intent, "params": params if isinstance(params, dict) else {}}


def answer_query(db: Session, query: str, today: date | None = None) -> dict:
    today = today or DEMO_ANCHOR_DATE
    query = (query or "").strip()
    if not query:
        raise AskError("Ask a question first.")

    source = "gemini"
    try:
        parsed = _parse_intent_via_gemini(query)
    except GeminiTextError as e:
        logger.warning(
            "Ask Shaala intent parsing via Gemini failed (%s) -- falling back to keywords.", e
        )
        parsed = _parse_intent_fallback(db, query)
        source = "fallback"

    intent = parsed.get("intent")
    params = parsed.get("params") or {}

    if intent not in _WHITELIST:
        return {
            "query": query,
            "intent": None,
            "answer": _UNKNOWN_INTENT_ANSWER,
            "data": None,
            "source": source,
        }

    try:
        result = _WHITELIST[intent](db, params, today)
    except AskError as e:
        return {"query": query, "intent": intent, "answer": str(e), "data": None, "source": source}

    return {
        "query": query,
        "intent": intent,
        "answer": _format_answer(intent, result),
        "data": result,
        "source": source,
    }

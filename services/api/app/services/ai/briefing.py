"""Principal's Weekly Briefing (PROMPT.md §6.6): one button turns computed
aggregates into a short narrative that cites its own numbers. `compute_stats`
is deliberately the only thing that touches the database here -- it returns
small counts and rates, never raw rows, and that dict is the entire universe
of facts the model (or the fallback template) is allowed to mention.

Mirrors the vision provider's demo-safety contract: any Gemini failure --
including simply no GEMINI_API_KEY configured, the normal state for this repo
without a key added -- falls back to a deterministic template built from the
exact same stats dict, so the button never dead-ends in an error screen.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import DEMO_ANCHOR_DATE
from app.db.models import (
    ActionItem,
    ActionStatus,
    AttendanceRecord,
    AttendanceStatus,
    Document,
    DocumentStatus,
)
from app.services.ai.gemini_text import GeminiTextError, call_gemini_json
from app.services.signals.rules import ATTENDANCE_CLIFF, MIN_RECORDS_FOR_CLIFF
from app.services.staffing.forecast import forecast as staffing_forecast

logger = logging.getLogger(__name__)

ATTENDANCE_WINDOW_DAYS = 7

BRIEFING_PROMPT_TEMPLATE = """You write a short weekly briefing for an Indian school \
principal. Use ONLY the numbers in the JSON below -- never invent a statistic that \
isn't listed here. Cite at least two of the numbers directly. Write 3-5 plain \
sentences, no markdown, no bullet points, no headers.

Return ONLY JSON: {{"narrative": "<your 3-5 sentence briefing>"}}

Stats:
{stats_json}
"""


def _at_risk_student_count(db: Session, today: date) -> int:
    window_start = today - timedelta(days=ATTENDANCE_WINDOW_DAYS - 1)
    stmt = select(AttendanceRecord.student_id, AttendanceRecord.status).where(
        AttendanceRecord.date >= window_start, AttendanceRecord.date <= today
    )
    totals: dict[int, int] = {}
    presents: dict[int, int] = {}
    for student_id, status in db.execute(stmt):
        totals[student_id] = totals.get(student_id, 0) + 1
        if status != AttendanceStatus.absent:
            presents[student_id] = presents.get(student_id, 0) + 1
    return sum(
        1
        for sid, total in totals.items()
        if total >= MIN_RECORDS_FOR_CLIFF and (presents.get(sid, 0) / total) < ATTENDANCE_CLIFF
    )


def _staffing_peak(db: Session, today: date) -> dict | None:
    result = staffing_forecast(db, days=7, as_of=today)
    peak = None
    for dept in result["departments"]:
        for day in dept["days"]:
            if peak is None or day["expected_absences"] > peak["expected_absences"]:
                peak = {
                    "department": dept["department"],
                    "date": day["date"],
                    "expected_absences": round(day["expected_absences"], 1),
                }
    return peak


def compute_stats(db: Session, today: date | None = None) -> dict:
    today = today or DEMO_ANCHOR_DATE

    open_items = list(db.scalars(select(ActionItem).where(ActionItem.status == ActionStatus.open)))
    open_by_severity: dict[str, int] = {}
    for item in open_items:
        open_by_severity[item.severity.value] = open_by_severity.get(item.severity.value, 0) + 1

    window_start = today - timedelta(days=ATTENDANCE_WINDOW_DAYS - 1)
    statuses = list(
        db.scalars(
            select(AttendanceRecord.status).where(
                AttendanceRecord.date >= window_start, AttendanceRecord.date <= today
            )
        )
    )
    total = len(statuses)
    present = sum(1 for s in statuses if s != AttendanceStatus.absent)
    attendance_rate_pct = round(present / total * 100, 1) if total else None

    docs_pending = (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.status == DocumentStatus.needs_review)
        )
        or 0
    )

    return {
        "as_of": today.isoformat(),
        "open_actions_total": len(open_items),
        "open_actions_by_severity": open_by_severity,
        "attendance_rate_pct_7d": attendance_rate_pct,
        "at_risk_students": _at_risk_student_count(db, today),
        "documents_pending_review": docs_pending,
        "staffing_peak": _staffing_peak(db, today),
    }


def _template_narrative(stats: dict) -> str:
    parts: list[str] = []

    total = stats["open_actions_total"]
    if total:
        critical = stats["open_actions_by_severity"].get("critical", 0)
        tail = f", {critical} of them critical" if critical else ""
        parts.append(
            f"There {'is' if total == 1 else 'are'} {total} open item"
            f"{'' if total == 1 else 's'} on the Action Center{tail}."
        )
    else:
        parts.append("The Action Center is clear -- nothing needs attention right now.")

    if stats["attendance_rate_pct_7d"] is not None:
        parts.append(
            f"Attendance over the last 7 days is running at {stats['attendance_rate_pct_7d']}%."
        )

    at_risk = stats["at_risk_students"]
    if at_risk:
        parts.append(
            f"{at_risk} student{'s' if at_risk != 1 else ''} "
            "have fallen below the 75% attendance threshold this week."
        )

    docs = stats["documents_pending_review"]
    if docs:
        parts.append(f"{docs} scanned document{'s' if docs != 1 else ''} still need review.")

    peak = stats["staffing_peak"]
    if peak and peak["expected_absences"] > 0:
        day_label = date.fromisoformat(peak["date"]).strftime("%A")
        n = peak["expected_absences"]
        parts.append(
            f"The tightest staffing day ahead is {day_label} in {peak['department']}, "
            f"with about {n} expected absence{'s' if n != 1 else ''}."
        )

    return " ".join(parts)


def generate_briefing(db: Session, today: date | None = None) -> dict:
    today = today or DEMO_ANCHOR_DATE
    stats = compute_stats(db, today)

    source = "gemini"
    try:
        prompt = BRIEFING_PROMPT_TEMPLATE.format(stats_json=json.dumps(stats, indent=2))
        result = call_gemini_json(prompt)
        narrative = result.get("narrative")
        if not isinstance(narrative, str) or not narrative.strip():
            raise GeminiTextError("Gemini response missing a 'narrative' string.")
    except GeminiTextError as e:
        logger.warning("Weekly Briefing via Gemini failed (%s) -- falling back to template.", e)
        narrative = _template_narrative(stats)
        source = "template"

    return {
        "narrative": narrative,
        "stats": stats,
        "source": source,
        "generated_at": datetime.now(UTC).isoformat(),
    }

"""The proactive rule engine (PROMPT.md §6.3): a registry of pure functions,
each reading real DB state and reporting what it currently detects.
`run_signals` reconciles that against open ActionItem rows -- creates what's
newly true, refreshes what's still true, auto-resolves what stopped being
true. Called on a 30s APScheduler tick *and* immediately after relevant
mutations (see call sites in routers/), per PROMPT.md §6.3.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEMO_ANCHOR_DATE
from app.db.models import ActionItem, ActionSeverity, ActionStatus


@dataclass
class Detection:
    """What a rule found. `key` identifies this specific instance within its
    kind (e.g. one per absence, one per room+slot) so the reconciler can tell
    "still the same problem" from "a new one" and "resolved"."""

    key: str
    title: str
    body: str
    payload: dict
    primary_action: str


SignalFn = Callable[[Session, date], list[Detection]]


@dataclass
class _Rule:
    fn: SignalFn
    kind: str
    severity: ActionSeverity


_REGISTRY: list[_Rule] = []


def signal(kind: str, severity: str) -> Callable[[SignalFn], SignalFn]:
    def decorator(fn: SignalFn) -> SignalFn:
        _REGISTRY.append(_Rule(fn=fn, kind=kind, severity=ActionSeverity(severity)))
        return fn

    return decorator


def run_signals(db: Session, today: date | None = None) -> list[ActionItem]:
    # Anchored to the demo's fixed "today", not the real wall clock -- see
    # config.DEMO_ANCHOR_DATE.
    today = today or DEMO_ANCHOR_DATE
    changed: list[ActionItem] = []

    for rule in _REGISTRY:
        detections = {d.key: d for d in rule.fn(db, today)}
        open_items = list(
            db.scalars(
                select(ActionItem).where(
                    ActionItem.kind == rule.kind, ActionItem.status == ActionStatus.open
                )
            )
        )
        open_by_key = {item.payload.get("_key"): item for item in open_items}

        for key, det in detections.items():
            existing = open_by_key.get(key)
            if existing is None:
                item = ActionItem(
                    kind=rule.kind,
                    severity=rule.severity,
                    title=det.title,
                    body=det.body,
                    payload={**det.payload, "_key": key},
                    primary_action=det.primary_action,
                )
                db.add(item)
                changed.append(item)
            elif existing.title != det.title or existing.body != det.body:
                existing.title = det.title
                existing.body = det.body
                existing.payload = {**det.payload, "_key": key}
                changed.append(existing)

        for dedup_key, item in open_by_key.items():
            if dedup_key not in detections:
                item.status = ActionStatus.resolved
                item.resolved_at = datetime.now(UTC)
                changed.append(item)

    db.commit()
    return changed

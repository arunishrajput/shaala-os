from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActionItem, ActionStatus
from app.db.session import get_db
from app.security import get_current_user
from app.services.notifications import draft_parent_messages
from app.ws.manager import manager

router = APIRouter(prefix="/actions", tags=["actions"], dependencies=[Depends(get_current_user)])

# Not alphabetical -- the Action Center is a priority stack (PROMPT.md §6.3),
# critical always leads regardless of creation time.
_SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}


def _out(item: ActionItem) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "severity": item.severity.value,
        "title": item.title,
        "body": item.body,
        "payload": item.payload,
        "status": item.status.value,
        "created_at": item.created_at,
        "resolved_at": item.resolved_at,
        "primary_action": item.primary_action,
    }


@router.get("")
def list_actions(status: str | None = "open", db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(ActionItem).order_by(ActionItem.created_at.desc())
    if status is not None:
        stmt = stmt.where(ActionItem.status == status)
    items = list(db.scalars(stmt))
    items.sort(key=lambda a: _SEVERITY_ORDER.get(a.severity.value, 9))
    return [_out(a) for a in items]


@router.post("/{action_id}/resolve")
async def resolve(action_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(ActionItem, action_id)
    if item is None:
        raise HTTPException(status_code=404, detail="No such action item.")
    item.status = ActionStatus.resolved
    item.resolved_at = datetime.now(UTC)
    db.commit()
    await manager.broadcast("action.resolved", _out(item))
    return _out(item)


@router.post("/{action_id}/draft-messages")
async def draft_messages(action_id: int, db: Session = Depends(get_db)) -> dict:
    """The low_attendance_trend card's primary action. Drafting messages
    doesn't itself fix the attendance number, so unlike /resolve this is a
    genuine acknowledgment: the card is done *for this admin*, not because the
    underlying condition changed -- the next signals tick is what actually
    re-evaluates whether it's still true.
    """
    item = db.get(ActionItem, action_id)
    if item is None:
        raise HTTPException(status_code=404, detail="No such action item.")
    if item.kind != "low_attendance_trend":
        raise HTTPException(
            status_code=400, detail=f"kind='{item.kind}' has no message-drafting action."
        )
    student_ids = item.payload.get("student_ids", [])
    drafted = draft_parent_messages(db, student_ids)

    item.status = ActionStatus.resolved
    item.resolved_at = datetime.now(UTC)
    db.commit()

    await manager.broadcast("notifications.updated", {})
    await manager.broadcast("action.resolved", _out(item))
    return {"drafted": len(drafted), "action": _out(item)}


@router.post("/{action_id}/dismiss")
async def dismiss(action_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(ActionItem, action_id)
    if item is None:
        raise HTTPException(status_code=404, detail="No such action item.")
    item.status = ActionStatus.dismissed
    item.resolved_at = datetime.now(UTC)
    db.commit()
    await manager.broadcast("action.dismissed", _out(item))
    return _out(item)

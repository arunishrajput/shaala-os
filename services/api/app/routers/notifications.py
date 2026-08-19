from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Notification
from app.db.session import get_db
from app.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(get_current_user)])


def _out(n: Notification) -> dict:
    return {
        "id": n.id,
        "to_name": n.to_name,
        "to_phone": n.to_phone,
        "channel": n.channel,
        "body": n.body,
        "status": n.status,
        "created_at": n.created_at,
    }


@router.get("")
def list_notifications(limit: int = 20, db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
    return [_out(n) for n in db.scalars(stmt)]

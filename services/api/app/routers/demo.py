from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.db import seed as seed_module
from app.db.session import SessionLocal
from app.services.signals.registry import run_signals
from app.services.timetable.explain import clear_cache
from app.ws.manager import manager

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/reset")
async def reset() -> dict:
    """Judges mutate shared demo data at odd hours (PROMPT.md §11) -- this
    restores the fixed-seed baseline. seed.main() is synchronous and does a
    lot of DB round trips (the 90-day attendance/absence history especially),
    so it runs in a thread rather than blocking the event loop for everyone
    else connected over /ws/events during the reset.
    """
    await run_in_threadpool(seed_module.main)
    clear_cache()  # stale entry ids from the wiped timetable tables

    db = SessionLocal()
    try:
        run_signals(db)
    finally:
        db.close()

    await manager.broadcast("demo.reset", {})
    return {"status": "ok"}

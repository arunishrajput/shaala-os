import os

from fastapi import APIRouter, Depends, Header, HTTPException
from starlette.concurrency import run_in_threadpool

from app.db import seed as seed_module
from app.db.session import SessionLocal
from app.services.signals.registry import run_signals
from app.services.timetable.explain import clear_cache
from app.ws.manager import manager

router = APIRouter(prefix="/demo", tags=["demo"])

# The reset key is shared between this endpoint and the GitHub Actions
# demo-survival workflow. Set DEMO_RESET_KEY in your Render environment and
# as a GitHub Actions secret (Settings → Secrets → Actions → DEMO_RESET_KEY).
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
_RESET_KEY = os.getenv("DEMO_RESET_KEY", "")


def _verify_reset_key(x_reset_key: str = Header(default="")) -> None:
    """Dependency: require X-Reset-Key header to match DEMO_RESET_KEY env var."""
    if not _RESET_KEY:
        raise HTTPException(
            status_code=500,
            detail="DEMO_RESET_KEY is not configured on the server.",
        )
    if x_reset_key != _RESET_KEY:
        raise HTTPException(status_code=403, detail="Invalid reset key.")


@router.post("/reset", dependencies=[Depends(_verify_reset_key)])
async def reset() -> dict:
    """Judges mutate shared demo data at odd hours (PROMPT.md \u00a711) -- this
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

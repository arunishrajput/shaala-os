from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import SessionLocal
from app.routers import (
    actions,
    attendance,
    auth,
    demo,
    documents,
    health,
    notifications,
    people,
    staffing,
    timetable,
)
from app.services.signals import rules  # noqa: F401 -- registers the @signal rules on import
from app.services.signals.registry import run_signals
from app.ws.routes import router as ws_router

scheduler = AsyncIOScheduler()


def _signals_tick() -> None:
    db = SessionLocal()
    try:
        run_signals(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run once at startup too, so the Action Center isn't stale for up to 30s
    # on a cold boot or right after a demo reset.
    _signals_tick()
    scheduler.add_job(_signals_tick, "interval", seconds=30, id="signals_tick")
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Shaala OS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
# attendance before people: both declare a /students/... path, and FastAPI
# matches in registration order, not by specificity. attendance's literal
# /students/id-cards.pdf must be tried before people's parameterized
# /students/{student_id} or the latter swallows it (int-parses "id-cards.pdf",
# 422s) — found by the id-cards.pdf test actually exercising the route.
app.include_router(attendance.router)
app.include_router(people.router)
app.include_router(timetable.router)
app.include_router(documents.router)
app.include_router(actions.router)
app.include_router(demo.router)
app.include_router(notifications.router)
app.include_router(staffing.router)
app.include_router(ws_router)

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.db.session import SessionLocal
from app.limiter import limiter
from app.routers import (
    actions,
    ask,
    attendance,
    auth,
    briefing,
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

# Rate limiter — must be registered before any route that uses @limiter.limit().
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Fail fast if CORS_ORIGINS is not set — a missing value previously fell back
# to ["*"], allowing any origin to make credentialed cross-origin requests.
if not settings.cors_origins:
    raise RuntimeError(
        "CORS_ORIGINS must be set (comma-separated list of allowed origins). "
        "Example: CORS_ORIGINS=https://shaala-os.vercel.app,http://localhost:5173"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Security + cache headers ──────────────────────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)

    # Prevent browser caching — this app's live-update model depends on every
    # refetch actually hitting the server (browsers served stale counts from XHR
    # cache on rapid WS-triggered refetches; verified with direct curl vs app).
    response.headers["Cache-Control"] = "no-store"

    # Prevent MIME-type sniffing — stops browsers treating an uploaded image
    # that embeds a <script> tag as executable JavaScript.
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Deny framing — prevents clickjacking attacks that embed this app in an
    # invisible iframe on a malicious page.
    response.headers["X-Frame-Options"] = "DENY"

    # HSTS — instruct browsers to use HTTPS for the next year.
    # Render enforces HTTPS by default; this header tells browsers to skip
    # the initial HTTP request entirely on subsequent visits.
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )

    # Referrer policy — don't leak the full URL in the Referer header when
    # the app links to third-party resources.
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # CSP — restrict where the browser may load resources from.
    # Flutter web requires unsafe-inline for both scripts and styles.
    # Adjust connect-src if you add third-party API calls in future phases.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' wss:; "
        "frame-ancestors 'none';"
    )

    return response


app.include_router(health.router)
app.include_router(auth.router)
# attendance before people: both declare a /students/... path, and FastAPI
# matches in registration order, not by specificity. attendance's literal
# /students/id-cards.pdf must be tried before people's parameterised
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
app.include_router(briefing.router)
app.include_router(ask.router)
app.include_router(ws_router)

#!/usr/bin/env python3
"""
Shaala OS — Remaining Security Fix PRs (Round 2)
=================================================
Run from the root of your shaala-os repo in Git Bash:

    cd ~/Desktop/shaala-os
    python raise_remaining_prs.py

Pre-requisites:
    1. GitHub CLI installed  →  https://cli.github.com/
    2. gh auth login         →  run once
    3. origin = your fork   →  git remote get-url origin

Raises 6 PRs from Phantom9869/shaala-os  →  arunishrajput/shaala-os
for the 11 remaining open issues from the security audit.
"""

import os
import subprocess
import sys

OFFICIAL_REPO = "arunishrajput/shaala-os"


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def run(cmd, check=True, cwd=None):
    print(f"  $ {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.stdout.strip():
        print(f"    {result.stdout.strip()}")
    if result.returncode != 0 and check:
        print(f"  ✖ ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result


def write(path, content):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"  ✎ wrote {path}")


def replace_in_file(path, old, new):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if old not in content:
        print(f"  ⚠  pattern not found in {path} — skipping")
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.replace(old, new, 1))
    print(f"  ✎ patched {path}")
    return True


def append_to_file(path, text):
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"  ✎ appended to {path}")


def make_pr(branch, title, body, ops, username):
    print(f"\n{'='*70}")
    print(f"  PR: {title}")
    print(f"{'='*70}")
    run("git checkout main")
    run(f"git checkout -b {branch}")
    for op in ops:
        if op[0] == "write":
            write(op[1], op[2])
        elif op[0] == "replace":
            replace_in_file(op[1], op[2], op[3])
        elif op[0] == "append":
            append_to_file(op[1], op[2])
    run("git add -A")
    run(f'git commit -m "{title}"')
    run(f"git push origin {branch}")
    run(
        f'gh pr create '
        f'--repo {OFFICIAL_REPO} '
        f'--base main '
        f'--head {username}:{branch} '
        f'--title "{title}" '
        f'--body "{body}"'
    )
    print(f"  ✅  {username}:{branch}  →  {OFFICIAL_REPO}/main")


def get_username():
    r = run("gh api user --jq .login", check=False)
    username = r.stdout.strip()
    if not username:
        print("  ✖ Could not get GitHub username. Run: gh auth login")
        sys.exit(1)
    return username


def preflight(username):
    print("Checking prerequisites …")
    if not os.path.isdir(".git"):
        print("  ✖ Not a git repo root. cd into your shaala-os repo first.")
        sys.exit(1)
    r = run("gh --version", check=False)
    if r.returncode != 0:
        print("  ✖ GitHub CLI not found. Install from https://cli.github.com/")
        sys.exit(1)
    r = run("gh auth status", check=False)
    if r.returncode != 0:
        print("  ✖ Not logged in. Run: gh auth login")
        sys.exit(1)
    r = run("git remote get-url origin", check=False)
    if "arunishrajput" in r.stdout:
        print("  ✖ origin points to the official repo. Set it to your fork:")
        print(f"    git remote set-url origin https://github.com/{username}/shaala-os.git")
        sys.exit(1)
    run("git checkout main")
    run("git pull origin main")
    print("  ✅  Prerequisites OK\n")


# ──────────────────────────────────────────────────────────────────────────────
# PR 1 — fix/demo-reset-protection  (issue #2)
# POST /demo/reset is an unauthenticated public endpoint that wipes the DB.
# Fix: require X-Reset-Key header matching DEMO_RESET_KEY env var.
# ──────────────────────────────────────────────────────────────────────────────

DEMO_PY = '''\
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
    """Judges mutate shared demo data at odd hours (PROMPT.md \\u00a711) -- this
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
'''

PR1_OPS = [
    ("write", "services/api/app/routers/demo.py", DEMO_PY),

    # CI workflow: pass the key in the curl call
    ("replace",
     ".github/workflows/demo-survival.yml",
     '          curl -sf -o /dev/null -w "reset: %{http_code} in %{time_total}s\\n" \\\n            -X POST https://shaala-os-api.onrender.com/demo/reset',
     '          curl -sf -o /dev/null -w "reset: %{http_code} in %{time_total}s\\n" \\\n            -X POST https://shaala-os-api.onrender.com/demo/reset \\\n            -H "X-Reset-Key: ${{ secrets.DEMO_RESET_KEY }}"'),

    # Test: pass the key header (conftest.py already sets DEMO_RESET_KEY=pytest-demo-reset-key)
    ("replace",
     "services/api/tests/test_demo_reset.py",
     '    resp = client.post("/demo/reset")',
     '    resp = client.post("/demo/reset", headers={"X-Reset-Key": "pytest-demo-reset-key"})'),

    # .env.example: document the new variable
    ("append",
     ".env.example",
     """
# --- Demo reset protection ---
# Required by POST /demo/reset. Add this value to GitHub Actions Secrets too
# (Settings → Secrets → Actions → DEMO_RESET_KEY) so the hourly reset works.
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
DEMO_RESET_KEY=replace-with-a-real-random-key
"""),
]

PR1_BODY = """\
## What
Fixes issue **#2** — `POST /demo/reset` was an unauthenticated public endpoint \
that wiped and re-seeded the entire school database with no credentials required.

### Changes
- `demo.py`: added `_verify_reset_key` dependency requiring `X-Reset-Key` header \
matching the `DEMO_RESET_KEY` env var. Returns `403` on wrong key, `500` if server \
is misconfigured.
- `demo-survival.yml`: CI hourly-reset job now passes `X-Reset-Key` from the \
`DEMO_RESET_KEY` Actions secret.
- `test_demo_reset.py`: test now sends the key header (conftest.py already sets \
`DEMO_RESET_KEY=pytest-demo-reset-key` for the test environment).
- `.env.example`: documents the new required variable.

## Required actions after merge
1. Generate a key: `python -c "import secrets; print(secrets.token_hex(32))"`
2. Set `DEMO_RESET_KEY=<value>` in Render → Environment Variables
3. Add `DEMO_RESET_KEY` to GitHub → Settings → Secrets → Actions
"""


# ──────────────────────────────────────────────────────────────────────────────
# PR 2 — fix/websocket-auth  (issue #6)
# /ws/events accepted anonymous connections and broadcast all school events
# (attendance marks, student names, guardian numbers) to anyone.
# Fix: require ?token=<jwt> query param, close with 1008 if invalid.
# ──────────────────────────────────────────────────────────────────────────────

WS_ROUTES_PY = '''\
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.security import decode_access_token
from app.ws.manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/events")
async def ws_events(
    websocket: WebSocket,
    token: str = Query(..., description="Bearer JWT — same token used for REST calls"),
) -> None:
    """Real-time event stream.

    The Flutter client appends ?token=<jwt> to the WebSocket URL before
    connecting. We verify it here before accepting so anonymous browsers
    cannot subscribe to the live feed of student names, attendance marks,
    and guardian phone numbers.

    Close code 1008 = Policy Violation (RFC 6455 §7.4.1) — the standard
    code for authentication/authorisation failure on WebSocket.
    """
    payload = decode_access_token(token)
    if payload is None:
        await websocket.close(code=1008, reason="Invalid or expired token")
        return

    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected", "payload": {}})
        while True:
            # No inbound protocol yet — keep alive and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
'''

PR2_OPS = [("write", "services/api/app/ws/routes.py", WS_ROUTES_PY)]

PR2_BODY = """\
## What
Fixes issue **#6** — `GET /ws/events` accepted any anonymous WebSocket connection \
and streamed every school event in real time to anyone who connected: student \
attendance marks with names, document commits, guardian notifications with phone \
numbers.

### Changes
- `ws/routes.py`: added `token: str = Query(...)` parameter. The server calls \
`decode_access_token()` before `manager.connect()` and closes with WebSocket \
close code **1008 (Policy Violation)** on failure.

## Flutter client change needed
The WebSocket URL must append `?token=<jwt>` (same JWT used for REST calls). \
Find wherever `WebSocketChannel.connect` / `WebSocketChannel.fromUri` is called \
in `apps/admin/lib/core/ws_client.dart` and update:
```dart
// Before
final uri = Uri.parse('wss://shaala-os-api.onrender.com/ws/events');

// After
final uri = Uri.parse(
  'wss://shaala-os-api.onrender.com/ws/events?token=$accessToken',
);
```
"""


# ──────────────────────────────────────────────────────────────────────────────
# PR 3 — fix/upload-guards  (issue #5)
# /documents/upload had no file size cap, no MIME validation, no count limit.
# Fix: 10 MB per file, 5 files per request, MIME allowlist.
# ──────────────────────────────────────────────────────────────────────────────

UPLOAD_OLD = '''\
@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
) -> dict:
    documents = []
    for file in files:
        content = await file.read()
        document = process_upload(db, content, file.content_type or "application/octet-stream")
        documents.append(_summary(document))
        await manager.broadcast("document.uploaded", _summary(document))
    run_signals(db)
    await manager.broadcast("actions.updated", {})
    return {"documents": documents}'''

UPLOAD_NEW = '''\
# Upload limits — conservative defaults for a school document context.
_MAX_FILES_PER_REQUEST = 5
_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB per file
_ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


@router.post("/upload")
async def upload(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
) -> dict:
    if len(files) > _MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=413,
            detail=f"At most {_MAX_FILES_PER_REQUEST} files per request.",
        )

    documents = []
    for file in files:
        # Validate MIME type before reading the body — fail fast on obvious junk.
        if file.content_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"Unsupported file type '{file.content_type}'. "
                    f"Allowed: {', '.join(sorted(_ALLOWED_MIME_TYPES))}"
                ),
            )

        # Read in chunks and enforce the per-file size cap — never load an
        # unbounded file into RAM, and never fill Postgres with unlimited data.
        chunks: list[bytes] = []
        total = 0
        chunk_size = 64 * 1024  # 64 KB
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_FILE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"File '{file.filename}' exceeds the "
                        f"{_MAX_FILE_BYTES // (1024 * 1024)} MB limit."
                    ),
                )
            chunks.append(chunk)
        content = b"".join(chunks)

        document = process_upload(db, content, file.content_type)
        documents.append(_summary(document))
        await manager.broadcast("document.uploaded", _summary(document))

    run_signals(db)
    await manager.broadcast("actions.updated", {})
    return {"documents": documents}'''

PR3_OPS = [("replace", "services/api/app/routers/documents.py", UPLOAD_OLD, UPLOAD_NEW)]

PR3_BODY = """\
## What
Fixes issue **#5** — `POST /documents/upload` had no guards:
- No file size limit → could exhaust server RAM or fill Postgres
- No MIME type check → arbitrary file types passed to the image processor
- No per-request count limit → easy DoS via many concurrent large uploads

### Changes
- `documents.py`: added `_MAX_FILES_PER_REQUEST = 5`, `_MAX_FILE_BYTES = 10 MB`, \
and `_ALLOWED_MIME_TYPES` allowlist.
- Files are read in 64 KB chunks so the server never holds more than one file \
in memory at once. Size is checked incrementally; the connection is rejected \
mid-stream if the limit is exceeded.
- Returns `413 Request Entity Too Large` for size/count violations and \
`415 Unsupported Media Type` for unknown MIME types.
"""


# ──────────────────────────────────────────────────────────────────────────────
# PR 4 — fix/docker-hardening  (issues #9, #10)
# Postgres port 5432 exposed on host with trivial default password.
# Source code volume-mounted into the running container.
# ──────────────────────────────────────────────────────────────────────────────

DOCKER_COMPOSE = """\
services:
  db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-shaala}
      # Default password removed — must be set explicitly in .env.
      # The old default "shaala" made the database directly accessible to anyone
      # who could reach port 5432 with trivial credentials.
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-shaala}
    # No `ports:` mapping — Postgres must not be reachable from outside Docker.
    # The api container talks to it as db:5432 over the internal bridge network.
    # Exposing 5432 to the host lets any process (or network peer) connect
    # directly, bypassing the API layer entirely.
    volumes:
      - db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-shaala}"]
      interval: 5s
      timeout: 5s
      retries: 10

  api:
    build: ./services/api
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: ${DATABASE_URL}
    ports:
      - "8000:8000"
    # Source-code volume mount removed. The Dockerfile already COPYs the code
    # into the image at build time. Mounting ./services/api:/app was a dev
    # shortcut that let container writes overwrite host source files (and vice
    # versa). Use `docker compose up --build` to pick up code changes instead.
    depends_on:
      db:
        condition: service_healthy

volumes:
  db_data:
"""

PR4_OPS = [("write", "docker-compose.yml", DOCKER_COMPOSE)]

PR4_BODY = """\
## What
Fixes issues **#9** and **#10** from the security audit.

### #9 — Postgres port 5432 exposed on the host
`ports: - "5432:5432"` made the database directly reachable from outside \
Docker — with the default password `shaala`, anyone who could reach the \
host could connect directly to Postgres and bypass the API entirely.

**Fix:** `ports:` mapping removed from the `db` service. Containers in the same \
Compose stack communicate over the internal bridge network (`db:5432`); there is \
no need to expose Postgres externally.

The default `POSTGRES_PASSWORD=shaala` fallback is also removed — it must now be \
explicitly set in `.env`.

### #10 — Source code volume-mounted into the running container
`volumes: - ./services/api:/app` let container writes overwrite host source files \
and allowed any compromise of the running container to modify source code on disk.

**Fix:** volume mount removed. The `Dockerfile` already `COPY`s the code at build \
time. Run `docker compose up --build` to pick up local changes.

## Required action after merge
Set `POSTGRES_PASSWORD` to a strong value in your `.env` file before running \
`docker compose up`. The container will refuse to start if the variable is unset.
"""


# ──────────────────────────────────────────────────────────────────────────────
# PR 5 — fix/pyjwt-migration  (issue #11)
# python-jose is effectively unmaintained (last release 2022, open CVEs).
# Fix: replace with PyJWT 2.x (actively maintained).
# ──────────────────────────────────────────────────────────────────────────────

SECURITY_PY = '''\
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def qr_token_for(admission_no: str) -> str:
    """Shared by seed.py (initial students) and the admission_form commit path
    (Phase 3) so every student\'s QR token is derived the same, stable way."""
    # config.py\'s startup guard already ensured the secret is non-empty.
    key = settings.jwt_secret.encode()
    return hmac.new(key, admission_no.encode(), hashlib.sha256).hexdigest()[:20]


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(subject: dict[str, Any]) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {**subject, "exp": expire}
    # PyJWT 2.x encode() returns str directly (not bytes).
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except pyjwt.PyJWTError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """FastAPI dependency — injected into every route that requires a logged-in user.

    Or once at router level (applies to all routes in the file)::

        router = APIRouter(..., dependencies=[Depends(get_current_user)])
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
'''

PR5_OPS = [
    # Swap python-jose for PyJWT in requirements
    ("replace",
     "services/api/requirements.txt",
     "python-jose[cryptography]==3.5.0",
     "PyJWT==2.10.1"),

    # Full rewrite of security.py with PyJWT API
    ("write", "services/api/app/security.py", SECURITY_PY),
]

PR5_BODY = """\
## What
Fixes issue **#11** — `python-jose` is effectively unmaintained (last PyPI \
release November 2022, open security issues, no active maintainer).

### Changes
- `requirements.txt`: replaced `python-jose[cryptography]==3.5.0` with \
`PyJWT==2.10.1` (actively maintained, widely used, no known vulnerabilities).
- `security.py`: updated import (`import jwt as pyjwt`) and call sites:
  - `jwt.encode(...)` → `pyjwt.encode(...)` (PyJWT 2.x returns `str`, not bytes)
  - `jwt.decode(...)` → `pyjwt.decode(...)`
  - `except JWTError` → `except pyjwt.PyJWTError`

No behaviour change — same HS256 algorithm, same token format, same claims. \
Existing tokens issued by python-jose are compatible.

## Note on requirements.txt conflict
If `fix/api-hardening` is merged first (it adds `slowapi` to requirements.txt), \
resolve the conflict by keeping both `PyJWT==2.10.1` and `slowapi==0.1.9` in the \
file.
"""


# ──────────────────────────────────────────────────────────────────────────────
# PR 6 — fix/api-hardening  (issues #4, #7, #13)
# Issue #4:  CORS wildcard fallback (allow_origins=cors_origins or ["*"])
# Issue #7:  No rate limiting on login or the CPU-heavy timetable solver
# Issue #13: Missing security response headers
# ──────────────────────────────────────────────────────────────────────────────

LIMITER_PY = '''\
"""Central slowapi limiter instance.

Imported by main.py (to register with the app) and by individual routers
(to apply per-endpoint limits). Keeping it in its own module avoids circular
imports: main.py imports routers which import the limiter — fine as long as
the limiter itself doesn\'t import from main.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
'''

MAIN_PY = '''\
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
    # Run once at startup too, so the Action Center isn\'t stale for up to 30s
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

    # Prevent browser caching — this app\'s live-update model depends on every
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

    # Referrer policy — don\'t leak the full URL in the Referer header when
    # the app links to third-party resources.
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # CSP — restrict where the browser may load resources from.
    # Flutter web requires unsafe-inline for both scripts and styles.
    # Adjust connect-src if you add third-party API calls in future phases.
    response.headers["Content-Security-Policy"] = (
        "default-src \'self\'; "
        "script-src \'self\' \'unsafe-inline\'; "
        "style-src \'self\' \'unsafe-inline\'; "
        "img-src \'self\' data: blob:; "
        "connect-src \'self\' wss:; "
        "frame-ancestors \'none\';"
    )

    return response


app.include_router(health.router)
app.include_router(auth.router)
# attendance before people: both declare a /students/... path, and FastAPI
# matches in registration order, not by specificity. attendance\'s literal
# /students/id-cards.pdf must be tried before people\'s parameterised
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
'''

AUTH_OLD = '''\
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.db.session import get_db
from app.schemas import LoginRequest, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])'''

AUTH_NEW = '''\
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.db.session import get_db
from app.limiter import limiter
from app.schemas import LoginRequest, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])'''

AUTH_LOGIN_OLD = '''\
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_for_user(user)'''

AUTH_LOGIN_NEW = '''\
@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # brute-force / credential-stuffing guard
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_for_user(user)'''

TIMETABLE_IMPORTS_OLD = '''\
from fastapi import APIRouter, Depends, HTTPException'''

TIMETABLE_IMPORTS_NEW = '''\
from fastapi import APIRouter, Depends, HTTPException, Request'''

TIMETABLE_LIMITER_OLD = '''\
from app.security import get_current_user'''

TIMETABLE_LIMITER_NEW = '''\
from app.limiter import limiter
from app.security import get_current_user'''

TIMETABLE_GENERATE_OLD = '''\
@router.post("/generate")
def generate(payload: GenerateRequest, db: Session = Depends(get_db)) -> dict:'''

TIMETABLE_GENERATE_NEW = '''\
@router.post("/generate")
@limiter.limit("2/minute")  # CP-SAT solver runs up to 8 s; limit concurrent calls
def generate(request: Request, payload: GenerateRequest, db: Session = Depends(get_db)) -> dict:'''

PR6_OPS = [
    # New file: central limiter module
    ("write", "services/api/app/limiter.py", LIMITER_PY),

    # Full rewrite of main.py (CORS guard + security headers + limiter setup)
    ("write", "services/api/app/main.py", MAIN_PY),

    # Add slowapi to requirements
    ("replace",
     "services/api/requirements.txt",
     "apscheduler==3.11.3",
     "apscheduler==3.11.3\nslowapi==0.1.9"),

    # auth.py: add rate limit to login
    ("replace", "services/api/app/routers/auth.py", AUTH_OLD, AUTH_NEW),
    ("replace", "services/api/app/routers/auth.py", AUTH_LOGIN_OLD, AUTH_LOGIN_NEW),

    # timetable.py: add rate limit to generate
    ("replace", "services/api/app/routers/timetable.py", TIMETABLE_IMPORTS_OLD, TIMETABLE_IMPORTS_NEW),
    ("replace", "services/api/app/routers/timetable.py", TIMETABLE_LIMITER_OLD, TIMETABLE_LIMITER_NEW),
    ("replace", "services/api/app/routers/timetable.py", TIMETABLE_GENERATE_OLD, TIMETABLE_GENERATE_NEW),
]

PR6_BODY = """\
## What
Fixes issues **#4**, **#7**, and **#13** — three separate hardening concerns all \
touching `main.py`, bundled to avoid merge conflicts.

### #4 — CORS wildcard fallback removed
`allow_origins=settings.cors_origins or ["*"]` silently fell back to `["*"]` \
when `CORS_ORIGINS` was unset. Now raises `RuntimeError` at startup instead, \
ensuring misconfigured deployments fail loudly rather than opening all origins.

### #7 — Rate limiting added
New `app/limiter.py` module holds a `slowapi.Limiter` instance. Registered in \
`main.py` and applied to:
- `POST /auth/login` → **10 requests / minute / IP** (brute-force guard)
- `POST /timetable/generate` → **2 requests / minute / IP** (CP-SAT solver runs \
  up to 8 s; concurrent floods can DoS the server)

`slowapi==0.1.9` added to `requirements.txt`.

### #13 — Security response headers
The `no_store_middleware` is extended (renamed `security_headers_middleware`) to \
also set:
| Header | Purpose |
|---|---|
| `X-Content-Type-Options: nosniff` | Prevent MIME-sniffing attacks |
| `X-Frame-Options: DENY` | Prevent clickjacking via iframe |
| `Strict-Transport-Security` | Force HTTPS for 1 year |
| `Referrer-Policy` | Don't leak full URL to third parties |
| `Content-Security-Policy` | Restrict resource loading origins |

## Note on conflict with fix/pyjwt-migration
Both PRs touch `requirements.txt`. If merged after `fix/pyjwt-migration`, \
keep both `PyJWT==2.10.1` and `slowapi==0.1.9` in the file.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

PULL_REQUESTS = [
    {
        "branch": "fix/demo-reset-protection",
        "title": "security: protect POST /demo/reset with X-Reset-Key secret header",
        "body": PR1_BODY,
        "ops": PR1_OPS,
    },
    {
        "branch": "fix/websocket-auth",
        "title": "security: require JWT token on WebSocket /ws/events connection",
        "body": PR2_BODY,
        "ops": PR2_OPS,
    },
    {
        "branch": "fix/upload-guards",
        "title": "security: add 10 MB size cap, MIME allowlist, and 5-file limit on /documents/upload",
        "body": PR3_BODY,
        "ops": PR3_OPS,
    },
    {
        "branch": "fix/docker-hardening",
        "title": "security: remove exposed Postgres port and source-code volume mount from docker-compose",
        "body": PR4_BODY,
        "ops": PR4_OPS,
    },
    {
        "branch": "fix/pyjwt-migration",
        "title": "security: replace unmaintained python-jose with PyJWT 2.10.1",
        "body": PR5_BODY,
        "ops": PR5_OPS,
    },
    {
        "branch": "fix/api-hardening",
        "title": "security: remove CORS wildcard, add rate limiting, add security response headers",
        "body": PR6_BODY,
        "ops": PR6_OPS,
    },
]


if __name__ == "__main__":
    username = get_username()
    preflight(username)

    for pr_def in PULL_REQUESTS:
        make_pr(
            branch=pr_def["branch"],
            title=pr_def["title"],
            body=pr_def["body"],
            ops=pr_def["ops"],
            username=username,
        )

    print("\n" + "=" * 70)
    print("  All 6 PRs raised!")
    print("=" * 70)
    print(f"""
Review them at: https://github.com/{OFFICIAL_REPO}/pulls

Post-merge checklist:
  1. Generate DEMO_RESET_KEY and add to Render + GitHub Actions:
       python -c "import secrets; print(secrets.token_hex(32))"

  2. Set CORS_ORIGINS in Render to your Vercel URL:
       CORS_ORIGINS=https://shaala-os.vercel.app

  3. Set POSTGRES_PASSWORD (non-default) in Render / .env

  4. Update Flutter WebSocket URL to include ?token=<jwt>
     File: apps/admin/lib/core/ws_client.dart
""")

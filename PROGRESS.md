# Progress

Tracked by phase (PROMPT.md §9), not by calendar date. Updated at the end of every
phase, per CLAUDE.md.

## Current phase: 1 — Foundation & public URL — **gate passed**

## Done
- Repo scaffolded per PROMPT.md §4. Public GitHub repo: https://github.com/arunishrajput/shaala-os
- Docker Compose (Postgres 16 + FastAPI), `Makefile` with a real `verify` gate
  (ruff, mypy, pytest, flutter analyze, flutter build web).
- Full SQLAlchemy 2.0 data model (§5), one Alembic migration, `seed.py` with a
  fixed RNG seed: 12 sections, 40 teachers (3 deliberately tight), 600 students,
  12 rooms, 48 time slots, 90 days of textured attendance history (46,200 records:
  Monday dips, a festival dip, a flu week in 8-A, 6 students trending toward the
  75% cliff), 3 open ActionItems, 2 pending documents, 1 unresolved absence.
- JWT auth + `POST /auth/demo-login?role=admin|teacher|parent` (3 fixed demo
  accounts, per CLAUDE.md's auth boundary).
- Minimal `/ws/events` WebSocket (connection + broadcast plumbing; no domain
  events yet — those start in Phase 3/4 once there's something to broadcast).
- Flutter web shell: slate/indigo theme, nav rail (responsive to bottom nav under
  700px), go_router with auth redirect, hand-written Riverpod providers only (no
  codegen), dio `api_client` + WS-backed `eventStreamProvider`, read-only People
  screens (teachers list, class list, per-class student roster).
- CI (`.github/workflows/ci.yml`): ruff + flutter analyze on push/PR.
- **Deployed**: Neon Postgres 16 (`shaala-os`, us-west-2) · Render web service
  `shaala-os-api` (Oregon, Docker, free plan) · Vercel static hosting for the
  Flutter web build. Production seeded with the same fixed data as local.

## Stubbed (visible in the UI, honest "not built yet" states)
- Timetable, Documents, Attendance, Staffing screens — placeholder screens naming
  the phase they arrive in.
- Dashboard shows real teacher/class counts but not the Action Center (Phase 4).
- People screens are read-only by design (edit/create forms deliberately deferred
  past Phase 1 — not a judged moat feature, see the Phase 1 plan's scope trim).

## Broken
- (none)

## Known gaps / manual follow-ups
- Gate text says "verified from a phone on mobile data" — verified instead via
  desktop browser automation against the live URL (WSS connects, data loads, no
  console errors). A real mobile-network check is still worth doing before Phase 6.
- Render's `render` CLI has no command to update env vars on an existing service
  (only at creation) and one-off Jobs require a paid plan — worked around via
  `--pre-deploy-command` (now reset to just `alembic upgrade head` for future
  deploys). `POST /demo/reset` (Phase 4) will be the real fix for reseeding prod.
- Seeding a remote DB from this environment over `docker compose run` hit two real
  issues, now fixed in `seed.py`: (1) relying on the driver's default executemany
  for the ~46k-row attendance insert was pathologically slow over a high-latency
  link — fixed with explicit chunked multi-row `VALUES` inserts; (2) the whole
  seed was one giant transaction, so a slow/killed attendance insert rolled back
  *everything*, including the fast core data — fixed by committing core people
  data (schools/teachers/students/etc.) before the slow attendance load.

## Next 3 tasks (Phase 2 — the solver)
1. CP-SAT model in `services/api/app/services/timetable/solver.py` + `/timetable/generate`.
2. Grid UI with class/teacher switcher, explain panel, drag-and-drop with live
   validation and ranked alternatives.
3. `docs/solver.md` written for real while the model is fresh.

---

## Phase log

### Phase 1 — Foundation & public URL — ✅ gate passed
Gate: `make verify` exits 0 ✅ · `curl https://shaala-os-api.onrender.com/health`
returns 200 ✅ · the deployed web app (https://shaala-os.vercel.app) loads seeded
students live over `wss://` ✅ (see "known gaps" above re: mobile-data check).

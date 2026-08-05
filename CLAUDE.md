# CLAUDE.md — operating rules for this repo
<!-- Keep this file under 150 lines. It is loaded into context on EVERY session.
     The full spec lives in PROMPT.md — read it once at the start of a phase, not every turn. -->

## Project
**Shaala OS** — school operations platform. Submission for PaperBuddy EduHack ("Hack the Web").
Full spec: `PROMPT.md`. Current state: `PROGRESS.md`. Video script: `DEMO_SCRIPT.md`.

## Non-negotiables
1. **Work in numbered phases (PROMPT.md §8), never in calendar days.** State the phase at the
   start of every session. You have no reliable sense of elapsed time between sessions.
2. **Do not start phase N+1 until `make verify` passes and you've updated `PROGRESS.md`.**
3. **Never break the demo.** Every commit leaves `make demo` working.
4. **Never invent an API.** If unsure how a package works, read the installed source
   (`.venv/lib/python3.11/site-packages/...`, `~/.pub-cache/...`) or its docs. Do not guess
   method names, constructor args, or model IDs.
5. **Never hardcode secrets or model IDs.** They go in `.env`; `.env.example` is committed.
6. **Stub loudly, never silently.** A stub raises `NotImplementedError` or renders a visible
   "Not built yet" state, and gets a line in `PROGRESS.md`. Never fake a working feature.
7. **If blocked >10 minutes, stub it, log it, move on.** Report the block; don't spin.

## Verification — the definition of done
Nothing is "done" until this exits 0:
```
make verify     # ruff + mypy(light) + pytest + flutter analyze + build_web
```
Run it before every commit. If you claim something works, you have run it.
Never report success from reading code alone.

## Working style
- **Vertical slices only.** DB → API → provider → widget → visible on screen. Never build
  three backend layers before anything renders.
- **One feature per commit.** Message format: `phase-N: <what a judge would call it>`.
- Prefer targeted edits over rewriting files. Don't echo large files back into chat.
- Keep responses short. Show diffs and command output, not narration.
- Before each phase: print a ≤10-line plan. After each phase: run `make verify`, update
  `PROGRESS.md`, commit, state the next phase.

## Stack facts (do not drift)
- Backend: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL 16. Python 3.11.
- Solver: OR-Tools CP-SAT. Never a greedy/random scheduler.
- Frontend: Flutter Web + **Riverpod 2.x, manual providers only — NO riverpod_generator,
  NO build_runner codegen for providers.** freezed is used ONLY for data models.
- Realtime: one WebSocket at `/ws/events` → `StreamProvider` → providers self-invalidate.
- No `setState` for server data, ever. `AsyncValue.when` everywhere.
- Prod deps stay light: no dlib, no face_recognition, no torch, no sklearn. See PROMPT.md §3.

## Out of scope — do not build (PROMPT.md §2 explains why)
Fee management · LMS / course content · exam paper generation · payment gateways ·
multi-tenancy · i18n · settings pages · dark-mode toggle · RFID/IoT/firmware ·
UI unit tests · auth beyond JWT + 3 demo logins.

## Files you own and must keep current
- `PROGRESS.md` — done / stubbed / broken / next 3 tasks. Update at the end of every phase.
- `README.md` — a graded deliverable from Phase 1, not written at the end.
- `DEMO_SCRIPT.md` — the video script; refine each phase.
- `docs/solver.md` — the constraint model in prose. Write it in Phase 2 while it's fresh.

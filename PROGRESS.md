# Progress

Tracked by phase (PROMPT.md §9), not by calendar date. Updated at the end of every
phase, per CLAUDE.md.

## Current phase: 1 — Foundation & public URL

## Done
- Repo scaffolded per PROMPT.md §4.
- Git repo initialized, public GitHub repo created: https://github.com/arunishrajput/shaala-os

## Stubbed
- (none yet)

## Broken
- (none yet)

## Next 3 tasks
1. Docker Compose + Makefile with a real `verify` target.
2. Backend skeleton: `/health`, full data model, one Alembic migration, `seed.py`.
3. Flutter shell (theme, nav rail, router, api/ws clients) + deploy plumbing.

---

## Phase log

### Phase 1 — Foundation & public URL (in progress)
Gate: `make verify` exits 0 **and** `curl https://<prod>/health` returns 200 **and**
the deployed web app loads seeded students over `wss://` from a phone on mobile data.

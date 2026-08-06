# Progress

Tracked by phase (PROMPT.md §9), not by calendar date. Updated at the end of every
phase, per CLAUDE.md.

## Current phase: 2 — The solver — **gate passed**

## Done
- **Phase 1** — foundation, deploy plumbing, Flutter shell, People screens. See
  phase log below.
- **Phase 2** — CP-SAT timetable solver (`services/timetable/solver.py`): full
  hard-constraint set from PROMPT.md §6.2, weighted soft objective (idle gaps,
  spread, heavy-early, preferred slots, balance), `POST /timetable/generate`
  persisting a new `TimetableVersion` + `TimetableEntry` rows.
- Explain-any-cell (`explain.py`): rules-based room/roster reasons, ranked
  alternatives with real costs, and a genuine re-solve-with-cell-forbidden
  objective diff — cached per entry. `GET /timetable/explain/{id}`.
- Drag-and-drop validation (`POST /timetable/validate-move`, `POST
  /timetable/move`): real conflict detection (room type/capacity, teacher
  availability/caps, double-booking) with ranked alternatives on conflict.
- Substitute repair algorithm (`substitute.py`): minimal-perturbation
  candidate ranking + `apply_substitution` cloning a new version with only the
  absent teacher's periods reassigned. Algorithm + tests only — wiring into
  `/timetable/absence` and the Action Center is Phase 4 by design (see
  `docs/solver.md`'s scope note).
- Flutter timetable grid: class/teacher switcher, live solver-stats banner,
  drag-and-drop with a red-toast conflict path, explain side panel.
- `tests/test_solver.py` — all 5 PROMPT.md §6.2 assertions green, plus a timing
  test (full solve < 10s). 9/9 backend tests passing.
- `docs/solver.md` written for real: variables, every constraint, why CP-SAT,
  the time-budget quality tradeoff, and two real bugs found and fixed via the
  solver's own infeasibility pre-checks (lab capacity < class strength; lab
  demand exceeding lab supply once room count was fixed at 3 per PROMPT.md §5).
- Production redeployed and reseeded with the corrected data.

## Stubbed (visible in the UI, honest "not built yet" states)
- Documents, Attendance, Staffing screens — placeholder screens naming the
  phase they arrive in.
- Dashboard shows real counts but not the Action Center (Phase 4).
- People screens are read-only by design (Phase 1 scope trim).
- `/timetable/absence`, `/timetable/substitute`, notification drafts — the
  substitute *algorithm* is built and tested; the live demo wiring is Phase 4.

## Broken
- **`POST /timetable/generate` fails on the deployed production URL.** Works
  reliably locally (~8s, verified repeatedly via `make verify` and manual
  testing) but Render's free-tier instance (512MB RAM) can't complete a solve
  of this size (~30k CP-SAT variables including the soft-objective auxiliaries)
  — diagnostic added to the API response shows `num_branches: 0` even after a
  25s budget, meaning it's stalling before search even starts, not just
  running slow. Points at memory pressure during presolve, not CPU. Explored:
  capping solver worker threads to available cores (didn't help — same result
  at 8 vs. fewer workers), raising the time budget via `SOLVER_TIME_LIMIT_S`
  env var (didn't help — still 0 branches at 25s). Root-caused but not yet
  fixed; the Flutter UI degrades gracefully (shows the failure reason in a red
  banner, per `_StatsBanner`) rather than hanging or crashing, so this doesn't
  break the deployed app, it just means the "Generate" button doesn't work on
  the live URL yet. Decided to defer further work on this to Phase 5/6
  (demo-hardening) rather than keep spending Phase 2 time on infra tuning —
  options on the table: upgrade Render's plan, or shrink the CP-SAT model
  (the soft-objective's idle-gap/balance terms add several thousand auxiliary
  variables per `docs/solver.md` — the likely first place to cut).

## Known gaps / manual follow-ups
- Phase 1's "verified from a phone on mobile data" gate item — still only
  checked via desktop browser automation. Worth doing for real before Phase 6.
- Explain's full re-solve-with-forbidden-cell (~6-8s) re-solves the *entire*
  timetable, not just the one entry frozen-except-itself — disclosed in
  `docs/solver.md`, not hidden. The fast ranked-alternatives path used for the
  actual UI suggestions doesn't have this cost. This path is *also* affected by
  the production memory issue above, so the explain panel's re-solve-diff
  section won't populate on the deployed URL either — the rules-based reasons
  and ranked alternatives (the fast, non-solving paths) still work fine.
- CP-SAT's 8s default time budget returns `FEASIBLE` (zero hard violations,
  gate-compliant) but rarely `OPTIMAL` — soft-constraint quality is
  time-bounded, documented in `docs/solver.md` with real numbers. (Local only —
  see the Broken item above for the separate production issue.)

## Next 3 tasks (Phase 3 — the AI reader)
1. `VisionProvider` interface (`gemini` + `fixture` backends) — verify the
   current Gemini model ID before use, never hardcode one from memory.
2. Document upload (single/bulk/camera/"Try a sample") → preprocess → extract
   → `Document`/`ExtractedField` rows → review UI with bbox overlay and
   confidence highlighting → commit → real `Student`/`AttendanceRecord` rows.
3. Fixtures for all 4 doc types captured so `VISION_PROVIDER=fixture` works
   with the network disabled (the Phase 3 gate's literal requirement).

---

## Phase log

### Phase 1 — Foundation & public URL — ✅ gate passed
Gate: `make verify` exits 0 ✅ · `curl https://shaala-os-api.onrender.com/health`
returns 200 ✅ · the deployed web app (https://shaala-os.vercel.app) loads seeded
students live over `wss://` ✅ (see "known gaps" re: mobile-data check).

### Phase 2 — The solver — ✅ gate passed
Gate: `pytest tests/test_solver.py` green, all 5 §6.2 assertions ✅ · a full
solve (372 periods across 12 classes) completes in ~8s, zero hard violations ✅.

# Progress

Tracked by phase (PROMPT.md §9), not by calendar date. Updated at the end of every
phase, per CLAUDE.md.

## Current phase: 4 — The intelligence — **gate passed**

## Done
- **Phase 1** — foundation, deploy plumbing, Flutter shell, People screens.
- **Phase 2** — CP-SAT timetable solver, explain-any-cell, drag-and-drop
  validation, substitute repair algorithm. See phase log below.
- **Phase 4** — the proactive layer (`services/signals/`, `services/staffing/`,
  `services/notifications.py`, `services/id_cards.py`):
  - Signal engine: a registry of pure functions over real DB state (not canned
    text) reconciled against open `ActionItem` rows — create what's new,
    refresh what's still true, auto-resolve what stopped being true. Six
    rules: `uncovered_classes` (unresolved `TeacherAbsence` + active
    timetable), `low_attendance_trend` (rolling 7-day window per student),
    `documents_need_review`, `staffing_shortfall` (feeds off the new
    forecast), `room_conflict`, `free_periods` (flags a class only when it
    has *more* free periods than its least-free peer — an absolute threshold
    fired identically for all 12 classes at first, since every section
    shares the same structural slack by design). Runs on a 30s APScheduler
    tick and immediately after every mutation that can change a signal
    (document commit/reject, absence marked, substitute assigned, demo
    reset) — the tick alone would blow the gate's timing budget.
  - This retired the 3 hand-written `ActionItem` rows and 2 placeholder
    `Document` rows `seed.py` carried since Phase 1 as dashboard-filler —
    the real engine now computes genuine equivalents within moments of
    seeding.
  - Substitute engine wired end to end: `POST /timetable/absence` (get-or-
    create per teacher+date, idempotent) and `POST /timetable/substitute`,
    closing the "deliberately not built here" note `substitute.py` carried
    since Phase 2. Re-keyed on `(class_id, slot_id)` instead of `entry_id` —
    each successful assignment clones the whole active `TimetableVersion`,
    so an `entry_id` from the initial uncovered-periods listing is already
    stale by the second assignment in a multi-period absence (the actual
    Mrs. Rao case). `TeacherAbsence.resolved` flips once every period that
    day is covered, which is what lets the Action Center card auto-resolve.
  - Notification Outbox: real `Notification` rows, drafted (never sent — no
    SMS/WhatsApp provider, correctly out of scope) on "Draft parent
    messages" and on a completed substitute assignment ("teachers
    notified"). Drafting is a deliberate acknowledgment, not a claim the
    underlying condition is fixed — the card can legitimately reopen next
    tick if the attendance number hasn't moved.
  - Staffing forecast (`services/staffing/forecast.py`): per-department EWMA
    + day-of-week seasonal baseline over `TeacherAbsence` history. Needed 90
    days of that history seeded — it didn't exist before (Phase 1 only
    seeded student attendance) — textured with a Mathematics-department
    spike inside the last 30 days so the backtest has a real seasonal
    signal to find. Backtest reports a skill score against a naive
    flat-average baseline rather than raw "1 − MAE/mean", which reads as
    ~0% on this sparse count data even when the model is genuinely
    informative.
  - Attendance: `POST /attendance/scan` (QR, dedupes to "already marked"
    rather than a second row or an error), `POST /attendance/manual`,
    `GET /attendance/today`, `GET /attendance/student/{id}/summary`,
    `GET /students/id-cards.pdf` (reportlab + qrcode, real students, real
    QR tokens, printable grid). `POST /attendance/group-photo` is a loud
    501 stub — PROMPT.md §6.4B's optional stretch, not built this session.
  - `POST /demo/reset` — reseeds in a thread (doesn't block the event loop),
    clears the explain cache, re-runs signals, broadcasts `demo.reset`.
    Measured 3.87s locally against the 15s §11 budget.
  - Flutter: Action Center card stack on the Dashboard (severity dot, one
    line of evidence, one primary button, optimistic resolve/dismiss) with
    a live open-item badge on the header bell; a substitute-assignment
    dialog reachable both from that card and from a new per-teacher "Mark
    absent" action on the People screen (there was no UI path to actually
    *create* an absence before this); an Outbox panel on the Dashboard;
    Attendance screen (Kiosk tab with `mobile_scanner`, live feed, counter,
    graceful no-camera placeholder; Manual roll call tab); Staffing screen
    (forecast cards + `fl_chart` backtest line chart); a header "Reset demo
    data" button (confirm → progress dialog → full page reload, since a
    fresh seed mints new primary keys everywhere and nothing short of a
    reload can guarantee the UI isn't holding a stale id).
  - Found and fixed two demo-stability/architecture issues before they
    shipped: (1) the signal engine and forecast initially used
    `date.today()` for "today," but all seeded history is anchored to a
    fixed `ANCHOR_DATE` — wall-clock today would have made results drift
    daily and stop matching the recorded demo video. Centralized
    `DEMO_ANCHOR_DATE` in `config.py`. (2) `make verify` never regenerated
    `.freezed.dart`/`.g.dart` (correctly gitignored as generated code),
    only ever passing locally because old `build_runner` output happened to
    still be on disk — a genuinely fresh clone would have failed
    `flutter analyze` immediately. CI already did this correctly; the local
    gate hadn't. Verified the fix by deleting every generated file and
    re-running `make verify` clean.
  - Found and fixed a real routing bug: `/students/id-cards.pdf` 404'd
    because `people.router`'s `/students/{student_id}` was registered first
    and FastAPI matches in registration order, not by specificity —
    `"id-cards.pdf"` int-parsed against `{student_id}` and failed before
    ever reaching the literal route.
  - `tests/test_signals.py`, `test_staffing.py`, `test_absence.py`,
    `test_notifications.py`, `test_attendance.py`, `test_staffing_router.py`,
    `test_demo_reset.py` — 38 backend tests total, 1 skipped (a
    kind-availability check that depends on tick ordering), all passing.
- **Phase 3** — the document pipeline (`services/vision/`, `services/documents.py`):
  - `VisionProvider` interface with `FixtureProvider` (hash-keyed replay, zero
    network calls) and `GeminiProvider` (`generateContent` REST API, verified
    against current docs — model `gemini-3.6-flash`, checked 2026-08-06, not
    guessed). Any Gemini failure auto-falls back to fixture with a logged
    warning, per PROMPT.md §6.1's demo-safety requirement.
  - Preprocessing (`preprocess.py`): real deskew (Otsu threshold + minAreaRect)
    and CLAHE contrast enhancement, opencv-headless only.
  - 4 programmatically-generated sample documents (`fixtures/generate_fixtures.py`
    + `fixtures/samples/`) with pixel-accurate bounding boxes captured at draw
    time — no real scanned forms exist for this project, so these exercise the
    full pipeline honestly rather than faking OCR difficulty.
  - `Document`/`ExtractedField` persistence with confidence-based
    `needs_review` routing (< 0.85). Table rows flatten into `row{i}.{key}`
    `ExtractedField` entries so corrections work uniformly for both plain
    fields and table cells; `read_fields()` reconstructs the table on read.
  - `POST /documents/upload|samples/{type}`, `GET /documents`, `GET
    /documents/{id}`, `POST /documents/{id}/commit|reject`.
  - Commit mapping per doc type: `admission_form` → real `Student` row (shared
    `qr_token_for` with `seed.py`, extracted to `security.py`);
    `attendance_sheet` → `AttendanceRecord` rows resolved by class+roll_no
    against real seeded students; `leave_application` → `TeacherAbsence`
    resolved by teacher code; `marks_sheet` → archived only, no target table
    (Shaala OS deliberately doesn't store grades, PROMPT.md §2) — the warning
    explaining this is generated into the fixture itself, so a judge sees it
    in the review UI, not just in this file.
  - WebSocket broadcast on upload/commit (found and fixed a real bug: raw
    `json.dumps()` can't serialize `datetime` — switched to
    `jsonable_encoder`).
  - Flutter Documents screen: file upload, bulk upload with a real per-file
    progress list (not simulated — each file is a separate request), "Try a
    sample" chips, status filter. Review panel: image + bbox overlay drawn
    from the field's real coordinates on focus, amber styling + confidence %
    for low-confidence fields (sorted to lead the tab order), editable
    top-level fields, read-only table view for row data, commit/reject.
  - Dashboard's "Students" counter now listens for `document.committed` and
    self-invalidates (PROMPT.md §7.3's own pattern), with an `AnimatedSwitcher`
    fade per §7.4 — verified live end-to-end in the browser: committed a
    sample admission form on the Documents screen, the Dashboard's count
    updated 600 → 601 without a manual refresh.
  - `tests/test_documents.py` — 8 tests: the Phase 3 gate's literal timing
    requirement, confidence routing, all 4 doc-type commit paths, corrections
    applied before commit, double-commit rejection, graceful handling of an
    unrecognized image. 17/17 backend tests passing.

## Stubbed (visible in the UI, honest "not built yet" states)
- Group-photo attendance (`POST /attendance/group-photo`) — PROMPT.md §6.4B's
  optional stretch, gated on "only if Phase 4 is comfortably ahead." Returns
  a clear 501 with an explanation rather than a silent no-op; QR scan and
  manual roll call are the supported paths.
- People screens are read-only by design (Phase 1 scope trim), except the new
  per-teacher "Mark absent" action (Phase 4).
- Table row cells (attendance/marks sheets) are read-only in the review UI —
  only top-level fields are correctable this phase. Backend already supports
  per-cell correction (each cell is its own `ExtractedField`); the UI just
  doesn't expose it yet. Named as a real limitation, not hidden.
- Camera capture uses the browser's native file-input camera integration (how
  mobile browsers already offer "Camera / Photo Library / Files" on an
  `accept="image/*"` input) rather than an in-app embedded camera view.
- `GeminiProvider` is fully implemented and code-verified against current API
  docs but has not been exercised against the live Gemini API in this session
  — no key was provided to the assistant (correctly — the user manages their
  own key locally and on Render). `VISION_PROVIDER=fixture` is what's actually
  been run and tested.

## Broken
- **`POST /timetable/generate` fails on the deployed production URL** (Phase 2
  finding, still open). Works reliably locally; Render's free-tier RAM can't
  fit the solve. Root-caused, not fixed — deferred to Phase 5/6 per an
  explicit decision, see the Phase 2 entry below for detail.

## Known gaps / manual follow-ups
- Phase 1's "verified from a phone on mobile data" gate item — still only
  checked via desktop browser automation.
- Explain's full re-solve-with-forbidden-cell and `/timetable/generate` itself
  are both affected by the production memory issue above; the document
  pipeline is unaffected and now verified live in production (see Phase 3
  log entry above for the free-tier pre-deploy-command gap this uncovered).
- The Staffing screen's backtest chart and the header "Reset demo data"
  button were verified statically only (`flutter analyze` clean,
  `flutter build web` succeeds, backend endpoints curl-verified with sane
  data) — browser click automation stopped responding partway through this
  session (confirmed broken against a plain external page too, not this
  app's code) and hadn't recovered by the time Phase 4 shipped. Every other
  Phase 4 feature (Action Center, substitute assignment, notifications,
  attendance kiosk/manual/ID-cards) was verified live in the browser.
  Worth a five-minute visual pass next session.

## Next 3 tasks (Phase 5 — feature freeze & bug bash)
1. Live-verify the Staffing chart and the Reset demo data button (see known
   gap above) now that a fresh session should have working browser tooling.
2. Full walk of the judge's path: every empty state, every error state,
   every loading skeleton, mobile responsiveness — PROMPT.md §9's Phase 5
   gate ("no dead ends, no raw exception strings, nothing that only works if
   you click in the right order").
3. Revisit the Phase 2 production solver RAM gap and the Phase 5/6-deferred
   §6.6 stretch items (Principal's Weekly Briefing, Ask Shaala) only if
   Phase 5 finishes with room to spare — PROMPT.md's own hard rule is that a
   flawless five-feature product beats a shaky eight.

---

## Phase log

### Phase 1 — Foundation & public URL — ✅ gate passed
Gate: `make verify` exits 0 ✅ · `curl https://shaala-os-api.onrender.com/health`
returns 200 ✅ · the deployed web app (https://shaala-os.vercel.app) loads seeded
students live over `wss://` ✅ (see "known gaps" re: mobile-data check).

### Phase 2 — The solver — ✅ gate passed (locally) · ⚠️ production gap open
Gate: `pytest tests/test_solver.py` green, all 5 §6.2 assertions ✅ · a full
solve (372 periods across 12 classes) completes in ~8s, zero hard violations,
**on standard dev/CI hardware** ✅. Render's free-tier instance can't complete
the same solve (see Broken, above) — explicitly deferred to Phase 5/6.

### Phase 3 — The AI reader — ✅ gate passed
Gate: with `VISION_PROVIDER=fixture` (no network calls in that code path — not
just "network disabled," structurally incapable of making one), a sample
admission form becomes a real `Student` row in well under the 15s budget
(measured consistently under 1s locally) ✅. Verified via `pytest` and, live,
in the browser against **both** the local stack and the deployed production
URL (`shaala-os.vercel.app` / `shaala-os-api.onrender.com`): committed a
sample admission form (601st student, dashboard ticked 600→601 live over WS)
and a sample leave application (correctly routed to `TeacherAbsence`, student
count unchanged) directly against production.

**Deploy runbook correction, found while shipping this phase:** Render's free
tier silently skips `preDeployCommand` — the deploy log says so explicitly
("Predeploy command not run. Commands can only run on paid instance types"),
it isn't just slow or hidden. The `alembic upgrade head` pre-deploy command
configured on the service has therefore never actually been running.
`services/api/tests` never caught this because they run against the
Docker-composed local Postgres, not prod. Migration `7724d77e9a26` (this
phase's `original_url` → `Text` column widen) had to be applied by hand:
`docker compose run --rm -e DATABASE_URL=<neon-prod-url> --no-deps api alembic
upgrade head`, using `neonctl connection-string` to get the URL. **Every
future phase that adds a migration must do this manually after pushing** —
there is no free-tier auto-migration path. Worth revisiting if the Render
plan is ever upgraded (Phase 5/6 territory, alongside the solver RAM issue).

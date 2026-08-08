# Progress

Tracked by phase (PROMPT.md §9), not by calendar date. Updated at the end of every
phase, per CLAUDE.md.

## Current phase: 6 — Artifacts & ship — **in progress**

**Phase 5 → 6 transition note:** moved on by explicit user decision
("go ahead and move to phase 6") with two Phase 5 items still statically-only
verified, not gate-closed: the Staffing screen's backtest chart and the
900px/760px `LayoutBuilder` mobile breakpoints (Timetable, Documents,
Attendance kiosk). Everything else in the Phase 5 gate — dead ends, raw
exceptions, empty states, the WS badge, the dashboard live-counter — is
code-reviewed, fixed, and live-verified.

**Update, during Phase 6 screenshot capture:** the Staffing chart is now
live-verified — `docs/screenshots/05-staffing.jpg` is a real screenshot of
the `fl_chart` backtest line rendering correctly with real forecast data
(department cards, predicted-vs-actual lines, the honest "2.5% better than
a flat-average baseline" skill score). One item left: the mobile-width
`LayoutBuilder` breakpoints (900px for Documents/Timetable, 760px for the
Attendance kiosk). Partial evidence gathered — the nav rail's own
icon-only collapse at ≥700px/<1000px was confirmed rendering correctly at
800px width — but none of the three panel-specific breakpoints were
reached before the browser tooling locked up across all open tabs
(confirmed environmental: every tab, including ones untouched by the
resize, stopped responding to screenshot calls). Not retried further per
the tool guidance against rabbit-holing on browser automation failures.
Carried forward; low-risk since the code is a straightforward,
already-reviewed `LayoutBuilder` conditional identical in shape across all
three screens.

**Second update:** retried live-resize verification with a fresh tab;
`resize_window` reported success three times (800×830, 800×900, 1000×700)
but `window.innerWidth` — checked directly via JS after each call, not
inferred from a screenshot — stayed pinned at 1512 every time. This is a
different, more specific failure than the earlier tab-lockup: the tool
call succeeds but has no effect on the actual OS window, so no amount of
retrying resolves it in this session. Stopped after three attempts per the
guidance against rabbit-holing, and fell back to static verification
instead: read `documents_screen.dart`, `timetable_screen.dart`, and
`attendance_screen.dart`'s `LayoutBuilder` bodies plus the panel widgets
they render. All three are sound — in the narrow branch, `ReviewPanel` and
`ExplainPanel` both take `width: null` (not their normal fixed 680px/360px)
so they fill the available width instead of overflowing it, and the
Attendance kiosk's camera pane sits in a `Column` with
`CrossAxisAlignment.stretch` rather than its normal `SizedBox(width: 420)`.
No fixed-width widget survives into any narrow branch. This is real
evidence from reading the exact code that runs, not a guess — but it is
static, not a pixel-rendered click-through, and is logged as such rather
than claimed as equivalent to live verification.

## Done
- **Phase 6** — artifacts & ship (in progress):
  - README.md: five real screenshots captured live (Dashboard, Timetable +
    explain panel, Documents review with bbox overlay, Attendance manual
    roll call, Staffing forecast + backtest chart) in
    `docs/screenshots/`; a hero GIF (`docs/hero.gif`, 2.7MB) of the actual
    Mrs. Rao flow recorded live — mark Aadhya Menon absent, two uncovered
    periods surfaced with ranked candidates, assigned both, "Every period
    is covered," Dashboard Outbox shows both drafted notifications, no
    uncovered-class alert; a Mermaid architecture diagram (no PNG tooling
    needed, renders natively on GitHub); an updated "what's real vs
    stubbed" table reflecting every Phase 5 fix.
  - Screenshots and the GIF were captured against a **local** `make demo`
    instance with a real generated timetable (372 entries, 8.03s,
    feasible), not production — production's timetable is empty (the
    known Render RAM gap from Phase 2), so the Timetable and "Mark absent"
    screens have nothing to show there. Named explicitly in the README and
    here, not hidden. Killed a stale `flutter run -d web-server` process
    that had been running for hours and stopped responding; rebuilt a
    clean local release bundle (`--dart-define`d at `localhost:8000`) and
    served it statically instead.
  - DEMO_SCRIPT.md: replaced the placeholder beat sheet with real,
    word-for-word narration lines for all 7 beats, plus an explicit
    recording note that the solver and Mrs. Rao beats need the local
    instance for the same reason as the screenshots above.
  - Deploy hardening (PROMPT.md §11): `.github/workflows/demo-survival.yml`
    — a `/health` ping every 10 minutes (Render's free tier sleeps after
    ~15 minutes idle) and an hourly `POST /demo/reset`. Not just written —
    triggered manually via `gh workflow run` and confirmed both jobs
    actually succeed against production (`health: 200 in 32.25s`,
    `reset: 200 in 32.17s`). The 32-second timings are themselves real
    evidence this safeguard is needed: the instance had gone back to sleep
    during this same work session.
  - Live-verified two more items along the way: the Staffing screen's
    backtest chart (closing a Phase 5 known gap — see the screenshot) and
    the icon-only `NavigationRail` collapse at the 700–1000px breakpoint.
    The Documents/Timetable/Attendance-kiosk panel-specific breakpoints
    (900px/760px) could not be live-clicked — `resize_window` is a no-op
    in this session (confirmed via `window.innerWidth` after three
    attempts at different sizes) — but are now statically verified: all
    three `LayoutBuilder` narrow branches replace/stack instead of
    overflowing, and no fixed-width widget survives into any of them (see
    the transition note above for the exact evidence per screen).
  - Visual identity pass (user: "make it beautiful using frontend
    skills"): added Fraunces (serif, w600) to the theme's `display*`/
    `headline*` text-theme slots only — every screen title and "big
    number" across the app runs through those slots already, so this one
    theme-level change propagated everywhere with no per-screen risk,
    without touching Phase 5's just-verified widget trees. Plus Jakarta
    Sans stays for body/UI chrome. Rebuilt the login screen: a quiet
    ruled-paper `CustomPainter` background (horizontal rules + one margin
    line, both low-alpha) as the one deliberate signature element tying
    back to "paper in, decisions out"; a single restrained fade+rise entry
    animation on the login card; the Admin button now reads as primary
    (filled) against Teacher/Parent (outlined) instead of three identical
    buttons. Committed as `665f40d`. Recaptured all 6 screenshots and the
    hero GIF against the redesigned theme for visual consistency
    (`b013bd2`) — the old assets were taken before Fraunces existed and no
    longer matched.
  - **Not yet done:** the actual demo video (needs the user's voice
    recording and burned-in captions — outside what this session can
    produce), a real phone-on-mobile-data check of the live URL, and the
    submission platform's form (platform itself still unknown — see
    `docs/brief.md`).
- **Phase 5** — feature freeze & bug bash (in progress, first pass done,
  Flutter-only so far):
  - Added a single `friendlyError(Object error)` helper (`data/repositories.dart`)
    that routes every caught exception (`ApiException`, `DioException`, anything
    else) through the existing message-formatting logic, and swept every screen
    to use it instead of raw `'$e'`/`error.toString()` interpolation — fixed
    ~15 spots across the Action Center, Documents (review panel, upload picker,
    bulk upload, sample chips), Timetable (grid, explain panel, generate,
    substitute panel), People, Class students, Staffing, Attendance's kiosk scan
    handler, the header Reset button, and login (`AuthNotifier.demoLogin`).
  - Closed 5 real dead-end bugs — actions that could fail with **no** user-visible
    feedback: `KioskNotifier.handleScan` had no error handling at all before this
    pass (a failed scan just silently did nothing); manual roll-call marking,
    document reject, the upload file-picker, and the sample-doc chips were the
    same. All five now surface a SnackBar or inline error with a real message.
  - Fixed a genuine architecture bug in `substitute_dialog.dart`: if `assign()`
    failed partway through a multi-period absence, the error branch replaced the
    *entire* panel, hiding the remaining still-actionable periods — a dead end
    for the Mrs. Rao story if one assignment ever failed. Error now renders as a
    banner above the still-visible periods list, gated on `state.absenceId ==
    null` to distinguish "never loaded" from "loaded, then one action failed."
  - Added 4 missing empty states (People's Teachers/Classes tabs, class roster,
    manual roll-call with no class selected) that previously rendered a blank
    `ListView`/`SizedBox` with no explanation.
  - Documents' review panel loading state upgraded from a bare spinner to
    `SkeletonList`; its Commit/Reject buttons now disable each other mid-request
    instead of allowing a double-submit race.
  - Responsive pass: Timetable (grid + explain panel), Documents (list + review
    panel), and Attendance's kiosk tab (camera + live feed) now use
    `LayoutBuilder` to switch from side-by-side to stacked/single-panel below a
    width threshold (900px for the panel screens, 760px for the kiosk row)
    instead of overflowing at phone width, per PROMPT.md §7.2.
  - Ran `dart format lib/` across the codebase (35 files reformatted; spot-
    checked several untouched files to confirm only cosmetic line-wrap diffs).
    `flutter analyze` clean after two lint fixes this surfaced (`friendlyError`
    needed explicit braces on a single-line `if`; `action_center.dart`'s async
    catch needed an explicit `context.mounted` guard).
  - Committed `e0ce6e3` ("phase-5: bug bash — raw exceptions, dead ends, empty
    states, mobile layout"), pushed, redeployed (Vercel frontend rebuilt with
    prod dart-defines; Render backend unchanged this slice — everything above
    is Flutter-only).
  - Second slice (`7bce164`), closing the two screens named as unaudited
    above: found a real bug in `_WsBadge` (header's Live/Connecting… dot) —
    it derived connectivity from whether the domain-event stream had ever
    emitted anything, so once any WebSocket message arrived it latched
    "Live" forever, even through a later silent drop-and-reconnect (`WsClient`
    swallows `onDone`/`onError` internally and just retries after 3s, never
    surfacing that to listeners). This is a real correctness problem, not
    cosmetic — a judge watching that badge during a genuine Render free-tier
    idle disconnect would see a lie. Fixed by giving `WsClient` its own
    `connectionStatus` stream, driven by `WebSocketChannel.ready` (verified
    against the installed `web_socket_channel` 3.0.3 source, not guessed —
    it's implemented in both the web and IO adapters) plus the existing
    `onDone`/`onError` hooks, exposed as a new `wsConnectionProvider` the
    badge now watches instead of `eventStreamProvider`. Also gave the Login
    screen's three demo-login buttons a real spinner on the one actually
    pressed — previously all three just went inert on click with zero visual
    confirmation the tap registered.
  - Redeployed after this slice: pushed `7bce164`, rebuilt
    `flutter build web` with the production dart-defines
    (`API_BASE_URL=https://shaala-os-api.onrender.com`,
    `WS_BASE_URL=wss://shaala-os-api.onrender.com`), `vercel --prod` from
    `build/web`, aliased to `shaala-os.vercel.app`. Both prod URLs curl 200
    immediately after.
  - **Not yet done, this phase is not gate-passed:** live browser
    verification of any Phase 5 fixes across both slices — browser click
    automation has been broken across three attempts in two sessions now
    (confirmed environmental via a plain external test page, not
    app-specific); relied on backend tests + `flutter analyze` +
    `flutter build web` + direct curl checks instead. Every screen named in
    PROMPT.md §9's Phase 5 gate has now been code-reviewed and fixed where
    something was actually wrong; what remains is eyes on it.
  - **Third slice — browser tooling recovered this session; live-verified
    against production for the first time since Phase 3.** Confirmed
    working exactly as designed: the header Reset button (confirm dialog →
    progress dialog → full reload → back to login — previously only
    statically verified), the Login screen's new per-button spinner, the
    Documents review panel end-to-end (bbox overlay on the real image,
    amber low-confidence field sorted first, commit → student genuinely
    created — verified via a direct API check, not just the UI), and
    `/timetable/generate` correctly showing the new friendly message
    instead of a raw error when it fails on Render's free tier.
  - Found and fixed a real bug this surfaced immediately: hit Render's
    free-tier cold start on the very first login attempt and got a raw Dio
    exception on screen — *"The request connection took longer than
    0:00:10.000000 and it was aborted. To get rid of this exception, try
    raising the RequestOptions.connectTimeout..."* — exactly what the
    Phase 5 `friendlyError` sweep was supposed to prevent.
    `ApiException.fromDioException` only ever read a `detail` off an HTTP
    response body; for network-level failures (timeout, connection error)
    with no response at all, it fell straight through to dio's own raw
    `e.message`. Fixed by branching on `DioExceptionType` (checked against
    the installed dio 5.11.0 source) and naming the Render cold-start
    possibility directly in the message, since that's the real, expected
    path here. Committed `5b6d564`, live-verified the fix immediately after
    on the same failure path.
  - Chased a second, deeper bug from the same live pass, all the way to a
    real fix and a clean live re-confirmation: committed a sample admission
    form and the Dashboard's student counter stayed at 600 instead of
    ticking to 601 — the exact "student count ticks up live" beat
    DEMO_SCRIPT.md opens with. Confirmed via direct API checks throughout
    that the backend side was never at fault (601 real rows, immediately,
    every time — 10 rapid successive `curl` polls right after a commit all
    came back correct). Added temporary instrumentation to trace the actual
    client-side sequence rather than guessing, and found the WS event, the
    `invalidateSelf()` call, and the provider rebuild were all firing
    correctly on `document.committed` — the *refetch itself* was the one
    returning stale data. Root cause: no response from this API ever set
    `Cache-Control`, and Dio's web adapter uses `XMLHttpRequest` (checked
    against the installed `dio_web_adapter` 2.2.1 source, not guessed),
    which Chrome was willing to serve from its own HTTP cache for a repeat
    GET to the identical `/students` URL — even with no `Last-Modified` or
    `ETag` present. This undermines the app's entire "WS says something
    changed, refetch" model for every GET endpoint, not just this one.
    Fixed with a blanket `Cache-Control: no-store` middleware in
    `services/api/app/main.py` (`69361f0`) rather than annotating routes
    one at a time.
  - Also added, while investigating: the four WS-driven self-invalidating
    providers (students count, action items, notifications,
    attendance-today) now also invalidate on the `'connected'` event
    (`60d7f34`), which the backend sends on the initial connect *and* every
    reconnect — a sound defensive pattern for genuine connection drops,
    even though it turned out not to be this bug's actual cause.
  - **Live re-verified after both fixes deployed, cleanly this time**:
    reset → committed a fresh admission form → the Dashboard counter
    correctly ticked 600 → 601 without a manual refresh. It took roughly
    20 seconds end to end on this pass, longer than the sub-second local
    timing — real Render free-tier latency through the full
    commit → broadcast → run_signals → second broadcast → WS delivery →
    client refetch chain, not a bug. Worth keeping in mind for the recorded
    demo (leave a beat after committing before the counter visibly moves),
    but the mechanism itself is confirmed correct and live-verified, not
    just architecturally sound.
  - Along the way, also live-confirmed two more previously-unverified items
    from this same session: an admission-form commit correctly disabling
    Reject/re-triggering while in flight, and the header Reset button's
    confirm → progress → full reload → login cycle working a second time
    from a warm session (not just cold).
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
    First deployed measurement was 73s against the 15s §11 budget — see the
    Phase 4 gate entry below for the full root-cause and fix; landed at
    5.8-6.7s on the deployed URL after two rounds of real optimization.
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
- The Staffing screen's backtest chart is now live-verified (Phase 6
  screenshot capture — see `docs/screenshots/05-staffing.jpg` and the
  transition note at the top of this file). Every Phase 4/5 feature (Action
  Center, substitute assignment, notifications, attendance
  kiosk/manual/ID-cards, Reset button, Documents pipeline, WS badge, login,
  Staffing chart) has now been verified live in the browser at least once.
- Phase 5's mobile-responsive `LayoutBuilder` breakpoints (900px for
  Documents/Timetable, 760px for the Attendance kiosk) and the
  substitute-dialog error-banner fix are statically verified, not
  live-clicked. Two separate attempts across this session: first the
  browser tooling locked up across every open tab mid-resize; on retry
  with a fresh tab, `resize_window` itself proved to be a no-op
  (`window.innerWidth` stayed at 1512 across three different target
  sizes, checked directly via JS, not inferred from screenshots). Both are
  environmental failures, not code issues — see the transition note at
  the top of this file for the line-level code evidence gathered instead.
  Worth a real device or a working resize tool if one becomes available;
  not worth further time in this session per the anti-rabbit-holing
  guidance.
- Phase 5's original two-remaining-item list is now down to one (the
  breakpoints above) — this file's Phase 5 phase-log entry below still
  reads "gate not yet passed," which is accurate; Phase 6 work proceeded in
  parallel per explicit user instruction rather than waiting on it.

## Next 3 tasks (Phase 6 — artifacts & ship)
1. If a working browser-resize path becomes available, live-click the
   900px/760px breakpoints to upgrade them from statically-verified to
   live-verified — the one item this session's tooling couldn't close.
2. Sweep the rest of the app (Dashboard, Timetable, Documents, Attendance,
   People, Staffing) for the same "make it beautiful" pass the login
   screen and theme got — the redesign so far is deliberately scoped to
   the theme-level Fraunces change plus login only, to avoid destabilizing
   Phase 5's just-verified widget trees; a wider pass is a real option if
   there's session time left.
3. Things only the user can do: record the actual demo video (voice +
   burned-in captions), test the live URL from a real phone on mobile
   data, fill out the submission platform's form (platform itself unknown
   — see `docs/brief.md`).

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

### Phase 4 — The intelligence — ✅ gate passed, with one inherited blocker named
Gate (PROMPT.md §9): "the full Mrs. Rao story runs in under 10 seconds on the
**deployed** URL, unassisted, starting from a fresh `POST /demo/reset`."
Broken into its two real parts:

- **The story itself** (mark a teacher absent → see the real uncovered
  periods → assign substitutes → the absence and its Action Center card
  resolve): timed at **0.40s** end to end against a fresh local reseed +
  generated timetable (3 uncovered periods for Kavita Rao, all assigned,
  `absence_resolved: true` on the last one) — nowhere near the 10s budget.
  Also verified live in the browser earlier this phase (see the substitute-
  engine log entry above): the dialog showed exactly 9-A/10-B/11-C/6-A, and
  assigning all four cleared the card with no manual refresh.
- **`POST /demo/reset` itself**, which the gate requires running *first*:
  measured **73 seconds** on the first deployed check against Render+Neon —
  5x over PROMPT.md §11's separate, explicit 15s budget for this exact
  endpoint. Root-caused properly rather than guessed at (see the two
  `seed.py` phase-4 commits): most seed functions did one `db.add()` per row
  in a loop, fine over Docker-to-Docker localhost, expensive as 650+ real
  round trips over Render-to-Neon; fixed with single bulk
  `INSERT ... RETURNING id` per table. That barely moved the number (73s →
  71s) because the ~46k-row attendance history — already chunked bulk
  `INSERT` — was the actual dominant cost, confirmed by measuring per-row
  cost directly against the live production database at three different
  chunk sizes (500/2000/5000 rows): ~3.4ms/row at every size, meaning the
  bottleneck was Neon free-tier write throughput, not round-trip count.
  Switched to `COPY ... FROM STDIN` (measured ~1.1ms/row on the same
  database, ~3x faster, verified empirically before committing to it) and
  the deployed endpoint measured **5.8-6.7s** across repeated checks — an
  11x improvement, comfortably inside the 15s budget.
- **What's still blocked, and why it's not fixed this session:** getting an
  *active timetable* on the deployed URL at all — required for the
  uncovered-periods part of the story to have anything to show — still
  fails, because `POST /timetable/generate` still can't complete on Render's
  free-tier RAM (the Phase 2 finding, already root-caused and explicitly
  deferred to Phase 5/6 by prior decision in this same project). This isn't
  a new Phase 4 problem; Phase 4 just added a gate that happens to depend on
  it. Not re-litigated here — same deferral stands.

**Bottom line:** every part of the gate that Phase 4 actually owns (the
story, and the reset budget) passes, with real numbers, against the
deployed URL. The one part that doesn't (an active timetable existing on
that URL at all) was broken before Phase 4 started and is tracked as its
own item, not folded into this phase's status.

### Phase 5 — Feature freeze & bug bash — ⏳ in progress, not yet gate-passed
Gate (PROMPT.md §9): no dead ends, no raw exception strings reaching the UI,
no state that only works if the user clicks in exactly the right order,
responsive down to phone width.

First pass complete and shipped (`e0ce6e3`, pushed, redeployed): a systematic
code-level sweep — not a feature list — found and fixed real instances of
every category the gate names. See the Done entry above for the full list;
in short, ~15 raw-exception leaks routed through a new `friendlyError()`
helper, 5 genuine dead ends (kiosk scan had *no* error handling at all),
1 architecture bug where an error could hide otherwise-still-actionable UI
(`substitute_dialog.dart`), 4 missing empty states, and 3 screens made to
degrade gracefully at phone width via `LayoutBuilder` instead of overflowing.

This was done by direct code review and grep-based sweeps, not by clicking
through the app — browser click automation has now failed identically across
three separate attempts spanning two sessions (confirmed environmental, not
app-related, by testing against a plain external page each time). Verified
instead via `flutter analyze` (clean), `flutter build web` (succeeds),
backend tests (38 passing, 1 skipped), and direct curl checks against both
local and production.

Second slice (`7bce164`) closed the two screens the first slice hadn't
reached yet: the header's Live/Connecting… badge was a real correctness bug,
not cosmetic — it latched "Live" permanently after the first WebSocket
message and would keep claiming a healthy connection through a genuine
silent drop-and-reconnect, since `WsClient` handled that internally and
never told any listener. Fixed with a dedicated `connectionStatus` stream
driven by `WebSocketChannel.ready` (checked against the installed
`web_socket_channel` 3.0.3 source before using it, per CLAUDE.md rule 4)
plus the existing `onDone`/`onError` hooks. The Login screen's three demo
buttons also went from "disables on click, no other feedback" to a real
per-button spinner. Rebuilt with production dart-defines, pushed, and
`vercel --prod`-deployed; both prod URLs curl 200 afterward.

Third slice: browser tooling recovered mid-session, enabling the first live
verification pass since Phase 3. Confirmed working exactly as designed: the
Reset button's full confirm → progress → reload → login cycle, the Login
spinner, and the Documents pipeline end to end (bbox overlay, low-confidence
sort, commit landing as a real `Student` row — checked directly against the
API, not just the UI). This immediately paid for itself: hit Render's free
tier cold start on the first live login attempt and caught a real bug —
`ApiException.fromDioException` had no handling for network-level failures
(no HTTP response to read a `detail` from), so it fell through to dio's own
raw, multi-line `DioExceptionType` message. Fixed by branching on the
exception type (checked against installed dio 5.11.0 source) and naming the
cold-start possibility directly (`5b6d564`), then live-reverified the exact
same failure path immediately after — clean, friendly message this time.

A second bug surfaced from the same pass, and this one took real digging to
run to ground: after a commit, the Dashboard's student counter stayed stale
instead of ticking up, the literal first beat of DEMO_SCRIPT.md. First
instrumented and fixed the wrong-but-reasonable hypothesis — the four
WS-driven self-invalidating providers only react to their own named event
type, so a connection drop could plausibly lose a broadcast (fixed in
`60d7f34` by also invalidating on `'connected'`, a sound defensive pattern
kept regardless). But live re-testing after that fix still showed the same
staleness, and direct `curl` polling proved the backend was never at fault
(601, immediately, on 10/10 rapid successive checks after a commit). More
instrumentation isolated the real cause precisely: the WS event, the
`invalidateSelf()` call, and the provider rebuild were all firing correctly
— the *refetch itself* was returning stale data. No response from this API
ever set `Cache-Control`, and Dio's web adapter uses `XMLHttpRequest`
(checked against the installed `dio_web_adapter` 2.2.1 source), which
Chrome was willing to serve from its own cache for a repeat GET to the
identical URL. Fixed with a blanket `Cache-Control: no-store` middleware
(`69361f0`) rather than annotating routes one at a time, since this
undermined the app's entire live-update model, not just this one counter.
Live re-verified cleanly afterward: reset → commit → the counter correctly
ticked 600 → 601 with no manual refresh, taking roughly 20 seconds
end-to-end (real Render free-tier latency through the full request chain,
not a bug — worth a deliberate beat in the recorded demo).

**Gate is not being declared passed yet**, but only two items remain, and
neither has working-vs-broken evidence either way yet: the Staffing chart
and the mobile-width `LayoutBuilder` breakpoints. Every other screen and
state PROMPT.md §9's Phase 5 gate cares about has been code-reviewed, fixed
where something was actually wrong, and live-verified in the browser this
session. Carried forward as "Next 3 tasks" above.

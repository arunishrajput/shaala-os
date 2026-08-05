# SHAALA OS — Build Specification
### v4 · PaperBuddy EduHack ("Hack the Web") · track: Future-Ready Ops · online · 5-day budget · software-only

> **How to use this file.** Two files live at repo root:
> - `CLAUDE.md` — short, hard rules, loaded every session.
> - `PROMPT.md` — this file, the full spec. Claude reads it **once at the start of each phase**, not every turn.
>
> Kick off with:
> `claude "Read CLAUDE.md, then PROMPT.md end to end. Do not write code yet. Restate the plan in under 20 lines, flag anything over-scoped or mis-sequenced, then start Phase 1."`

---

## 0. WHO IS JUDGING YOU (read this first — it changes everything)

**The organizer is PaperBuddy, a live commercial School & Coaching ERP.** Their
shipping product already does: smart attendance, fee management, LMS, parent
communication, and AI exam generation. Their marketing site and the hackathon
site are both **Flutter Web** apps.

Five consequences, all of which shape the build:

1. **Your judges are domain experts.** They have argued about timetable edge
   cases in real customer calls. A fake solver or an LLM wrapper called "our AI
   engine" gets spotted in seconds. Everything you ship must survive an expert
   asking *"okay, but what happens when two labs are booked and the only free
   Physics teacher has hit her daily cap?"*
2. **Do not rebuild their product.** Fees, LMS, exam generation and parent
   messaging are *their existing features*. Building them shows no insight and
   invites a direct, losing comparison. Build the hard things they haven't
   commoditized — see §2.
3. **Flutter Web is the house language.** The brief nudges at Riverpod; the
   organizer *writes Flutter for a living*. Your Dart code is the code they can
   read fastest and judge hardest. Structure it like you're being hired.
4. **The real prize is the internship**, not the ₹11,000 split across a team.
   That means the repo is a work sample. Commit history, README, tests, and
   architecture docs are graded whether or not the rubric says so.
5. **It's online and web-first ("Hack the Web").** Nobody watches you present.
   Judges open a link at a random hour, poke for four minutes, watch a video,
   skim the README. Deployment is a Phase-1 task, not a Phase-6 task.

> ⚠️ **Unverified details.** The track page renders client-side and could not be
> read programmatically. Before Phase 1, the human must paste into `docs/brief.md`:
> exact submission deadline, team size, judging rubric and weights, submission
> platform fields (Devfolio/Unstop), and any stack restrictions. **If the rubric
> contradicts anything here, the rubric wins.** Do not guess at these.

---

## 1. THE PRODUCT

**Name:** Shaala OS · **Tagline:** *Paper in, decisions out.*

**Pitch:**
> Shaala OS turns a school's paper and chaos into a live database, then acts on
> it — reading forms with AI, generating conflict-free timetables with a real
> constraint solver, and telling the principal what needs attention before they
> think to ask.

**The story every feature serves — memorize it, the demo is built around it:**

> It's 8:05 AM. Mrs. Rao, who teaches Physics to 9-A, 10-B and 11-C, calls in
> sick. Normally that's 45 minutes of a clerk running down corridors with a
> register. In Shaala OS the principal's dashboard already has a card waiting:
> *3 classes uncovered, here are the 3 best substitutes, tap to assign.* One
> tap. Timetable rewritten. Teachers notified. Parents of 11-C told their extra
> class moved. Six seconds.

---

## 2. STRATEGY — WHAT TO BUILD, AND WHAT TO REFUSE TO BUILD

**Build these three. They are the moat.**

| # | Feature | Why it wins against this specific judge |
|---|---|---|
| 1 | **CP-SAT timetable engine** with explain-any-cell and a substitute repair loop | Genuinely hard, genuinely valuable, and PaperBuddy hasn't commoditized it. A real constraint solver is a technical claim you can prove in `docs/solver.md`. |
| 2 | **Document → data pipeline** with per-field confidence and human-in-the-loop review | This is the problem statement's headline ask. The differentiator is the *review UI*, not the OCR call. |
| 3 | **Proactive Action Center** — the dashboard as an inbox of one-tap decisions | The brief explicitly asks the dashboard to surface issues rather than make admins hunt. Almost every team will ship charts instead. |

**Supporting cast (smaller, still built):** QR attendance kiosk, staffing
forecast, notification outbox, teacher view.

**Refuse to build:** fee management, LMS/course content, exam paper generation,
report cards, payment gateways, multi-tenancy, i18n, settings pages, dark-mode
toggles, RFID/IoT/firmware, UI unit tests, auth beyond JWT + three demo logins.
Note the first five are *PaperBuddy's own shipping features* — building them is
strictly downside. Put them in the README roadmap instead, framed as "deliberately
out of scope; this is an ops-intelligence layer, not another ERP."

---

## 3. TECH STACK — PINNED, NOT NEGOTIABLE

Version drift is the #1 way an AI-assisted Flutter build dies. Pin these in
`pubspec.yaml` / `requirements.txt` in Phase 1 and never bump mid-build.

**Frontend — `apps/admin`**
```
flutter: 3.x stable (record the exact version in README)
flutter_riverpod: ^2.5.0      # MANUAL providers only — no riverpod_generator
go_router: ^14.0.0
freezed_annotation + json_annotation   # models ONLY
dio, web_socket_channel, fl_chart, google_fonts, mobile_scanner, file_picker
build_runner: used ONLY for freezed/json models
```
> **One style rule:** every provider is hand-written (`Provider`, `StreamProvider`,
> `AsyncNotifierProvider`). Do **not** mix in `@riverpod` codegen — the two styles
> produce different generated symbols and a half-migrated codebase that won't build.
> Mixed provider styles are the single most common self-inflicted build break.

**Backend — `services/api`**
```
python 3.11
fastapi, uvicorn[standard], sqlalchemy>=2.0, alembic, psycopg[binary]
pydantic>=2, python-jose[cryptography], passlib[bcrypt]
ortools            # the solver — keep it
opencv-python-headless   # headless build only; the GUI build breaks in Docker
pillow, reportlab, qrcode, httpx, apscheduler
```
**Deliberately excluded, and say so in the README:**
- ❌ `face_recognition` / `dlib` — needs a C++ toolchain, ~1GB image, and will OOM
  a 512 MB free-tier container. Group-photo attendance becomes **optional and
  fixture-backed** (§5.4B).
- ❌ `scikit-learn` / `torch` — the staffing forecast uses a transparent EWMA +
  seasonal baseline (§5.5). Smaller, faster, and *more* defensible to an expert judge
  than a black box trained on 90 synthetic rows.

**Infra:** PostgreSQL 16 (Docker locally, Neon in prod) · backend on Render/Railway/Fly
(Docker) · Flutter Web on Vercel/Firebase Hosting · GitHub Actions for lint + solver tests.

**Vision model:** Gemini Flash behind a `VisionProvider` interface with providers
`gemini | fixture`. **Verify the current model ID before use** and put it in `.env`.
Never hardcode a model string you recalled from memory.

---

## 4. REPO LAYOUT

```
shaala-os/
├── CLAUDE.md  PROMPT.md  PROGRESS.md  README.md  DEMO_SCRIPT.md  LICENSE
├── Makefile                 # up | seed | reset | demo | verify | test
├── docker-compose.yml  .env.example  .github/workflows/ci.yml
├── docs/
│   ├── brief.md             # human pastes the official rubric + deadline here
│   ├── architecture.png     # one clean diagram
│   ├── solver.md            # the constraint model in prose
│   └── screenshots/
├── apps/admin/lib/
│   ├── core/                # theme, router, api_client, ws_client, env
│   ├── data/                # freezed models + repositories
│   ├── providers/           # ALL Riverpod providers live here
│   └── features/
│       ├── auth/ dashboard/ documents/ timetable/
│       ├── attendance/ people/ staffing/ teacher/
└── services/api/
    ├── app/
    │   ├── main.py
    │   ├── db/              # models.py, session.py, seed.py
    │   ├── routers/
    │   ├── services/
    │   │   ├── vision/      # provider interface + gemini.py + fixture.py + prompts.py
    │   │   ├── timetable/   # solver.py, explain.py, substitute.py
    │   │   ├── signals/     # the proactive rule engine
    │   │   └── staffing/    # forecast.py
    │   └── ws/              # event bus + connection manager
    ├── tests/               # solver property tests + API smoke tests
    └── fixtures/            # 4 sample form images + cached AI responses
```

---

## 5. DATA MODEL — one Alembic migration, Phase 1

Every table must be used by a demo feature. Nothing speculative.

```
School(id, name, academic_year)
User(id, email, password_hash, role ENUM(admin,teacher,parent), linked_id)

Teacher(id, name, code, subjects[], max_periods_per_week, max_periods_per_day,
        unavailable_slots[], preferred_slots[], phone, dept)
Student(id, admission_no, name, class_id, roll_no, guardian_name, guardian_phone,
        qr_token UNIQUE, photo_url)
ClassSection(id, grade, section, strength, home_room_id)
Subject(id, name, code, weekly_periods, needs_lab BOOL, is_double_period BOOL)
Room(id, name, capacity, type ENUM(classroom,lab,hall))
TimeSlot(id, day 0-5, period 1-8, start, end, is_break)

Assignment(id, class_id, subject_id, teacher_id)
TimetableVersion(id, created_at, label, solver_stats JSONB, is_active)
TimetableEntry(id, version_id, class_id, subject_id, teacher_id, room_id, slot_id,
               is_substitution, original_teacher_id NULL)

AttendanceRecord(id, student_id, date, status, method ENUM(qr,vision,manual),
                 marked_at, confidence FLOAT NULL, source_ref)
TeacherAbsence(id, teacher_id, date, reason, resolved BOOL)

Document(id, type, original_url, status ENUM(pending,needs_review,committed,rejected),
         raw_ai_response JSONB, uploaded_at, committed_at, uploaded_by)
ExtractedField(id, document_id, field_name, value TEXT, confidence FLOAT,
               bbox JSONB, was_corrected BOOL, corrected_value TEXT)

ActionItem(id, kind, severity ENUM(critical,warning,info), title, body, payload JSONB,
           status ENUM(open,resolved,dismissed), created_at, resolved_at, primary_action)
Notification(id, to_name, to_phone, channel, body, status, created_at)   # the Outbox
EventLog(id, type, payload JSONB, at)                                    # WS + audit trail
```

**Seed data is a feature.** `seed.py`, **fixed RNG seed**, identical on every run
and every redeploy:
- 12 sections (6-A → 10-B, plus 11/12 Science & Commerce)
- 40 teachers across 8 departments — deliberately make 2–3 tightly constrained so
  the solver has genuine pressure to relieve and the explain panel has something to say
- 600 students with names, guardians, roll numbers, QR tokens
- 8 classrooms, 3 labs (Physics/Chem/Computer), 1 hall
- **90 days of attendance history with real texture:** Monday dips, a post-festival
  dip, a flu week in one section, and exactly 6 students trending toward the 75% cliff
- 3 open ActionItems, 2 pending documents, 1 unresolved absence — **the dashboard is
  never empty on a judge's first load**

---

## 6. FEATURE SPEC

### 6.1 AI Document Reader — "paper to data in 8 seconds"

Not an OCR box. A pipeline with a human in the loop. The review UI is the feature.

**Doc types (auto-classified):** `admission_form`, `attendance_sheet`,
`marks_sheet`, `leave_application`.

```
upload (file, camera, or bulk)
  → preprocess (deskew + contrast, opencv-headless)
  → VisionProvider.extract(image, schema)      # JSON + per-field confidence
  → persist Document + ExtractedField rows
  → any field confidence < 0.85 → status = needs_review
  → Review UI: original image | editable fields, side by side
       · low-confidence fields glow amber and lead the tab order
       · focusing a field draws its bbox on the image
  → one-tap Commit → creates real Student / AttendanceRecord rows
  → WebSocket event → dashboard counters animate up live
```

**Vision prompt** (`services/vision/prompts.py`, strict JSON):
```
You are a document extraction engine for an Indian school's records.
Return ONLY valid JSON. No markdown fences, no prose.

{
  "doc_type": "admission_form|attendance_sheet|marks_sheet|leave_application",
  "doc_type_confidence": 0.0-1.0,
  "fields": [{"name":"<snake_case>","value":"<string>","confidence":0.0-1.0,
              "bbox":[x0,y0,x1,y1]}],     // bbox normalized 0-1
  "rows": [ {...} ],                       // tabular docs only
  "warnings": ["<human-readable issue>"]
}

Rules:
- Indian names may be transliterated; preserve exactly as written.
- Dates -> ISO 8601. If ambiguous (03/04/25) assume DD/MM/YY, confidence <= 0.7.
- Phone numbers -> digits only, 10 digits.
- Illegible handwriting -> value "" and confidence 0.0. Never guess.
- Confidence must reflect genuine legibility, not politeness.
```

**Bulk mode:** drop 20 photos → progress list → results table → *"Commit 17
high-confidence, review 3."* This is the moment a judge leans in.

**Demo safety:** `VISION_PROVIDER=fixture` replays cached JSON from
`fixtures/responses/` keyed by image hash. Any API error or quota exhaustion
**auto-falls back to fixture** with a console warning — never an error screen on
the live URL. Ship 4 sample images behind a **"Try a sample"** button so a judge
with no paper forms handy still experiences the feature.

---

### 6.2 Smart Timetable — the technical moat

**OR-Tools CP-SAT.** Model it properly and write it up in `docs/solver.md` —
that document is the artifact that proves the claim to an expert judge.

Variables: `x[class, subject, teacher, room, slot] ∈ {0,1}`

**Hard constraints:** one teacher in one place per slot · one class per room per
slot · one subject per class per slot · each (class, subject) gets exactly its
`weekly_periods` · lab subjects only in lab rooms · room capacity ≥ class strength ·
teacher `unavailable_slots` respected · nothing in `is_break` slots · teacher daily
and weekly caps.

**Soft constraints (weighted objective, sliders exposed in the UI):** minimize
teacher idle gaps (w=5) · spread subjects across the week, no two same-subject
periods in a day unless double (w=8) · heavy subjects in periods 1–4 (w=3) · honour
preferred slots (w=2) · balance workload across days (w=4).

Return `solver_stats`: wall time, branches, objective value, soft violations.
**Put them on screen.** *"480 assignments across 12 classes in 2.4s, zero hard
violations"* is the sentence that wins this track.

**Three capabilities that turn a solver into a demo:**

1. **Explain any cell.** Click a period → side panel with the real reason chain:
   > *Why Physics / Mr. Khan / Lab-2?*
   > • Physics 9-A needs a lab; 2 of 3 labs are busy Tue P3
   > • Mr. Khan is the only free Physics teacher — Ms. Iyer has 11-C now
   > • Moving this to Wed P2 opens a 3-period gap for Mr. Khan (+15 cost)
   >
   Implement as rules-based reason strings **plus** a re-solve with that assignment
   forbidden, diffing the objective. Cache per entry.

2. **Drag-and-drop with live validation.** Dragging greys out invalid targets
   instantly (client-side constraint check), glows valid ones. Dropping into a
   conflict → red toast naming the exact clash + **3 ranked alternatives with costs**.

3. **Substitute engine — the hero moment.** `POST /timetable/absence` →
   minimal-perturbation repair (freeze everything else, re-assign only that
   teacher's periods) → rank candidates by *free that slot > teaches the subject >
   lowest weekly load > has taught this class* → return top 3 with reasons → admin
   taps → new `TimetableVersion`, WS event, notification drafts. **Under 1.5s.**

**Tests (these are the ones that matter, put them in CI):** solver output contains
zero hard-constraint violations on the seed data · every (class, subject) hits its
exact weekly quota · no teacher exceeds daily/weekly caps · a forced-infeasible
input returns a structured "infeasible + why" response rather than crashing ·
substitution never introduces a new conflict.

---

### 6.3 The Proactive Action Center

**The dashboard is an inbox, not a report.** The top of the screen is not charts —
it's a prioritized stack of cards, each with a severity dot, a plain-English title,
one line of evidence, and **exactly one primary button**.

- 🔴 *3 classes uncovered today* — Mrs. Rao absent → **[Assign substitutes]**
- 🔴 *6 students drop below 75% this week* → **[Draft parent messages]**
- 🟠 *4 scanned forms need review* — 2 low-confidence fields → **[Review now]**
- 🟠 *Science will be 2 teachers short next Monday* → **[View forecast]**
- 🟡 *Chem Lab double-booked Thu P5* → **[Resolve]**
- 🟡 *8-B has 3 free periods this week* → **[Fill with remedial]**

**Signal engine** (`services/signals/`): a registry of **pure functions**, run on a
30s APScheduler tick *and* immediately after relevant events. Pure functions are
easy for a judge to read and easy for you to test.
```python
@signal(kind="uncovered_classes", severity="critical")
def detect_uncovered_classes(db, today) -> list[ActionItem]: ...
```

Below the stack: a compact live strip — today's attendance %, live scan feed,
period-now indicator (*"Period 4 · 11 classes in session · 1 room free"*), 30-day
sparkline.

**Everything animates on WebSocket events.** When a judge scans a QR code with
their phone, a number on their laptop must move. That cross-device moment sells the
"all-in-one, reactive" requirement by itself.

---

### 6.4 Attendance — supporting cast, not the headline

PaperBuddy already ships "smart attendance," so this is table stakes. Build it well,
keep it small, don't spend the moat's time here.

**A. QR ID cards (primary).** The system generates printable ID cards as a PDF
(`reportlab` + `qrcode`), each carrying a signed `qr_token`. Kiosk mode in the
browser (`mobile_scanner`) on any phone or webcam: point at a card → checked in →
row slides into the live feed → counter ticks up on every connected device.
Unknown token → *"Unregistered card — assign to a student?"* → live enrolment in 3
seconds. Duplicate scans within 60s are ignored and shown as "already marked".
**Put a printable QR in the README so a judge can try it from their own phone.**

**B. Group-photo vision (optional, only if Phase 4 is comfortably ahead).** Runs
**locally only**, fixture-backed on the deployed demo. Do not put dlib in the prod
image. Be explicit in the README: encodings not photos, opt-in, QR primary, vision
assistive. **Naming your own limitations reads as engineering maturity to this judge.**

**C. Manual roll call.** Three lines of UI in the teacher view. Real schools need
a fallback and showing you know that is cheap credibility.

All three paths write the same `AttendanceRecord` with a `method` field and trigger
the same downstream signals.

---

### 6.5 Staffing Forecast — small, transparent, honest

No neural net. A **per-department EWMA + day-of-week seasonal baseline** over the
90 days of seeded history, plus approved-leave and exam-period adjustments.

- Output for the next 7 days: expected absences per department, expected uncovered
  periods, **and a recommendation** — *"Pre-clear 2 substitutes for Science on
  Monday: Mr. Verma (free P2–P5), Ms. D'Souza (free P1–P3)."*
- **Ship a backtest chart** — predicted vs actual over the last 30 days with one
  honest accuracy number, computed at runtime, not hardcoded.
- Label it "forecast, not prophecy" in the UI. To a judge who sells to schools,
  a transparent baseline with a real error bar beats a black box every time.

---

### 6.6 AI layer beyond OCR (Phase 5 stretch only)

**Principal's Weekly Briefing** — one button turns computed aggregates into a short
narrative that cites its own numbers. Feed it statistics, never raw rows.

**Ask Shaala (⌘K)** — natural language → **constrained JSON intent** → a whitelist
of hand-written query functions. *"Who's free Tuesday period 3?"* **The model never
writes SQL.** Say that explicitly in the README; it's a security-literacy signal.

Do **not** build an exam paper generator — PaperBuddy already sells one.

---

## 7. FLUTTER / RIVERPOD CONVENTIONS

**7.1 Theme.** Never ship default Material blue. Deep slate base (`#0F172A`,
`#1E293B`), one accent (`#6366F1`), semantic red/amber/green for severity, Inter or
Plus Jakarta Sans via `google_fonts`, generous whitespace, 12px radii, restrained
elevation. The organizer's own brand is near-black (`#050505`) — a dark, high-contrast
product will feel native to them. Judges form an opinion in half a second from a screenshot.

**7.2 Layout.** Persistent left nav rail (Dashboard, Timetable, Documents,
Attendance, People, Staffing); top bar with school name, live clock, current-period
indicator, and a bell bound to open ActionItems. Responsive down to phone width —
"Hack the Web" means a judge may open it on their phone.

**7.3 Riverpod — used the way the brief wants it used.**
```dart
// The WebSocket is the single source of truth for "something changed".
final eventStreamProvider = StreamProvider<AppEvent>((ref) =>
    ref.watch(wsClientProvider).events);

// Domain providers invalidate themselves on relevant events. This IS the
// "updates seamlessly whenever data changes" requirement, literally.
class ActionItemsNotifier extends AsyncNotifier<List<ActionItem>> {
  @override
  Future<List<ActionItem>> build() {
    ref.listen(eventStreamProvider, (_, next) {
      final t = next.value?.type;
      if (t == 'action.created' || t == 'action.resolved') ref.invalidateSelf();
    });
    return ref.read(apiProvider).fetchActions();
  }
}
final actionItemsProvider =
    AsyncNotifierProvider<ActionItemsNotifier, List<ActionItem>>(ActionItemsNotifier.new);
```
Rules: no `setState` for server data, ever · `AsyncValue.when` everywhere, with
**skeletons not spinners** (a judge on a slow connection will see your loading
states) · optimistic updates on Action Center taps with rollback on failure ·
providers live in `providers/`, never inline in widgets.

**7.4 Motion.** Every changing number animates (`AnimatedSwitcher`,
`TweenAnimationBuilder`). New cards slide in. Substitution plays a 400ms grid
rewrite. 200–400ms, no bounce.

---

## 8. API SURFACE

```
POST /auth/login | /auth/demo-login?role=admin|teacher|parent

POST /documents/upload        (multipart 1..n)      GET  /documents?status=needs_review
POST /documents/{id}/commit   (corrected fields)    POST /documents/{id}/reject

POST /timetable/generate      {weights}             GET  /timetable/active?class_id=|teacher_id=
POST /timetable/validate-move → {ok, conflicts[], alternatives[]}
POST /timetable/move                                GET  /timetable/explain/{entry_id}
POST /timetable/absence       → {uncovered[], candidates[]}
POST /timetable/substitute    → applies             GET  /timetable/export.pdf

POST /attendance/scan {qr_token}                    POST /attendance/manual
POST /attendance/group-photo  (multipart)           GET  /attendance/today
GET  /students/id-cards.pdf                         GET  /attendance/student/{id}/summary

GET  /actions?status=open     POST /actions/{id}/resolve | /dismiss
GET  /notifications           → the Outbox
GET  /staffing/forecast?days=7 | /staffing/backtest
POST /ai/briefing | /ai/ask
POST /demo/reset              WS /ws/events         GET /health
```

---

## 9. BUILD PLAN — SIX PHASES

**Work in phases, never calendar days.** Announce the phase you're entering, finish
it, run its gate, commit, report. **Do not start phase N+1 until the gate passes.**
If a phase overruns, cut scope from inside it — never reorder.

| Phase | What it is | Share of budget |
|---|---|---|
| 1 | Foundation & public URL | ~18% |
| 2 | The solver | ~20% |
| 3 | The AI reader | ~20% |
| 4 | The intelligence | ~22% |
| 5 | Feature freeze & bug bash | ~8% |
| 6 | Artifacts & ship | ~12% |

*(Human note: total budget is 5 days — phases 1–4 are roughly a day each, 5 and 6
split the last. Claude tracks phases, not dates.)*

### Phase 1 — Foundation, and get it on the internet
docker-compose · FastAPI `/health` · full Alembic migration · `seed.py` with fixed
seed and 90 days of history · JWT auth + `/auth/demo-login` · Flutter shell (theme,
nav rail, router, API client, WS client) · People screens · **backend + web + DB
deployed to production URLs** · CI running lint.

**Gate:** `make verify` exits 0 **and** `curl https://<prod>/health` returns 200
**and** the deployed web app loads seeded students over `wss://` from a phone on
mobile data. CORS, HTTPS and WebSocket-over-TLS all break in production and never
locally — prove them now, not in Phase 6.

### Phase 2 — The solver
CP-SAT model · `/timetable/generate` + stats · grid UI with class/teacher switcher ·
explain panel · drag-and-drop with live validation and ranked alternatives ·
`docs/solver.md` written while it's fresh.

**Gate:** `pytest tests/test_solver.py` green (all five assertions in §6.2) and 12
timetables generated in under 10 seconds with zero hard violations.

### Phase 3 — The AI reader
VisionProvider (gemini + fixture) · preprocessing · prompt + strict JSON parsing ·
upload single/bulk/camera/"Try a sample" · review UI with bbox overlay and
confidence highlighting · commit → real rows → WS event → dashboard reacts ·
fixtures captured for all 4 doc types.

**Gate:** with `VISION_PROVIDER=fixture` and the network disabled, a sample
admission form still becomes a student record in under 15 seconds.

### Phase 4 — The intelligence
Signal engine + 6 rules · Action Center card stack + one-tap resolve · **substitute
engine end to end** · notification Outbox with drafted parent messages · QR kiosk +
ID-card PDF · manual roll call · staffing forecast + backtest chart.

**Gate:** the full Mrs. Rao story runs in under 10 seconds on the **deployed** URL,
unassisted, starting from a fresh `POST /demo/reset`.

### Phase 5 — FEATURE FREEZE & bug bash
**The moment Phase 5 begins, feature work is over.** Anything unbuilt is roadmap.
Stretch items only if genuinely ahead (§6.6, teacher view). Then: every empty state,
every error state, every loading skeleton, mobile responsiveness, and a full walk of
the judge's path fixing whatever feels rough.

**Gate:** no dead ends, no raw exception strings surfaced to the UI, nothing that
only works if you click in the right order.

### Phase 6 — Artifacts & ship
README per §10 · demo video · deploy hardening (keep-alive, hourly demo reset,
cold-start check from mobile data) · two full dry runs on the live URL · submission
form filled with every field.

**Gate:** someone who has never seen the project opens the README, understands it in
60 seconds, and reaches a working demo. **Submit with 4+ hours to spare** — deadline-
minute submissions lose to timezone math and upload failures.

**Hard rule:** if Phase 4 ends shaky, cut §6.6 entirely and go to Phase 5. A flawless
five-feature product beats a shaky eight.

---

## 10. THE ARTIFACTS (in async judging these carry a third of the score)

**README.md — the highest-leverage file in the repo.** In this order:
1. Name, tagline, one-line pitch — above the fold
2. Hero GIF of the Mrs. Rao flow, under 8 MB
3. **Live demo link + demo credentials**, in a box, first screen
4. The problem in three lines with one number
5. **Feature list mapped to the problem statement's own headings, verbatim** —
   *AI Document Reader → §…, Smart Timetables → §…, All-in-One System → §…,
   Proactive Dashboard → §…, Smart Staffing → §…, Auto-Attendance → §…* Make it
   trivial for a judge to tick every box.
6. Five well-cropped screenshots
7. Architecture diagram + a paragraph on **why CP-SAT** and **why WebSocket-driven Riverpod**
8. Run locally in 3 commands, tested from a clean clone
9. **"What's real vs. what's stubbed"** — an honest table. Judges find the stubs anyway;
   naming them first converts a weakness into a credibility signal
10. Roadmap, including *why* fees/LMS/exams were deliberately excluded

**DEMO_SCRIPT.md → the video.** 3–4 minutes, screen recording, clean audio,
**captions burned in** (many judges watch muted), product on screen within 5 seconds,
no talking-head intro.
`0:00` the pain, one number → `0:20` paper in: photograph a form, amber field,
correct, commit, student appears; then bulk 15 → `1:00` the solver: generate 12
timetables live, show the stats line, click a cell for the explanation, drag into a
conflict and watch it refuse with alternatives → `1:50` the hero moment: mark Mrs.
Rao absent, card appears by itself, tap, grid rewrites, messages drafted → `2:30`
attendance: scan a QR with a phone while the laptop dashboard is on screen → `3:00`
forecast + one honest limitation → `3:30` architecture diagram, then the live URL
held on screen for 5 full seconds. Record three times, keep the third.

**Submission platform.** Fill every field — repo, live link, video, description,
tech tags. Empty fields read as an incomplete entry regardless of the build.

---

## 11. DEPLOYMENT & DEMO SURVIVAL (P0)

- Free-tier backends sleep. Add an uptime pinger or use a platform that doesn't
  spin down; show a friendly "waking up" state, never a failed fetch.
- Test the live URL **from mobile data on a phone**, not just your laptop.
- Every external AI call has try/except with a cached fallback. Your Gemini quota
  *will* run out while three judges are clicking.
- **Judges mutate shared demo data at 2 AM.** `POST /demo/reset` restores seed state
  in under 15 seconds, a visible **"Reset demo data"** button sits in the UI header,
  and an hourly cron auto-resets.
- Fixed RNG seed everywhere, so the deployed app looks identical to your video.
- Keep a 90-second screen capture of the full flow as insurance.

---

## 12. THINGS THAT WILL COST YOU THIS SPECIFIC HACKATHON

- ❌ Building fees/LMS/exam-generation — competing with your judge's own shipping product.
- ❌ A greedy or random "scheduling algorithm." This judge will check.
- ❌ One LLM call with no pipeline, no confidence handling, no human-in-the-loop,
  labelled "our AI engine."
- ❌ Mixing `@riverpod` codegen with manual providers. Pick manual. Stay there.
- ❌ Putting dlib/torch in the production image, then discovering the OOM at 3 AM.
- ❌ Leaving deployment until Phase 6.
- ❌ An empty dashboard on first load. Default Material blue. Default fonts.
- ❌ A README written in the last 40 minutes.
- ❌ Adding features once Phase 5 has begun.

---

## 13. FIRST INSTRUCTION

Start **Phase 1**. Before writing any code:

1. Restate the plan in ≤ 20 lines and **flag anything here you think is wrong,
   over-scoped, or mis-sequenced — push back, don't just comply.**
2. Ask the human for `docs/brief.md` (deadline, rubric, team size, submission fields).
   Do not guess at these.
3. Create `PROGRESS.md`, `README.md`, `DEMO_SCRIPT.md` skeletons and scaffold per §4.
4. Write the `Makefile` with a real `verify` target **before** the first feature, so
   the gate exists from commit one.
5. `make up` → FastAPI `/health`, Flutter shell, green WebSocket badge.
6. Then immediately do the deploy plumbing — a public URL must work before any
   feature work begins.
7. Commit as `phase-1: foundation`, report which phase is next, and continue.

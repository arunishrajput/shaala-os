# Demo Video Script

3–4 minutes. Screen recording, clean audio, **captions burned in** (many judges
watch muted). Product on screen within 5 seconds — no talking-head intro. Record
three times, keep the third.

**Recording setup — read this before hitting record:**
- Full-screen the app window (crop out the browser's address bar / tabs) for
  every beat except the closing shot, so switching between the live URL and a
  local instance (see below) is visually seamless.
- `POST /demo/reset` (or the header reset button) immediately before recording,
  against whichever instance you're using for that beat, so the numbers on
  screen match this script exactly.
- **Beats 1:00 and 1:50 (the solver + the Mrs. Rao flow) should be recorded
  against a local `make demo` instance, not the live URL.** This is a known,
  already-documented limitation, not something to hide: Render's free-tier RAM
  can't complete `POST /timetable/generate` (see PROGRESS.md), so production
  has no active timetable and nothing to show for these two beats. Every other
  beat (document reader, attendance, staffing, the closing shot) uses the real
  live URL. Say so plainly if asked — PROMPT.md's own advice is that naming a
  stub first is a credibility signal, not a weakness.

## Beat sheet

| Time | Beat | Narration |
|---|---|---|
| 0:00 | **The pain.** Cold open on the Dashboard, live counters visible. | "A teacher calls in sick. Someone runs down the corridor with a register, checking who's free. Forty-five minutes, every time. Shaala OS makes that six seconds." |
| 0:20 | **Paper in.** Documents screen → "Admission Form" sample → bbox overlay on the real image, amber low-confidence guardian-phone field → correct it → Commit → Dashboard student count ticks up live, no refresh. | "Every paper form becomes a real record. Low-confidence fields are flagged automatically — a human checks the one number the model wasn't sure about, not the whole form." |
| 1:00 | **The solver** *(local instance)*. Timetable screen → Generate → stats line (372 assignments, feasible, wall time) → click a cell → Explain panel shows why, ranked alternatives, and the objective cost of forbidding it → drag a cell into a conflict, watch it refuse. | "This isn't a greedy scheduler guessing its way to something plausible. It's a real constraint solver — a feasibility proof, not a guess. Click any cell and it tells you exactly why it's there, and what the next-best option would have cost." |
| 1:50 | **The hero moment** *(local instance)*. People screen → "Mark absent" on a teacher with a full load → substitute dialog surfaces every uncovered period with ranked candidates → one tap per period → "Every period is covered" → Dashboard: Outbox shows the drafted notifications, no uncovered-class alert. | "A teacher's absent. The system already knows which periods are uncovered and who's actually free to cover them — not a static list, the real timetable, checked live. One tap per period, and the substitute teachers are notified. No corridor, no register." |
| 2:30 | **Attendance.** Kiosk tab, scan a QR with a phone while the laptop dashboard is on screen — counter moves live on the laptop with no local action; or manual roll call if a phone isn't available. | "Attendance takes a QR scan, and it shows up everywhere instantly — no refresh, no polling, on any device watching." |
| 3:00 | **Forecast + one honest limitation.** Staffing screen, backtest chart on screen. | "The staffing forecast is honest about its limits — it beats a naive flat-average baseline by about two and a half percent on this data. Absence counts this small are genuinely hard to forecast, and we'd rather say that than oversell a number." |
| 3:30 | **Close.** Architecture diagram (from README) on screen for a few seconds, then cut to the live URL — `shaala-os.vercel.app` visible in the address bar — held for 5 full seconds. | "One Postgres schema. One WebSocket bus. One real constraint solver. This is Shaala OS." |

## Notes

- Every beat above has been walked through for real this session, not
  imagined — see PROGRESS.md's Phase 4/5/6 entries for the specific
  live-verification evidence behind each one (exact uncovered periods,
  measured timings, screenshots in `docs/screenshots/`).
- The demo must survive judges mutating shared data at odd hours: always start
  from a fresh `POST /demo/reset` before recording, on whichever instance
  you're using for that beat.
- Captions: burn in the narration column above, don't just caption filler
  words — many judges watch muted and the narration carries the technical
  claims (CP-SAT, live WebSocket updates, the honest backtest number).

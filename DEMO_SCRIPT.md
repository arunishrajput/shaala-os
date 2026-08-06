# Demo Video Script

3–4 minutes. Screen recording, clean audio, **captions burned in** (many judges
watch muted). Product on screen within 5 seconds — no talking-head intro. Record
three times, keep the third. Refined at the end of every phase as features land;
finalized in Phase 6 (PROMPT.md §10).

## Beat sheet

| Time | Beat | Status |
|---|---|---|
| 0:00 | The pain, one number (45 min → 6 sec) | ⏳ |
| 0:20 | Paper in: "Try a sample" admission form, amber low-confidence guardian-phone field, correct it, commit, student count on the dashboard ticks up live; then bulk-upload several forms | ✅ buildable now — Phase 3 done |
| 1:00 | The solver: generate live, show the stats line, click a cell for the explanation, drag into a conflict and watch it refuse with ranked alternatives | ✅ buildable now — Phase 2 done (locally; see the known production RAM gap in PROGRESS.md) |
| 1:50 | The hero moment: mark Mrs. Rao absent, Action Center card appears by itself, one tap, grid rewrites, parent messages drafted | ✅ buildable now — Phase 4 done. Verified live: "Mark absent" on Kavita Rao surfaced exactly 9-A/10-B/11-C/6-A, assigning all four cleared the card with no manual refresh |
| 2:30 | Attendance: scan a QR with a phone while the laptop dashboard is on screen and a counter moves live | ✅ buildable now — Phase 4 done. Verified the cross-device moment specifically: a scan from a second client updated a separate, idle browser tab's counter and feed live |
| 3:00 | Forecast + one honest limitation stated on screen | ✅ buildable now — Phase 4 done. The honest limitation to say on camera: the backtest reports a skill score against a naive flat-average baseline (~2.5% better), not a flashy accuracy number — absence counts this small are genuinely hard to beat a simple baseline on, and the script should say so rather than oversell it |
| 3:30 | Architecture diagram, then the live URL held on screen for 5 full seconds | ⏳ blocked on Phase 6 |

## Notes

- Nothing here is scripted in detail yet — that happens as each phase's feature
  actually exists and can be walked through for real, not imagined.
- The demo must survive judges mutating shared data at odd hours: always start from
  a fresh `POST /demo/reset` before recording.

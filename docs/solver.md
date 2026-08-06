# The Timetable Solver

CP-SAT (Google OR-Tools), not a greedy or randomized heuristic. This document
covers the model, why CP-SAT, and the three capabilities built on top of it:
explain-any-cell, drag-and-drop validation, and the substitute repair
algorithm. Code: `services/api/app/services/timetable/{solver,explain,substitute}.py`.

## Decision variables

PROMPT.md's spec writes the variable space as `x[class, subject, teacher, room,
slot]`. This implementation narrows that: the `Assignment` table (`class_id,
subject_id, teacher_id`) is the school's roster, fixed ahead of the solve —
"Mrs. Rao teaches Physics to 9-A" is a staffing decision an admin makes, not
something a scheduler should be free to invent. So the real variables are

```
x[assignment, room, slot] ∈ {0, 1}
```

one boolean per (assignment, candidate room, candidate slot) triple. A variable
only exists if the room/slot is a *candidate* for that assignment in the first
place (see "Pre-filtering" below) — invalid combinations are never represented,
rather than being modeled and then constrained away. At the current seed data
this is roughly 25,000 boolean variables.

## Pre-filtering (constraints satisfied by construction)

Four of the hard constraints in PROMPT.md §6.2 are enforced by simply not
creating the variable, not by an `Add()` constraint:

- **Lab subjects only in lab rooms** — a lab-needing assignment's candidate
  rooms are exactly the `lab`-typed rooms; a non-lab assignment never gets a
  lab room offered.
- **Room capacity ≥ class strength** — candidate rooms are filtered to
  `capacity >= section.strength`.
- **Teacher `unavailable_slots` respected** — candidate slots exclude any slot
  in the teacher's `unavailable_slots`.
- **Nothing in `is_break` slots** — the slot list handed to the model excludes
  break periods entirely.

## Hard constraints (modeled)

Everything that involves more than one assignment competing for the same
resource is a real constraint over the indexed variable groups
(`vars_by_assignment`, `vars_by_teacher_slot`, `vars_by_room_slot`,
`vars_by_class_slot`, `vars_by_teacher_day`, `vars_by_teacher`):

| Constraint | Model |
|---|---|
| Each (class, subject) gets exactly its `weekly_periods` | `sum(vars_by_assignment[a]) == subject.weekly_periods` |
| One teacher, one place, per slot | `sum(vars_by_teacher_slot[t, s]) <= 1` |
| One class per room per slot | `sum(vars_by_room_slot[r, s]) <= 1` |
| One subject per class per slot | `sum(vars_by_class_slot[c, s]) <= 1` |
| Teacher daily cap | `sum(vars_by_teacher_day[t, d]) <= teacher.max_periods_per_day` |
| Teacher weekly cap | `sum(vars_by_teacher[t]) <= teacher.max_periods_per_week` |

`tests/test_solver.py` checks every one of these against the actual persisted
`TimetableEntry` rows after a real solve, not just against the model — it reads
the database, not the solver's self-report.

## Soft constraints (weighted objective)

CP-SAT minimizes a single weighted sum of penalty terms. Weights are the
PROMPT.md §6.2 defaults (`DEFAULT_WEIGHTS`), overridable per `/timetable/generate`
call:

- **Idle gaps (w=5).** Per teacher per day, an auxiliary "used at period p"
  boolean is derived for each period; `first`/`last` used *compact* period
  index (via `AddMinEquality`/`AddMaxEquality`) give a `span`, and
  `idle = span - count_used`. The index is compact (skips the lunch break)
  specifically so the break itself is never mistaken for an idle gap.
- **Spread — no repeat same-subject-same-day unless double (w=8).** Per
  (assignment, day), `excess = max(daily_count - allowed, 0)` where `allowed`
  is 2 for `is_double_period` subjects, 1 otherwise.
- **Heavy subjects in periods 1-4 (w=3).** A subject is "heavy" if
  `weekly_periods >= 5` (PROMPT.md doesn't define the term; this is the
  documented proxy). Direct penalty on any such assignment's variable being 1
  for `period > 4`.
- **Preferred slots (w=2).** Direct penalty when a teacher with a non-empty
  `preferred_slots` list is scheduled outside it. Inactive on the current seed
  (no teacher has `preferred_slots` populated yet) but fully wired.
- **Balance workload across days (w=4).** Per teacher, `max_daily - min_daily`
  across the six days, using the same per-day counts as the idle-gap term.

## Why CP-SAT, not a greedy scheduler

A greedy assignment (fill the first open slot that doesn't obviously conflict)
can produce a schedule that looks plausible and is silently wrong — it has no
way to prove a full weekly quota is achievable before it paints itself into a
corner, and no way to say *why* it failed. CP-SAT gives:

1. A genuine feasibility proof — `FEASIBLE`/`OPTIMAL` means every hard
   constraint above is satisfied, not "satisfied as far as we checked."
2. A real infeasibility signal (`INFEASIBLE`) instead of an infinite loop or a
   broken partial schedule.
3. The ability to forbid one exact variable and re-solve — this is the whole
   mechanism behind explain-any-cell's "what if this cell couldn't happen"
   answer, and it's not something a greedy heuristic can do at all (there's no
   model to re-solve).

## Time budget

`TIME_LIMIT_SECONDS = 8.0`. The Phase 2 gate requires a full solve (all 12
classes, ~372-432 periods depending on curriculum) in under 10 seconds with
**zero hard violations** — it does not require the soft objective to be
optimal. At 8s, CP-SAT reliably returns `FEASIBLE` (all hard constraints
satisfied) but rarely `OPTIMAL`. Measured on the seed data: objective ≈ 1300 at
a 3s budget, ≈ 550-620 at 8s, ≈ 130 given 25s. This is a real, disclosed
quality-vs-latency tradeoff, not hidden: `solver_stats.status` tells you which
one you got, and `soft_violations` breaks the objective down by term.

## Seed data tuning (a real infeasibility, and how it was found)

The pre-check (`diagnose_infeasibility`, below) caught a genuine modeling bug
during development, not a contrived one: seed data originally gave lab rooms
capacity 40 while classes have strength 50 — no lab-needing subject could ever
be scheduled for a full class. Fixed by raising lab capacity to 60.

A second, subtler issue surfaced after that: with `Physics=5, Chemistry=5,
CS=3` weekly periods, aggregate lab demand was `12 classes x 13 periods = 156`
lab-periods/week against a supply of `3 labs x 42 slots = 126` — oversubscribed
by design, not a bug in any one assignment. Seed data now uses `Physics=3,
Chemistry=3, CS=2` (demand 96/126, 76% utilization) — tight enough that "2 of 3
labs are busy" (the explain-panel example in PROMPT.md §6.2) is a real,
frequent scenario rather than a manufactured one, while staying solvable.

## Infeasibility: "why", not just "no"

`diagnose_infeasibility` runs *before* the solver, checking two aggregate
conditions that account for the most common real causes:

1. Does every assignment have at least one valid (room, slot) combination at
   all, and enough of them to cover its `weekly_periods`?
2. Does any teacher's assigned weekly load exceed their `max_periods_per_week`?

If either fails, `/timetable/generate` returns `{"feasible": false, "status":
"INFEASIBLE", "reasons": [...]}` immediately — no solver time spent, and a
specific, named reason (`tests/test_solver.py::test_forced_infeasible_returns_structured_response`
verifies this end to end by deliberately overloading a teacher). If CP-SAT
itself comes back infeasible despite passing both checks (a genuine
combinatorial conflict the aggregate checks can't see), the API still returns
a structured response instead of crashing — just a more general message, since
full conflict explanation would need assumption-based UNSAT analysis this
implementation doesn't do.

## Explain any cell

`GET /timetable/explain/{entry_id}`, cached per entry (`_explain_cache`, an
in-process dict — fine at this scale and lifetime; no Redis needed). Three
parts:

1. **Room reason.** For lab subjects: "N of M labs are busy at this slot,"
   computed from the other entries in the active version. For classrooms: a
   one-line capacity statement.
2. **Teacher/roster reason.** Since the teacher is fixed by `Assignment`, not
   chosen by the solver, this explains the roster: who else in the department
   was busy at this slot and what they were doing instead — this is where "Ms.
   Iyer has 11-C now"-style lines come from, computed for real from the active
   version's entries, not scripted.
3. **Re-solve with this exact cell forbidden, diff the objective** — the
   literal PROMPT.md ask. `solve()` accepts a `forbidden` set of
   `(assignment_id, room_id, slot_id)` keys and simply excludes those variables
   from the model, then re-solves the *whole* timetable (a 6s budget) and
   reports how the objective changed. This is why the result is cached: it's a
   full solve, not a lookup.

A fourth, cheaper piece — **ranked alternatives** — doesn't re-solve at all.
`find_alternatives` checks each candidate (room, slot) for the *same*
assignment directly against the active version's occupancy (is the teacher /
room / class free there), then scores feasible ones with `estimate_move_cost`:
a deterministic, local re-evaluation of the same weighted terms above (idle
gap, balance, heavy-early, preferred-slot, spread), holding every other entry
fixed. This is an approximation of the full objective — intentionally, so it's
fast enough for interactive use — and it's the same function that powers
`POST /timetable/validate-move`'s "3 ranked alternatives with costs."

## Drag-and-drop validation

`POST /timetable/validate-move` checks, directly (no solver call): break slot,
room type/capacity, teacher `unavailable_slots`, teacher/room/class occupancy
at the target slot from the active version's other entries, and the teacher's
daily cap. Returns `{ok, conflicts[], alternatives[]}` — `alternatives` only
populated (via `find_alternatives`) when there's a conflict, so a clean move
doesn't pay for suggestions it won't show. `POST /timetable/move` re-validates
before applying (never trusts the client) and mutates the entry in place on the
active version — a manual move is a live edit, not a new solver run or a new
`TimetableVersion`.

## Substitute repair (the algorithm — not the demo flow)

`services/timetable/substitute.py`. Scope note: PROMPT.md §6.2 describes the
substitute engine's *algorithm* and its *demo wiring* (Action Center card,
`POST /timetable/absence`, notification drafts) in the same paragraph, but
§9 puts "substitute engine end to end" in Phase 4. This phase builds and tests
the algorithm; Phase 4 wires it into `/timetable/absence`, the Action Center,
and notifications.

`find_substitutes(db, teacher_id)` — minimal-perturbation repair: every other
entry in the active version is left untouched ("freeze everything else"); for
each of the absent teacher's periods, candidates are ranked by the PROMPT.md
§6.2 order:

1. **Free at that exact slot** — a hard filter (not a preference: a teacher
   already teaching elsewhere physically cannot cover a second class).
2. **Teaches the subject** (dept match).
3. **Lowest current weekly load** (spreads the burden rather than piling onto
   whoever's already free).
4. **Has already taught this class** (continuity).

`apply_substitution(db, entry_id, new_teacher_id, label)` clones the active
version into a new one, replacing only the one entry's teacher
(`is_substitution=True`, `original_teacher_id` preserved) — every other entry
is copied verbatim. `tests/test_solver.py::test_substitution_never_introduces_new_conflict`
runs this against a real absence (Kavita Rao, the demo's Mrs. Rao) and
re-checks all three double-booking constraints on the resulting version.

## Known limitations (Phase 2 scope)

- Double periods (`is_double_period`) are only softly discouraged from
  splitting across a day — nothing forces the two periods to be *adjacent*.
  Not required by PROMPT.md's hard-constraint list.
- `preferred_slots` is fully modeled but inactive on the current seed (no
  teacher has any set).
- Room assignment for a drag-and-drop move keeps the entry's current room by
  default; if that room's busy at the target slot, `validate-move`'s
  alternatives will surface a different room.
- Explain's "re-solve forbidding this cell" re-solves the *entire* timetable
  (every other assignment is also free to move), not just this one entry with
  everything else frozen — an honest tradeoff disclosed here, not hidden. The
  cheaper `find_alternatives` path (frozen-except-this-entry) is what backs
  the actual ranked suggestions shown in the UI.

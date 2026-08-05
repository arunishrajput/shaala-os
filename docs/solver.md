# The Timetable Solver

> **Status: not written yet.** This document is scoped to be written in Phase 2,
> immediately after the CP-SAT model is built, while the constraint set is fresh
> (per CLAUDE.md's "files you own" list and PROMPT.md §9 Phase 2). It will cover, in
> prose: the decision variables, every hard constraint, the weighted soft-constraint
> objective, why CP-SAT over a greedy/heuristic scheduler, and how `solver_stats`
> (wall time, branches, objective value, soft violations) are computed and surfaced.

# Puzzles Manual Taxonomy Review

Current active scope: `domain=puzzles`, covering public task ids that start with
`task_puzzles__`.

## Current Status

- Active puzzle tasks: `80`
- Generated taxonomy proposal: `80` public task units
- Split tasks: `0`
- Rename-only tasks: `0`
- Current puzzle query rows: `104`
- Puzzle rows with unknown answer/annotation schemas: `0`
- Review artifacts live under `review/task-reviews/puzzles/...`.

## Scope Boundary

Earlier retired puzzle/notation review notes mixed puzzle tasks with notation
and probability tasks that now live under `misc`. This active review covers
only `task_puzzles__...` tasks. `task_misc__...` tasks must be audited under
the `misc` domain.

## Follow-Up

If a future audit finds a puzzle task-boundary violation, update the source
seeds and generated taxonomy artifacts together instead of hand-editing generated
CSV rows.

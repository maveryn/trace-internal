---
name: domain-temporal
description: Use when designing, implementing, or reviewing TRACE temporal-domain tasks, especially for clocks, calendars, schedules, timelines, and clean evidence contracts over time-structured visual artifacts.
---

# Temporal Domain

Use this whenever the task lives under `domain=temporal`.

## Read first
1. `docs/domains/TEMPORAL_TASK_SETUP.md`
2. `docs/domains/TASK_FAMILY_VARIANTS.md`
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## V1 temporal-domain policy
- Keep the domain centered on familiar time-structured visual artifacts such as clocks, calendars, schedules, and timelines.
- Prefer one stable visual scaffold per task id; widen question diversity through `task_variant` before adding another task id with nearly the same scene grammar.
- Favor local, visually obvious evidence for early temporal tasks (for example clock hands, date cells, event blocks, or timeline markers).
- Use 12-hour analog clocks only in the first clock tasks; keep seconds out of scope until the domain has stronger baseline coverage.
- When a temporal query applies an offset or transformation to the displayed time, keep the displayed scene fixed and let the prompt carry the transformation.
- Prefer non-semantic visual variety through explicit style/color axes recorded in trace; do not let palette or chrome changes leak into the prompt contract unless the task is truly about color.

## Evidence heuristics
- Use `bbox_set` when the witness unit is one or more visible regions such as clock hands, calendar cells, event blocks, or timeline markers.
- Keep prompt-facing evidence local to the queried object whenever possible; if the answer comes from one displayed artifact, do not widen evidence to unrelated decorative regions.
- If a future temporal task truly needs ordered witnesses, make that order explicit in the prompt and verifier contract instead of relying on incidental layout order.

## Current coverage
- `clock`
  - `task_temporal_clock_readout`
  - `task_temporal_clock_compare`
- `calendar`
  - `task_temporal_calendar_month_view`

## Planned near-term coverage
- `schedule`
  - `task_temporal_schedule`
- `timeline`
  - `task_temporal_timeline`

## Shared helpers to prefer
- `trace/tasks/temporal/shared/time_format.py`
- `trace/tasks/temporal/shared/calendar_scene.py`
- `trace/tasks/temporal/shared/clock_scene.py`
- `trace/tasks/temporal/shared/style.py`
- `trace/tasks/temporal/shared/task_support.py`
- `trace/tasks/temporal/shared/visual_defaults.py`
- `trace/tasks/temporal/shared/complexity.py`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`

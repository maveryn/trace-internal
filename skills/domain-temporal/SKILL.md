---
name: domain-temporal
description: Use when designing, implementing, or reviewing TRACE temporal-domain tasks, especially for clocks, calendars, schedules, timelines, and clean evidence contracts over time-structured visual artifacts.
---

# Temporal Domain

Use this whenever the task lives under `domain=temporal`.

## Read first
1. `docs/domains/TEMPORAL_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- Treat `docs/domains/TEMPORAL_TASK_SETUP.md` as the active temporal contract; do not duplicate its family/task/evidence inventory here.
- Keep the domain centered on familiar time-structured visual artifacts: clocks, calendars, schedules, and timelines.
- Prefer one stable visual scaffold per task id; widen question diversity through `task_variant` before adding near-duplicate task ids.
- Keep offset/transformation queries in the prompt while the displayed temporal artifact remains fixed.
- Keep non-semantic style and color axes recorded in trace without changing the prompt contract.

## Practical review checklist
- Keep prompt-facing evidence local to the queried witness: clock hands, winning clock faces, date cells, schedule blocks, or timeline event cards.
- Use `bbox_set` for visible temporal witnesses and make any required ordering explicit in the prompt/verifier contract.
- Ensure prompt examples match offset, comparison, interval, and ordering semantics rather than reusing a direct-readout example.
- Reuse shared temporal helpers under `trace/tasks/temporal/shared/` before adding task-local scene or time-format utilities.
- Split only when a new temporal task changes the visual scaffold or witness semantics enough to be a healthy standalone task.

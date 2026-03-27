---
name: domain-tile
description: Use when designing, implementing, or reviewing TRACE tile-domain tasks, especially for board layout, coordinate grounding, tile evidence types, and tile-specific balancing rules.
---

# Tile Domain

Use this whenever the task lives under `domain=tile`.

## Read first
1. `docs/domains/TILE_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Tile-domain rules
- Concrete tile tasks stay flat under `trace/tasks/tile/<task_group>_<task_name>.py`.
- Tile-shared helpers live under `trace/tasks/tile/shared/`.
- Public tile coordinates are zero-based `(row, col)` with top-left origin.
- Pixel coordinates are top-left, zero-based.
- The board is the only grid-like scaffold unless the task contract explicitly requires another one.
- Default tile board range is `3..7` unless the task has a documented reason to narrow or fix it.
- Rectangular boards are standard; movement/path tasks should use square cells so each step has equal visual cost.
- Named color prompts should use the shared `name [#RRGGBB]` formatter.

## Design heuristics
- Prefer `grid_point_set` or `grid_point_path` evidence over pixel-primary evidence.
- When board size strongly constrains answer support, use target-first sampling or exact constructive realization.
- Keep prompt-facing evidence minimal and store richer partitions/groups in trace.
- Reuse tile-shared render/background/noise helpers instead of creating per-task wrappers.

## Coverage reference
For current tile coverage and active task families, use:
- `docs/project/STATUS.md`
- `docs/domains/TASK_FAMILY_VARIANTS.md`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`

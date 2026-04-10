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

## Active-contract reminders
- Treat `docs/domains/TILE_TASK_SETUP.md` as the active board-geometry, coordinate, and evidence contract.
- Keep concrete tile task modules flat under `trace/tasks/tile/<task_group>_<task_name>.py`.
- Keep public tile coordinates zero-based `(row, col)` with top-left origin; pixel geometry is derived evidence only.
- Prefer `grid_point_set` and `grid_point_path` as prompt-facing evidence for rectangular tile tasks.
- Use square cells for movement/path tasks when rectangular cells would make equal-cost steps visually misleading.

## Practical review checklist
- Make the board coordinate system discoverable with row/column gutters when prompts or evidence use coordinates.
- Keep the board as the only grid-like scaffold unless the task contract explicitly requires another one.
- Use target-first sampling or exact constructive realization when board size strongly constrains answer support.
- Keep prompt-facing evidence minimal and store richer components, regions, paths, or partitions in trace metadata.
- Reuse tile-shared helpers under `trace/tasks/tile/shared/` before adding task-local render, graph, color, or noise utilities.

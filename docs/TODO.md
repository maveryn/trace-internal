# TRACE TODO

## Now
1. Keep `docs/ACTIVE_TASK_INVENTORY.md` as the only exhaustive active task and scene inventory.
2. Keep skills as operational overlays; canonical policy and contracts stay in `docs/`.
3. When active task, scene, registry, or taxonomy changes land, regenerate the inventory and run the docs consistency checks.

## Next
1. Close task-review and solve-rate artifact coverage gaps reported by `scripts/audit_active_tasks.py`.
2. Continue complexity calibration under the current gates in `plans/CALIBRATION_PLAN.md`.
3. Continue scene-by-scene puzzle/game rendering upgrades for repeated-cell, repeated-token, board, tile, sticker, voxel, and grid renderers.
4. Apply the same evidence-safe rendering-style and layout-jitter principles to other domains where the main content sits inside a larger canvas.
5. Continue rolling out domain-owned task complexity policy and replace remaining task-local ad hoc `complexity_score` formulas.
6. Add cross-domain `scene_variant` and role-binding guidance to architecture/ABI docs where task docs still rely on domain-local wording.
7. Improve dataset QA diagnostics and report summaries.

## Later
1. Add split-artifact generation with deterministic split-policy metadata.
2. Add richer dataset inspection tooling around trace shards and build reports.
3. Add future analytical geometry only as calibrated visual-family tasks with stable evidence contracts.
4. Add a geometry `estimate` task track only if it lands with a meaningfully different visual/evidence contract from existing exact-value geometry tasks.

## Deferred
1. Reward/tolerance policy tuning for RLVR scoring.
2. Polygon measurement variants not in current scope:
   - polygon diameter
   - polygon min-side / max-side

## Done At High Level
1. Core deterministic build/ABI/trace pipeline and strict-repro framework.
2. Validation/reporting baseline and error-code catalog.
3. External prompt-bundle system for active tasks.
4. Domain/task-group config loader and deterministic visual-variation infrastructure.
5. Task-review/sample-generation tooling with per-task artifacts and inspection workbooks.
6. Generated active task inventory at `docs/ACTIVE_TASK_INVENTORY.md`.

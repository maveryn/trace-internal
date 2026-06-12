# TRACE TODO

## Now
1. Continue fresh scene-package migration from `docs/SCENE_PACKAGE_MIGRATION/`.
2. Keep `docs/ACTIVE_TASK_INVENTORY.md` as the only exhaustive active task and scene inventory.
3. Keep skills as operational overlays; canonical policy and contracts stay in `docs/`.
4. When active task, scene, registry, or taxonomy changes land, regenerate the inventory and run the docs consistency checks.

## Next
1. Migrate remaining domains to scene-package layout, removing legacy routing, retired difficulty surfaces, stale review artifacts, and compatibility wrappers as each domain completes.
2. Add and maintain migration enforcement tests for objective ownership, identity-free shared code, prompt assets, config ownership, annotation contracts, and cross-scene/domain import boundaries.
3. Improve dataset QA diagnostics and report summaries.

## Later
1. After scene-package migration is complete, audit repo-local `skills/` so they reflect the final code-design principles instead of temporary migration workflow, then prepare reusable exportable skills for designing similar RL visual-reasoning environments in other domains.
2. Add split-artifact generation with deterministic split-policy metadata.
3. Add richer dataset inspection tooling around trace shards and build reports.
4. Add future analytical geometry only as calibrated visual-family tasks with stable annotation contracts.
5. Add a geometry `estimate` task track only if it lands with a meaningfully different visual/annotation contract from existing exact-value geometry tasks.

## Deferred
1. Reward/tolerance policy tuning for RLVR scoring.
2. Polygon measurement variants not in current scope:
   - polygon diameter
   - polygon min-side / max-side

## Done At High Level
1. Core deterministic build/ABI/trace pipeline and strict-repro framework.
2. Validation/reporting baseline and error-code catalog.
3. External prompt-bundle system for active tasks.
4. Domain/scene config loader and deterministic visual-variation infrastructure.
5. Task-review/sample-generation tooling with web-app inspection sidecars and optional static workbook exports.
6. Generated active task inventory at `docs/ACTIVE_TASK_INVENTORY.md`.

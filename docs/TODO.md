# TRACE TODO

## Now
1. Keep `docs/ACTIVE_TASK_INVENTORY.md` as the only exhaustive active task and scene inventory.
2. Keep skills as operational overlays; canonical policy and contracts stay in `docs/`.
3. When active task, scene, registry, or taxonomy changes land, regenerate the inventory and run the docs consistency checks.
4. Keep the frozen 1000-task train/test split in `docs/RLVR_TASK_SPLIT_PLAN.md` synchronized with intentional task-surface changes.

## Next
1. Create the real v0 training/eval dataset build config.
2. Run a full generation smoke pass from a clean output root.
3. Run solve-rate calibration and acceptance for all active tasks.
4. Run full dataset validation and review generated build reports.
5. Improve dataset QA diagnostics and report summaries.

## Later
1. Audit repo-local `skills/` periodically so they remain operational overlays
   over final docs instead of independent policy.
2. Add richer dataset inspection tooling around trace shards and build reports.
3. Add future analytical geometry only as calibrated visual-family tasks with stable annotation contracts.
4. Add a geometry `estimate` task track only if it lands with a meaningfully different visual/annotation contract from existing exact-value geometry tasks.

## Deferred
1. Reward/tolerance policy tuning for RLVR scoring.
2. Polygon measurement variants not in current scope:
   - polygon diameter
   - polygon min-side / max-side

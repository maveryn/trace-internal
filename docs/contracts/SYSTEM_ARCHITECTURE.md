# TRACE System Architecture

Implementation map for the contracts in `docs/contracts/BLUEPRINT.md`.

## 1) Runtime Layers
1. `trace/core/` — deterministic infrastructure: types, hashing, seeds,
   taxonomy, validation, build, reward contracts, reward scoring, and export.
2. `trace/core/prompts/` — prompt bundle loading, validation, selection, and
   rendering.
3. `trace/core/visual/` — deterministic shared background and post-image noise.
4. `trace/tasks/` — task registry plus concrete task implementations.
5. `trace/tasks/shared/` — cross-domain task helpers.
6. `trace/tasks/<domain>/shared/` — domain-wide helpers only when reused across
   multiple scenes in that domain.
7. `trace/tasks/<domain>/<scene_id>/` — scene-package task files and
   scene-local `shared/` helpers for migrated and review-candidate scenes.
8. `prompts/` — external prompt assets.
9. `configs/` — generation, rendering, prompt, and build configs.

Unmigrated scene packages may remain during migration. New review-candidate work
uses scene-package layout.

## 2) Runtime Data Flow
1. Load build config and type registry.
2. Resolve deterministic `dataset_id`.
3. Sample a public `task_id`.
4. Generate staged instances:
   - explicit task params from build config,
   - task-local query sampling,
   - public taxonomy resolution (`domain -> scene_id -> task_id`),
   - scene/task/query prompt rendering,
   - image rendering and visual variation,
   - answer and annotation binding from the same execution trace,
   - reward-contract resolution from public answer/annotation types,
   - sidecar trace write,
   - train-record write with `trace_ref`.
5. Optionally run strict-repro second pass and compare.
6. Run pre-finalize validation.
7. Write `validation_report.json` and `build_report.json`.
8. Atomically finalize on success; persist failure bundle on error.

## 3) Core Module Responsibilities
### Core Runtime
1. `trace/core/types.py` — ABI dataclasses.
2. `trace/core/canonical.py` and `trace/core/hash_utils.py` — canonical
   hashing.
3. `trace/core/seed.py` — seed derivation and spawn helpers.
4. `trace/core/identity.py` — `instance_id` computation.
5. `trace/core/type_registry.py` — answer/annotation type checks.
6. `trace/core/trace_store.py` — sidecar trace shard I/O.
7. `trace/core/validation.py` — pre-finalize dataset validation.
8. `trace/core/builder.py` — build orchestration.
9. `trace/core/build_presets.py` — reusable build recipes.
10. `trace/core/reward_contracts.py` — public reward-contract resolver.
11. `trace/core/reward_scoring.py` — shared TRACE answer/annotation scoring.
12. `trace/core/rlvr_export.py` — TRACE-to-RLVR export helpers.
13. `trace/core/taxonomy.py` — public taxonomy and implementation/source
    routing metadata.
14. `trace/core/strict_repro.py` — strict reproducibility comparisons.
15. `trace/core/scene_config.py` — config resolver for unmigrated scene
    packages and compatibility paths.
16. `trace/core/sampling.py` — shared sampling primitives.
17. `trace/core/json_io.py` — deterministic JSON writing.

### Prompt And Visual
1. `trace/core/prompts/assets.py` — prompt bundle loading/cache.
2. `trace/core/prompts/schema.py` — prompt schema validation.
3. `trace/core/prompts/select.py` — deterministic variant selection.
4. `trace/core/prompts/render.py` — strict rendering and metadata.
5. `trace/core/visual/background.py` — background style selection/rendering.
6. `trace/core/visual/noise.py` — post-image noise selection/application.
7. `trace/core/visual/defaults.py` — visual defaults loading.

### Task Framework
1. `trace/tasks/registry.py` — registration and creation.
2. `trace/tasks/base.py` — task protocol and `TaskOutput`.
3. `trace/tasks/shared/*` — cross-domain query, layout, annotation, config,
   prompt, and output helpers.
4. `trace/tasks/<domain>/<scene_id>/<objective_contract>.py` — one public task
   file per migrated or review-candidate task.
5. `trace/tasks/<domain>/<scene_id>/shared/*` — scene-local reusable state,
   sampling, rendering, prompt-slot, annotation, and output helpers.
6. `trace/tasks/<domain>/shared/*` — helpers reused by multiple scenes in one
   domain, never a dumping ground for one scene's task routing.

## 4) Active Task Inventory
The active public task surface is generated from the live registry and
taxonomy. Do not enumerate current tasks or scenes in this architecture doc.

Use `docs/ACTIVE_TASK_INVENTORY.md` for the committed generated inventory of
`domain -> scene_id -> task_id`. Regenerate it with:

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py
```

## 5) Architecture Invariants
1. Determinism from config, seeds, code versions, prompt assets, and visual
   assets.
2. `TrainInstance` stays lightweight; heavy replay metadata stays in sidecar
   trace.
3. Public records expose `domain`, `scene_id`, and task identity. Source routing
   metadata is debug/runtime metadata only.
4. Answer, annotation, and witness metadata are consistent from one execution
   trace.
5. Shared helpers are reused before adding task-local utilities, but shared code
   must stay identity-free.
6. Public task files own objective-specific construction, answer binding,
   annotation binding, prompt slots, trace payload, and final `TaskOutput`.
7. Builder parallelism changes throughput only; dataset identity and finalized
   row ordering stay invariant for fixed build-critical config.

## 6) When To Update This Doc
Update when module boundaries, build lifecycle, shared invariants, or extension
points change. Do not update this doc for ordinary task additions/removals; use
the generated inventory and domain/task docs instead.

# TRACE System Architecture

Implementation map for the contracts in `docs/BLUEPRINT.md`.

## 1) Layered structure
1. `trace/core/` — deterministic infrastructure (types, hashing, seeds, validation, build).
2. `trace/core/prompts/` — prompt bundle loading/rendering/selection.
3. `trace/core/visual/` — deterministic background + post-image noise.
4. `trace/tasks/` — task registry + concrete task implementations.
5. `trace/tasks/shared/` — cross-domain task helpers.
6. `trace/tasks/<domain>/shared/` — domain/task-family shared helpers.
7. `prompts/` — external prompt assets.
8. `configs/` — domain/task-group defaults and build configs.

## 2) Runtime data flow
1. Load build config + type registry.
2. Resolve deterministic `dataset_id`.
3. Generate staged instances:
   - task sampling,
   - task-level parameter injection (including deterministic `_sampling_index` for balance-aware variant samplers),
   - prompt rendering,
   - image rendering + visual variation,
   - trace write,
   - train-record write with `trace_ref`.
4. Optional strict-repro second pass + compare.
5. Run pre-finalize validation.
6. Write `validation_report.json` and `build_report.json`.
7. Atomic finalize on success; failure bundle on error.

## 3) Core module responsibilities
### Core runtime
1. `trace/core/types.py` — ABI dataclasses.
2. `trace/core/canonical.py` + `trace/core/hash_utils.py` — canonical hashing.
3. `trace/core/seed.py` — seed derivation/spawn helpers.
4. `trace/core/identity.py` — `instance_id` computation.
5. `trace/core/type_registry.py` — answer/evidence type checks.
6. `trace/core/trace_store.py` — sidecar trace shard I/O.
7. `trace/core/validation.py` — pre-finalize dataset validation.
8. `trace/core/builder.py` — build orchestration.
9. `trace/core/strict_repro.py` — strict reproducibility comparisons.
10. `trace/core/task_group_config.py` — merged domain/task-group defaults and section resolution (`shared` + `task_overrides`).
11. `trace/core/sampling.py` — shared sampling primitives.
12. `trace/core/json_io.py` — deterministic JSON writing.

### Prompt + visual
1. `trace/core/prompts/assets.py` — bundle loading/cache.
2. `trace/core/prompts/schema.py` — schema validation.
3. `trace/core/prompts/select.py` — deterministic variant selection.
4. `trace/core/prompts/render.py` — strict rendering + metadata.
5. `trace/core/visual/background.py` — background style selection/render.
6. `trace/core/visual/noise.py` — post-image noise selection/apply.
7. `trace/core/visual/defaults.py` — visual defaults loader.

### Task framework
1. `trace/tasks/registry.py` — registration and creation.
2. `trace/tasks/base.py` — task protocol and `TaskOutput`.
3. `trace/tasks/shared/*` — reusable query/layout/evidence/config/prompt helpers.
4. `trace/tasks/<domain>/<task_group>/*.py` — concrete tasks plus reusable task-group bases (for example `trace/tasks/geometry/measurement/shape_measure_base.py`).

## 4) Current active tasks
1. `trace/tasks/tile/path/shortest_path.py`
2. `trace/tasks/geometry/measurement/angle.py`
3. `trace/tasks/geometry/measurement/area.py`
4. `trace/tasks/geometry/measurement/perimeter.py`
5. `trace/tasks/geometry/measurement/length.py`
6. `trace/tasks/geometry/measurement/slope.py`
7. `trace/tasks/geometry/analytical_2d/area.py`
8. `trace/tasks/geometry/analytical_2d/length.py`
9. `trace/tasks/geometry/analytical_2d/perimeter.py`
10. `trace/tasks/geometry/analytical_3d/volume.py`
11. `trace/tasks/geometry/analytical_3d/surface_area.py`

## 5) Architecture invariants
1. Determinism from config + seeds + versions.
2. `TrainInstance` stays lightweight; heavy replay metadata stays in sidecar trace.
3. Answer/evidence/witness are consistent from one execution trace.
4. Shared helpers are reused before adding task-local utilities.

## 6) When to update this doc
Update when:
1. module boundaries move,
2. build lifecycle flow changes,
3. shared invariants or extension points change.

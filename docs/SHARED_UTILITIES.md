# TRACE Shared Utilities

Use this document to prevent duplicate helper implementations.

## 1) Placement policy
Choose the narrowest reusable layer:
1. `trace/core/*` — cross-system infrastructure (hashing, seeds, validation, build).
2. `trace/tasks/shared/*` — cross-domain task logic.
3. `trace/tasks/<domain>/shared/*` — domain/task-family logic.
4. task-local module — only truly task-specific behavior.

Promote helpers when a second consumer appears.

## 2) Canonical shared modules
### Core
1. `trace/core/canonical.py`, `trace/core/hash_utils.py`, `trace/core/identity.py`
2. `trace/core/seed.py`, `trace/core/sampling.py`
3. `trace/core/type_registry.py`, `trace/core/validation.py`
4. `trace/core/builder.py`, `trace/core/strict_repro.py`
5. `trace/core/task_group_config.py`, `trace/core/json_io.py`, `trace/core/query_types.py`
   - `task_group_config` resolves merged defaults and section-level `shared` + `task_overrides` composition.
6. `trace/core/prompts/*` and `trace/core/visual/*`

### Task-shared
1. `trace/tasks/shared/value_queries.py`
2. `trace/tasks/shared/value_query_sampling.py`
3. `trace/tasks/shared/layout_constraints.py`
4. `trace/tasks/shared/geometry_primitives.py`
5. `trace/tasks/shared/bbox_projection.py`
6. `trace/tasks/shared/graph_algorithms.py`
7. `trace/tasks/shared/config_defaults.py`
   - Resolves effective `generation`/`rendering`/`prompt` defaults from task-group config by merging section `shared` + `task_overrides.<task_id>`.
8. `trace/tasks/shared/visual_defaults.py`
9. `trace/tasks/shared/prompt_variants.py`
10. `trace/tasks/shared/output_metadata.py`

### Domain-shared (current)
1. Geometry: `trace/tasks/geometry/shared/graph_paper.py`, `graph_rendering.py`, `angle_geometry.py`
2. Tile: `trace/tasks/tile/shared/path_grid.py`, `maze_sampling.py`, `grid_layout.py`, `maze_scene.py`, `maze_rendering.py`

## 3) Reuse rules
1. Do not duplicate deterministic utilities.
2. Prefer importing canonical helpers over wrappers.
3. Prefer shared canonical type aliases (for example `geometry_primitives.Point`) over equivalent local redefinitions.
4. Keep module `__all__` limited to externally consumed symbols.
5. Keep internal helper steps private until they have external consumers.
6. If shared APIs change, update docs in the same change.

## 4) Quick review checklist
1. Did we search shared modules first?
2. Is this helper at the right layer?
3. Are we exposing only needed public API?
4. Did we update docs that reference helper placement?

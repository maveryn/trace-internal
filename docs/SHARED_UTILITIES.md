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
5. `trace/core/task_group_config.py`, `trace/core/json_io.py`
   - `task_group_config` resolves merged defaults and section-level `shared` + `task_overrides` composition.
6. `trace/core/answer_distribution.py`
   - Canonical answer-distribution degeneracy checks used by `scripts/check_task_answer_distribution.py`.
7. `trace/core/review_overlays.py`
   - Canonical review/sample overlay helpers for projecting evidence into pixel space and drawing workbook previews.
   - Use this from review/sample scripts instead of duplicating evidence-type adapters or marker rendering logic.
8. `trace/core/prompts/*` and `trace/core/visual/*`
   - `trace/core/visual/ranges.py` is the canonical visual-layer range parser for integer min/max normalization.

### Task-shared
1. `trace/tasks/shared/geometry_primitives.py`
2. `trace/tasks/shared/bbox_projection.py`
3. `trace/tasks/shared/graph_algorithms.py`
4. `trace/tasks/shared/config_defaults.py`
   - Resolves effective `generation`/`rendering`/`prompt` defaults from task-group config by merging section `shared` + `task_overrides.<task_id>`.
   - `required_group_default` / `required_group_defaults` are the canonical fail-fast helpers for required config keys (avoid hardcoded in-code fallback literals for required prompt/config slots).
   - `resolve_optional_int_bounds` is the canonical helper for optional inclusive integer bounds (for example `answer_min`/`answer_max`).
   - `resolve_required_int_bounds` / `resolve_required_float_bounds` are the canonical helpers for required numeric min/max pairs.
5. `trace/tasks/shared/visual_defaults.py`
6. `trace/tasks/shared/prompt_variants.py`
7. `trace/tasks/shared/output_metadata.py`
8. `trace/tasks/shared/text_rendering.py`
   - Canonical text/font helpers plus overlap-aware label placement (`resolve_text_label_center`) for geometry annotations.
9. `trace/tasks/shared/mcq.py`
10. `trace/tasks/shared/sequence.py`
   - Canonical deterministic sequence transforms (for example rotation) used by multiple tasks/domains.
11. `trace/tasks/shared/color_distance.py`
   - Canonical color-distance helpers (`rgb` + Lab CIE76/ΔE\*ab) and constrained color sampling for visibility-safe task styling.
   - Includes shared palette sampling (`sample_color_palette_with_distance_constraints`) that enforces anchor + pairwise separation.
   - Global defaults live here (`color_min_distance=60`, `color_distance_space=lab`) and can be overridden by task params/config hierarchy.
12. `trace/tasks/shared/prompt_json_example.py`
   - Canonical deterministic JSON-example builder for prompt slots (`answer_only` + `answer_and_evidence`) that preserves active evidence schema shape/cardinality.
   - For point-based evidence payloads, it emits small canonical non-degenerate layouts so prompt examples remain visually/semantically valid.
13. `trace/tasks/shared/deterministic_sampling.py`
   - Canonical deterministic index selection for target-support cycling.
   - Use `_sampling_index` when a caller explicitly requests balanced cycling; otherwise use a namespaced hash so target-answer selection does not accidentally correlate with other seed-driven decisions.

### Domain-shared (current)
1. Geometry: `trace/tasks/geometry/shared/graph_paper.py`, `graph_rendering.py`, `single_object_scene.py`, `angle_geometry.py`, `polygon_geometry.py`, `slope_geometry.py`, `shape_style.py`, `background_defaults.py`, `noise_defaults.py`, `variant_sampling.py`, `render_variation.py`, `annotation_values.py`, `labeled_point_evidence.py`, `point_labels.py`, `prompt_text.py`, `analytical_2d_scene.py`, `analytical_3d_solids.py`, `analytical_task.py`
   - `graph_paper.offset_point_by_grid_vector` is the canonical pixel-space translation helper for lattice vector offsets.
   - `background_defaults.load_geometry_background_defaults(...)` is the canonical geometry-domain loader for background defaults (domain baseline with optional task-group override).
   - `noise_defaults.load_geometry_noise_defaults(...)` is the canonical geometry-domain loader for post-image noise defaults (domain baseline with optional task-group override).
   - `shape_style.py` is the canonical geometry ink-style sampler and applies Lab-distance constraints against background anchor colors.
   - `render_variation.py` is the canonical integer render-range sampler (for example line-width ranges).
   - `annotation_values.py` provides canonical value formatting + structured annotation->value evidence map helpers for analytical geometry tasks.
   - `labeled_point_evidence.py` provides canonical graph-point evidence payload builders for labeled maps (`grid_point_map`), single graph points (`graph_point`), and unlabeled graph-point sets (`graph_point_set`), while keeping projected pixel-space helpers (`pixel_point_map`, `pixel_point_set`, `pixel_point_path`) plus grid-space projections in trace.
   - `point_labels.py` provides overlap-aware labeled-point rendering helpers reused by conic/point-evidence tasks.
   - `prompt_text.py` provides canonical prompt-fragment helpers such as `append_required_labels_clause(...)` so label-list suffixes keep consistent punctuation across geometry tasks.
   - `slope_geometry.py` provides reusable slope-line feasibility/sampling helpers for graph-paper slope tasks.
   - `analytical_2d_scene.py` provides reusable analytical 2D scene fitting, collision-aware annotation/label placement, and shared polygon/circle/helper rendering for annotated analytical objectives.
   - Use `fill_kind="shaded"` / `fill_kind="background"` on analytical polygon entities when a shaded-region objective needs persistent filled target regions or visible cutouts; keep that fill behavior in the shared analytical scene helper rather than bespoke task-local drawing.
   - `analytical_3d_solids.py` provides reusable 3D-solid rendering/sampling helpers shared by analytical 3D objectives (currently `volume` and `surface_area`).
   - `analytical_task.py` provides shared prompt-slot, answer-bound, and variant-resolution helpers reused by analytical geometry task modules.
2. Geometry measurement task-group: `trace/tasks/geometry/measurement/defaults.py`, `shape_measure_base.py`, `trace/tasks/geometry/shared/conic_geometry.py`, `trace/tasks/geometry/shared/length_geometry.py`
   - `defaults.py` centralizes task-group fallback defaults reused by measurement tasks.
   - `shape_measure_base.py` provides the shared generation/output pipeline for shape variants (polygon + conic) used by area/perimeter tasks.
   - `variant_sampling.py` in `trace/tasks/geometry/shared/` provides shared balanced variant-selection helpers reused across geometry task groups.
   - `conic_geometry.py` provides reusable circle/ellipse sampling, rendering, and scene-entity payload helpers.
   - `length_geometry.py` provides reusable integer-length segment vectors, sampling, and labeled-segment rendering helpers.
   - `polygon_geometry.py` provides reusable procedural polygon sampling plus feasible-target support probes for polygon-side measurement tasks, constructive triangle/quadrilateral area helpers and triangle-perimeter helpers for graph-paper measurement tasks, and conservative interior-span calculations for padded graph-paper placement.
   - Use `required_graph_cells_for_polygon_side_length(...)` when a task selects a polygon-side target before layout so the chosen target also carries forward the minimum graph span it needs.
   - Use `feasible_quadrilateral_area_values(...)`, `required_graph_cells_for_quadrilateral_area(...)`, and `sample_quadrilateral_instance_with_area_on_graph_paper(...)` when a task needs target-first 4-gon area sampling without violating the shared integer-perimeter polygon contract.
   - Procedural polygon templates reject adjacent collinear vertices so sampled `n`-gons do not collapse into visually degenerate lower-side polygons.
3. Tile: `trace/tasks/tile/shared/path_grid.py`, `maze_sampling.py`, `grid_layout.py`, `maze_scene.py`, `maze_rendering.py`

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

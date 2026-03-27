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
12. `trace/tasks/shared/color_format.py`
   - Canonical prompt-facing color text helpers (`#RRGGBB` formatting and `name [#RRGGBB]` labels) for any task that queries or names colors in the prompt.
13. `trace/tasks/shared/prompt_json_example.py`
   - Canonical deterministic JSON-example builder/resolver for prompt slots (`answer_only` + `answer_and_evidence`) that preserves active evidence schema shape/cardinality.
   - For point-based evidence payloads, it emits small canonical non-degenerate layouts so prompt examples remain visually/semantically valid.
14. `trace/tasks/shared/deterministic_sampling.py`
   - Canonical deterministic index selection for target-support cycling.
   - Use `_sampling_index` when a caller explicitly requests balanced cycling; otherwise use a namespaced hash so target-answer selection does not accidentally correlate with other seed-driven decisions.
14. `trace/tasks/shared/comparison_sampling.py`
   - Canonical winner/runner-up gap metrics for comparison-style tasks.
   - Use `compute_comparison_gap_metrics(...)` and `comparison_gap_is_valid(...)` when a task needs one shared ambiguity rule over ranked scalar values.
15. `trace/tasks/shared/counting_sampling.py`
   - Canonical object-count / target-count balancing for counting-style tasks across domains.
   - Use `resolve_counting_cardinality_pair(...)` when the count answer itself should be sampled from the global feasible support before object-count/layout choice.

### Domain-shared (current)
1. Geometry: `trace/tasks/geometry/shared/graph_paper.py`, `graph_rendering.py`, `single_object_scene.py`, `angle_geometry.py`, `multi_angle_scene.py`, `polygon_geometry.py`, `slope_geometry.py`, `shape_style.py`, `background_defaults.py`, `noise_defaults.py`, `variant_sampling.py`, `render_variation.py`, `annotation_values.py`, `labeled_point_evidence.py`, `point_labels.py`, `prompt_text.py`, `analytical_2d_scene.py`, `analytical_3d_solids.py`, `analytical_task.py`
   - `graph_paper.offset_point_by_grid_vector` is the canonical pixel-space translation helper for lattice vector offsets.
   - `background_defaults.load_geometry_background_defaults(...)` is the canonical geometry-domain loader for background defaults (domain baseline with optional task-group override).
   - `noise_defaults.load_geometry_noise_defaults(...)` is the canonical geometry-domain loader for post-image noise defaults (domain baseline with optional task-group override).
   - `shape_style.py` is the canonical geometry ink-style sampler and applies Lab-distance constraints against background anchor colors.
   - `render_variation.py` is the canonical integer render-range sampler (for example line-width ranges).
   - `annotation_values.py` provides canonical value formatting + structured annotation->value evidence map helpers for analytical geometry tasks.
   - `labeled_point_evidence.py` provides canonical graph-point evidence payload builders for labeled maps (`grid_point_map`), single graph points (`graph_point`), and unlabeled graph-point sets (`graph_point_set`), while keeping projected pixel-space helpers (`pixel_point_map`, `pixel_point_set`, `pixel_point_path`) plus grid-space projections in trace.
   - `point_labels.py` provides overlap-aware labeled-point rendering helpers reused by conic/point-evidence tasks.
   - `graph_rendering.graph_units_to_pixel(...)` is the canonical graph-unit-to-pixel projection helper once more than one task group needs hidden graph-unit layout coordinates.
   - `prompt_text.py` provides canonical prompt-fragment helpers such as `append_required_labels_clause(...)` so label-list suffixes keep consistent punctuation across geometry tasks.
   - `slope_geometry.py` provides reusable slope-line feasibility/sampling helpers for graph-paper slope tasks.
   - `multi_angle_scene.py` provides reusable target-conditioned multi-angle geometry construction plus object-label placement for sibling angle tasks across geometry task groups.
   - `multi_polygon_scene.py` provides reusable outline + object-label rendering for sibling multi-polygon scenes across geometry task groups.
   - `quadrilateral_prototypes.py` provides reusable centered quadrilateral-class samplers/classifiers shared by quadrilateral counting scenes and future mixed shape-type scenes.
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
   - `polygon_geometry.py` provides reusable procedural polygon sampling plus feasible-target support probes for polygon-side measurement tasks, constructive triangle/quadrilateral area helpers and triangle-perimeter helpers for graph-paper measurement tasks, conservative interior-span calculations for padded graph-paper placement, and strict polygon convexity classification (`convex` / `concave` / `degenerate`) for non-grid polygon-class tasks.
   - Use `required_graph_cells_for_polygon_side_length(...)` when a task selects a polygon-side target before layout so the chosen target also carries forward the minimum graph span it needs.
   - Use `feasible_quadrilateral_area_values(...)`, `required_graph_cells_for_quadrilateral_area(...)`, and `sample_quadrilateral_instance_with_area_on_graph_paper(...)` when a task needs target-first 4-gon area sampling without violating the shared integer-perimeter polygon contract.
   - Procedural polygon templates reject adjacent collinear vertices so sampled `n`-gons do not collapse into visually degenerate lower-side polygons.
3. Geometry comparison task-group: `trace/tasks/geometry/comparison/shared.py`, `trace/tasks/geometry/comparison/defaults.py`, `trace/tasks/geometry/comparison/rectangle_scene.py`
   - `comparison/shared.py` provides canonical query/object-count/winner-label balancing for geometry comparison tasks plus graph-paper slot placement helpers; use it once a second comparison task would otherwise duplicate the same label-choice scaffolding.
   - Use `slot_centers_graph_units(...)` for line-like comparison scenes and `bulky_slot_centers_graph_units(...)` when objects have larger footprints (for example rectangles) and need a roomier two-column layout.
   - `comparison/defaults.py` centralizes task-group fallback defaults reused across geometry/comparison tasks.
   - `comparison/rectangle_scene.py` provides reusable target-conditioned rectangle sampling, layout, and rendering for sibling rectangle-based comparison tasks (currently area and perimeter); keep object-family samplers/renderers there instead of duplicating near-identical task-local scene builders.
4. Geometry counting task-group: `trace/tasks/geometry/counting/shared.py`, `trace/tasks/geometry/counting/defaults.py`
   - `trace/tasks/shared/counting_sampling.py` now owns the cross-domain count-balancing helpers (`resolve_counting_object_count(...)`, `resolve_counting_target_count(...)`, `resolve_counting_cardinality_pair(...)`, `resolve_counting_target_first_cardinality_triplet(...)`, `resolve_counting_target_and_distractor_triplet(...)`, `counting_complexity_score(...)`).
   - `trace/tasks/shared/labeling.py` owns the cross-domain shuffled scene-label helper (`assign_shuffled_labels(...)`) and the shared `A..L` label pool used by multi-object families.
   - `counting/shared.py` keeps the geometry-specific roomy layout helpers plus a thin `assign_counting_labels(...)` wrapper over the shared label helper used by sibling geometry counting tasks.
   - `counting/defaults.py` centralizes task-group fallback defaults reused across geometry/counting tasks.
   - For class-counting tasks with overlapping school definitions (for example isosceles vs equilateral), keep the exclusive wording in prompt/config slots instead of relying on unstated conventions.
   - For polygon class-counting tasks such as convexity, use the shared strict classifier and reject `degenerate` near-flat/self-intersecting polygons instead of inventing one task-local visual heuristic.
   - `multi_shape_scene.py` provides reusable mixed polygon/circle/ellipse rendering plus object-label placement for sibling mixed-shape geometry scenes; use it when a second task needs the same object-family mix instead of creating another task-local renderer.
5. Tile: `trace/tasks/tile/shared/grid_graph.py`, `visual_defaults.py`, `maze_sampling.py`, `grid_layout.py`, `maze_scene.py`, `maze_rendering.py`, `tile_scene.py`, `tile_evidence.py`, `rectangular_board.py`, `tile_colors.py`, `named_color_board.py`, `reachability_board.py`, `trace/tasks/tile/shared/color_board_common.py`
   - `grid_graph.py` is the canonical 4-neighbor rectangular-tile graph helper layer (stable `cell_id`, open-grid adjacency, shortest-path adapters, and active-cell connected-components helpers).
   - `visual_defaults.py` is the canonical tile-domain background/noise loader layer shared across tile task groups.
   - `tile_scene.py` is the canonical dense-board `tile_cell` entity builder for non-maze tile tasks.
   - `tile_evidence.py` is the canonical coordinate-grounded tile evidence helper layer (`grid_point_set` / `grid_point_path` plus pixel projections).
   - `rectangular_board.py` is the canonical dynamic rectangular-board layout/rendering helper for single-board tile tasks.
   - `tile_colors.py` centralizes the named color palette used by color-driven tile tasks.
   - `named_color_board.py` is the canonical named-color board sampling/rendering layer shared across tile task groups, and it now owns the shared query-annotated scene-entity builder for named-color boards.
   - `reachability_board.py` is the canonical blocked-board reachability sampler for tile tasks that need one start tile plus reachable/unreachable open-cell partitions before task-specific target/path selection.
   - Concrete tile tasks live flat under `trace/tasks/tile/<task_group>_<task_name>.py`; keep reusable helpers under `trace/tasks/tile/shared/` instead of creating task-group wrapper packages for tile.
   - `color_board_common.py` now provides count-task adapters plus reusable per-color component analysis for flat tile tasks.
6. Icons: `trace/tasks/icons/shared/icon_assets.py`, `icon_noise.py`, `icon_scene.py`, `icon_style.py`, `icon_transform.py`, `icon_pair_grid_scene.py`, `trace/tasks/icons/counting/shared.py`
   - `icon_assets.py` is the canonical loader for the curated Prism icon bundle copied into `assets/icons/`; resolve pool membership through manifests rather than reconstructing SVG paths from task-local filename guesses.
   - `icon_noise.py` centralizes Prism-style per-icon subtle-noise sampling/application while preserving the icon alpha mask; use it for icon-instance perturbations instead of repurposing post-composite image noise helpers.
   - `icon_scene.py` provides the reusable two-panel `Reference` + `Scene` layout, panel geometry trace payloads, panel chrome rendering, random overlap-capped icon placement, and reading-order bbox canonicalization for sibling icon tasks.
   - `icon_style.py` provides curated-icon palette helpers that sample per-instance tints with Lab-distance separation from the panel/background chrome; keep Prism-style icon color policy there instead of re-implementing task-local palette samplers.
   - `icons/counting/shared.py` provides the shared render-param resolution, icon-instance noise sampling, and canonical trace-style block for sibling reference-scene icon counting tasks; reuse it once a second icon counting task would otherwise duplicate the same render-default parsing or style-trace assembly.
   - `icon_transform.py` is the canonical home for D4 transform ids and image-space transform application; use it for icon rotation/mirror families instead of encoding transform names task-locally.
   - `icon_pair_grid_scene.py` provides the reusable Reference-pair + labeled Scene-grid renderer for icon transformation-style tasks; use cell labels from this renderer as evidence instead of inventing task-local grid containers.

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

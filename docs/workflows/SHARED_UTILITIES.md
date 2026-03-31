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
   - `reconstruct_unique_shortest_path_by_adjacency(...)` is the canonical ordered-path reconstruction helper when tasks already have finalized adjacency plus BFS distance maps.
   - `unique_topological_order_by_adjacency(...)` is the canonical uniqueness checker for directed graph tasks that reason over one full topological order from finalized successor adjacency.
4. `trace/tasks/shared/config_defaults.py`
   - Resolves effective `generation`/`rendering`/`prompt` defaults from task-group config by merging section `shared` + `task_overrides.<task_id>`.
   - `required_group_default` / `required_group_defaults` are the canonical fail-fast helpers for required config keys (avoid hardcoded in-code fallback literals for required prompt/config slots).
   - `resolve_optional_int_bounds` is the canonical helper for optional inclusive integer bounds (for example `answer_min`/`answer_max`).
   - `resolve_required_int_bounds` / `resolve_required_float_bounds` are the canonical helpers for required numeric min/max pairs.
5. `trace/tasks/shared/visual_defaults.py`
6. `trace/tasks/shared/prompt_variants.py`
7. `trace/tasks/shared/output_metadata.py`
8. `trace/tasks/shared/text_rendering.py`
   - Canonical text/font helpers, compact text fitting (`fit_font_to_box`), contrast-preserving text outline selection (`resolve_text_stroke_fill`), and overlap-aware label placement (`resolve_text_label_center`) for geometry annotations and other in-figure labels.
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
   - `uniform_probability_map(...)` is the canonical helper for trace-facing finite-support probability maps once a second task needs the same deterministic support serialization.
15. `trace/tasks/shared/comparison_sampling.py`
   - Canonical winner/runner-up gap metrics for comparison-style tasks.
   - Use `compute_comparison_gap_metrics(...)` and `comparison_gap_is_valid(...)` when a task needs one shared ambiguity rule over ranked scalar values.
16. `trace/tasks/shared/counting_sampling.py`
   - Canonical object-count / target-count balancing for counting-style tasks across domains.
   - Use `resolve_counting_cardinality_pair(...)` when the count answer itself should be sampled from the global feasible support before object-count/layout choice.
   - `resolve_counting_target_and_distractor_triplet(...)` also supports target-conditioned distractor floors via `distractor_margin_over_target` when one family needs more negatives than positives for readable scenes.
17. `trace/tasks/shared/variant_sampling.py`
   - Canonical deterministic task-variant override/weight/balancing helpers across domains.
   - Use `resolve_variant(...)` plus `apply_balanced_variant_sampling(...)` instead of keeping parallel per-domain variant samplers.
   - Use `sampling_namespace=...` when one task needs more than one independently balanced variant axis (for example semantic variant plus scene variant).
   - Use `resolve_compatible_scene_query_variants(...)` when a task exposes chart-style compatible `scene_variant` + `query_variant` axes; do not keep that compatibility resolver trapped inside one domain once a second domain needs it.
18. `trace/tasks/shared/support_sampling.py`
   - Canonical deterministic integer-support parsing and balanced support cycling across domains.
   - Use this when a second domain needs the same support-list resolution / balanced answer-choice behavior instead of copying a domain-local helper.
   - When a task balances multiple axes under the same review `_sampling_index`, use `namespace_explicit_sampling_index=True` so downstream support cycling uses a namespace-specific support-order permutation instead of aliasing the same raw review index while still preserving flat review-time support coverage.
19. `trace/tasks/shared/named_colors.py`
   - Canonical repo-wide named-color palette plus deterministic sampling helpers shared across domains.
   - Use this when a second domain needs the same stable prompt/render color inventory instead of reaching into another domain's helper layer.
20. `trace/tasks/shared/name_assets.py`
   - Canonical shared loader for vendored short-name manifests reused across domains (currently charts and tables).
   - Use this when a second domain needs the same visible short-name pool instead of keeping another domain-local asset loader.
21. `trace/tasks/shared/drawing.py`
   - Canonical small drawing primitives (`draw_arrow`, `draw_dashed_line`, `draw_centered_text`, `draw_rounded_rect`) once a second domain needs the same deterministic vector/text chrome.
   - If a domain-local wrapper remains for compatibility (for example puzzles), keep it as a thin re-export rather than a second implementation.
22. `trace/tasks/shared/isometric_projection.py`
   - Canonical cross-domain 3D-to-2D isometric projection helper reused by geometry analytical 3D rendering and puzzle spatial block-stack rendering.
   - Promote new isometric-view consumers here instead of duplicating projection math inside a domain-shared module.
23. `trace/tasks/shared/graph_point_evidence.py`
   - Canonical cross-domain graph-point evidence builders for labeled graph maps, single graph points, unordered `graph_point_set` payloads, and empty graph-point-set witnesses.
   - Use this when a second domain needs graph-paper point evidence instead of importing geometry-local evidence helpers across domains.

### Domain-shared (current)
1. Geometry: `trace/tasks/geometry/shared/graph_paper.py`, `graph_rendering.py`, `single_object_scene.py`, `angle_geometry.py`, `multi_angle_scene.py`, `polygon_geometry.py`, `slope_geometry.py`, `shape_style.py`, `background_defaults.py`, `noise_defaults.py`, `render_variation.py`, `annotation_values.py`, `labeled_point_evidence.py`, `point_labels.py`, `prompt_text.py`, `analytical_2d_scene.py`, `analytical_3d_solids.py`, `solid_scene.py`, `function_graph_scene.py`, `analytical_task.py`, `complexity.py`, `consolidated_sampling.py`, `consolidated_legacy.py`
   - `graph_paper.offset_point_by_grid_vector` is the canonical pixel-space translation helper for lattice vector offsets.
   - `background_defaults.load_geometry_background_defaults(...)` is the canonical geometry-domain loader for background defaults (domain baseline with optional task-group override).
   - `noise_defaults.load_geometry_noise_defaults(...)` is the canonical geometry-domain loader for post-image noise defaults (domain baseline with optional task-group override).
   - `shape_style.py` is the canonical geometry ink-style sampler and applies Lab-distance constraints against background anchor colors.
   - `render_variation.py` is the canonical integer render-range sampler (for example line-width ranges).
   - `annotation_values.py` provides canonical value formatting + structured annotation->value evidence map helpers for analytical geometry tasks.
   - `labeled_point_evidence.py` provides canonical graph-point evidence payload builders for labeled maps (`grid_point_map`), single graph points (`graph_point`), unlabeled graph-point sets (`graph_point_set`), and the canonical empty `graph_point_set` payload for zero-witness geometry count tasks, while keeping projected pixel-space helpers (`pixel_point_map`, `pixel_point_set`, `pixel_point_path`) plus grid-space projections in trace.
   - `point_labels.py` provides overlap-aware labeled-point rendering helpers reused by conic/point-evidence tasks, including avoidance of blocked segments and nearby point markers so labels stay off the figure itself when a clean placement exists.
   - `graph_rendering.graph_units_to_pixel(...)` is the canonical graph-unit-to-pixel projection helper once more than one task group needs hidden graph-unit layout coordinates.
   - `prompt_text.py` provides canonical prompt-fragment helpers such as `append_required_labels_clause(...)` so label-list suffixes keep consistent punctuation across geometry tasks.
   - `slope_geometry.py` provides reusable slope-line feasibility/sampling helpers for graph-paper slope tasks.
   - `multi_angle_scene.py` provides reusable target-conditioned multi-angle geometry construction plus object-label placement for sibling angle tasks across geometry task groups.
   - `multi_polygon_scene.py` provides reusable outline + object-label rendering for sibling multi-polygon scenes across geometry task groups.
   - `quadrilateral_prototypes.py` provides reusable centered quadrilateral-class samplers/classifiers shared by quadrilateral counting scenes and future mixed shape-type scenes.
   - `function_graph_scene.py` provides reusable graph-paper plotted-function rendering helpers for graphing-family geometry tasks; keep floating-point graph-unit projection, function polyline drawing, and dashed horizontal guide-line rendering there instead of rebuilding those helpers task-locally.
   - `complexity.py` is the shared geometry-domain complexity layer; it owns normalized `[0, 1]` score construction, config-weight resolution, and the active family builders for migrated geometry tasks (currently comparison, counting, measurement, analytical_2d, analytical_3d, coordinate, solid, and graphing), while task modules still own the task-local raw-to-normalized measurements that feed those shared builders.
   - `analytical_2d_scene.py` provides reusable analytical 2D scene fitting, collision-aware annotation/label placement, and shared polygon/circle/helper rendering for annotated analytical objectives.
   - Use `fill_kind="shaded"` / `fill_kind="background"` on analytical polygon entities when a shaded-region objective needs persistent filled target regions or visible cutouts; keep that fill behavior in the shared analytical scene helper rather than bespoke task-local drawing.
   - `analytical_3d_solids.py` provides reusable 3D-solid rendering/sampling helpers shared by analytical 3D objectives (currently `volume` and `surface_area`).
   - `solid_scene.py` provides reusable cube-stack sampling plus isometric/orthographic rendering helpers for solid-view geometry tasks; keep cube occupancy growth, orthographic projection-cell derivation, and query-panel bbox projection there instead of rebuilding them inside each solid-view family.
   - `analytical_task.py` provides shared prompt-slot and answer-bound helpers reused by analytical geometry task modules.
   - `consolidated_sampling.py` is the canonical scene/query-axis resolver for consolidated geometry tasks; use it when a geometry family exposes chart-style `scene_variant` + `query_variant` sampling instead of re-implementing compatibility filtering per task.
   - `consolidated_legacy.py` is the canonical adapter layer for consolidated geometry tasks that delegate to legacy geometry generators while rewriting trace metadata to the active `scene_variant` / `query_variant` contract, including the review-facing `task_variant` probability fields that inspection/distribution tooling reads back later.
   - `polygon_transformations.py` is the canonical lattice-polygon transform helper for geometry tasks that reason over rigid transforms or similarity; keep asymmetric template sampling plus rigid/uniform/anisotropic polygon transforms and congruence/similarity checks there instead of encoding those transforms directly inside each geometry task.
   - `polygon_scene_helpers.py` is the canonical graph-paper polygon projection/reference-rendering helper for geometry families that reuse the same Reference-plus-candidates scaffold; keep point projection, polygon visibility checks, and `Reference` label rendering there instead of cloning those task-local helpers.
2. Geometry measurement task-group: `trace/tasks/geometry/measurement/defaults.py`, `shape_measure_base.py`, `trace/tasks/geometry/shared/conic_geometry.py`, `trace/tasks/geometry/shared/length_geometry.py`
   - `defaults.py` centralizes task-group fallback defaults reused by measurement tasks.
   - `shape_measure_base.py` provides the shared generation/output pipeline for shape variants (polygon + conic) used by area/perimeter tasks.
   - Keep measurement-family complexity scoring in `trace/tasks/geometry/shared/complexity.py`; `shape_measure_base.py` should only compute normalized per-task criteria (for example variant scan/precision/ambiguity signals) and pass them through the shared builder instead of reintroducing task-local weighted score formulas.
   - `conic_geometry.py` provides reusable circle/ellipse sampling, rendering, and scene-entity payload helpers.
   - `length_geometry.py` provides reusable integer-length segment vectors, sampling, and labeled-segment rendering helpers.
   - `polygon_geometry.py` provides reusable procedural polygon sampling plus feasible-target support probes for polygon-side measurement tasks, constructive triangle/quadrilateral area helpers and triangle-perimeter helpers for graph-paper measurement tasks, conservative interior-span calculations for padded graph-paper placement, and strict polygon convexity classification (`convex` / `concave` / `degenerate`) for non-grid polygon-class tasks.
   - Use `required_graph_cells_for_polygon_side_length(...)` when a task selects a polygon-side target before layout so the chosen target also carries forward the minimum graph span it needs.
   - Use `feasible_quadrilateral_area_values(...)`, `required_graph_cells_for_quadrilateral_area(...)`, and `sample_quadrilateral_instance_with_area_on_graph_paper(...)` when a task needs target-first 4-gon area sampling without violating the shared integer-perimeter polygon contract.
   - Procedural polygon templates reject adjacent collinear vertices so sampled `n`-gons do not collapse into visually degenerate lower-side polygons.
3. Geometry comparison task-group: `trace/tasks/geometry/comparison/shared.py`, `trace/tasks/geometry/comparison/defaults.py`, `trace/tasks/geometry/comparison/rectangle_scene.py`
   - `comparison/shared.py` provides canonical query/object-count/winner-label balancing for geometry comparison tasks plus graph-paper slot placement helpers; keep family-level complexity math out of this module now that geometry-shared `complexity.py` owns scoring policy.
   - Use `slot_centers_graph_units(...)` for line-like comparison scenes and `bulky_slot_centers_graph_units(...)` when objects have larger footprints (for example rectangles) and need a roomier two-column layout.
   - `comparison/defaults.py` centralizes task-group fallback defaults reused across geometry/comparison tasks.
   - `comparison/rectangle_scene.py` provides reusable target-conditioned rectangle sampling, layout, and rendering for sibling rectangle-based comparison tasks (currently area and perimeter); keep object-family samplers/renderers there instead of duplicating near-identical task-local scene builders.
4. Geometry counting task-group: `trace/tasks/geometry/counting/shared.py`, `trace/tasks/geometry/counting/defaults.py`
   - `trace/tasks/shared/counting_sampling.py` now owns the cross-domain count-balancing helpers (`resolve_counting_object_count(...)`, `resolve_counting_target_count(...)`, `resolve_counting_cardinality_pair(...)`, `resolve_counting_target_first_cardinality_triplet(...)`, `resolve_counting_target_and_distractor_triplet(...)`, `counting_complexity_score(...)`).
   - `trace/tasks/shared/labeling.py` owns the cross-domain scene-label helpers, including prefix-based shuffled labels (`assign_shuffled_labels(...)`) and random uppercase-subset labels (`assign_random_shuffled_labels(...)`) for families that should not bias toward `A, B, C, ...`.
   - `counting/shared.py` keeps the geometry-specific roomy layout helpers plus a thin `assign_counting_labels(...)` wrapper over the shared label helper used by sibling geometry counting tasks; keep counting-family complexity scoring in `trace/tasks/geometry/shared/complexity.py` instead of re-exporting the generic cross-domain count proxy once geometry counting tasks migrate.
   - `counting/defaults.py` centralizes task-group fallback defaults reused across geometry/counting tasks.
   - For class-counting tasks with overlapping school definitions (for example isosceles vs equilateral), keep the exclusive wording in prompt/config slots instead of relying on unstated conventions.
   - For polygon class-counting tasks such as convexity, use the shared strict classifier and reject `degenerate` near-flat/self-intersecting polygons instead of inventing one task-local visual heuristic.
   - `multi_shape_scene.py` provides reusable mixed polygon/circle/ellipse rendering plus object-label placement for sibling mixed-shape geometry scenes; use it when a second task needs the same object-family mix instead of creating another task-local renderer.
5. Graph: `trace/tasks/graph/shared/graph_sampling.py`, `graph_scene.py`, `task_support.py`, `style.py`, `visual_defaults.py`, `complexity.py`
  - `graph_sampling.py` is the canonical simple-graph topology sampler for graph-domain tasks; keep degree-support feasibility probes, disconnected-component construction, directed-reachability construction, unique-shortest-path construction, unicyclic/cycle samplers, bridge samplers, weighted-MST samplers, and articulation-point / unique-largest-component samplers there instead of cloning rejection loops per task.
  - `graph_scene.py` is the canonical labeled node-link graph renderer for graph-domain tasks; keep node/edge pixel geometry, panel chrome, layout fallback logic, and optional edge-weight label rendering there instead of task-local drawing.
  - `task_support.py` is the canonical graph-task support layer for balanced style-axis resolution and shared graph render-parameter defaults; if a second graph task needs the same node-shape / named-color / layout-transform plumbing, promote it there instead of copying task-local resolution code.
  - `style.py` is the canonical graph-domain visual-theme helper; keep named-color graph palettes and other non-semantic whole-image graph styling there instead of re-deriving per-task RGB themes.
  - `visual_defaults.py` is the canonical graph-domain background/noise loader layer shared across future graph task groups.
  - `complexity.py` is the shared graph-domain complexity layer; it owns normalized `[0,1]` score construction, config-weight resolution, and weighted-mean `TaskComplexity` construction, while graph tasks still own their task-local raw-to-normalized difficulty measurements.
6. Temporal: `trace/tasks/temporal/shared/time_format.py`, `calendar_scene.py`, `clock_scene.py`, `schedule_scene.py`, `timeline_scene.py`, `style.py`, `task_support.py`, `visual_defaults.py`, `complexity.py`
   - `time_format.py` is the canonical temporal-domain helper layer for 12-hour clock normalization, schedule/day-time formatting, timeline month/day labels, minute offsets, and reusable calendar/date labels such as weekday abbreviations or ordinal strings; keep wraparound and date-label rules there instead of re-encoding them per task.
   - `calendar_scene.py` is the canonical month-calendar renderer for temporal calendar tasks; keep date-cell geometry, month-grid layout, shared calendar render-param resolution, and date-cell trace projections there instead of task-local drawing.
   - `clock_scene.py` is the canonical analog-clock renderer for temporal clock tasks; keep hand geometry, face styling, shared clock render-param resolution, single-clock draw helpers, and hand-bbox/tip trace projections there instead of task-local drawing.
   - `schedule_scene.py` is the canonical single-day planner renderer for temporal schedule tasks; keep time-axis layout, lane assignment projections, shared schedule render-param resolution, and event-block trace geometry there instead of task-local drawing.
   - `timeline_scene.py` is the canonical milestone-timeline renderer for temporal timeline tasks; keep axis/event-card layout, shared timeline render-param resolution, and event-card trace projections there instead of task-local drawing.
   - `style.py` is the canonical temporal-domain visual-theme helper; keep named-color clock/calendar/schedule/timeline palettes and other non-semantic temporal styling there instead of re-deriving RGB themes per task.
   - `task_support.py` is the canonical temporal-task support layer for balanced named variant axes such as `task_variant` and `scene_variant`, plus stable sampling-index helpers reused across temporal tasks.
   - `visual_defaults.py` is the canonical temporal-domain background/noise loader layer shared across future temporal task groups.
   - `complexity.py` is the shared temporal-domain complexity layer; it owns normalized `[0,1]` score construction, config-weight resolution, and weighted-mean `TaskComplexity` construction, while temporal tasks still own their task-local raw-to-normalized difficulty measurements.
7. Tile: `trace/tasks/tile/shared/grid_graph.py`, `visual_defaults.py`, `maze_sampling.py`, `grid_layout.py`, `maze_scene.py`, `maze_rendering.py`, `tile_scene.py`, `tile_evidence.py`, `rectangular_board.py`, `tile_colors.py`, `named_color_board.py`, `reachability_board.py`, `trace/tasks/tile/shared/color_board_common.py`, `complexity.py`
   - `grid_graph.py` is the canonical 4-neighbor rectangular-tile graph helper layer (stable `cell_id`, open-grid adjacency, shortest-path adapters, and active-cell connected-components helpers).
   - `visual_defaults.py` is the canonical tile-domain background/noise loader layer shared across tile task groups.
   - `tile_scene.py` is the canonical dense-board `tile_cell` entity builder for non-maze tile tasks.
   - `tile_evidence.py` is the canonical coordinate-grounded tile evidence helper layer (`grid_point_set` / `grid_point_path` plus pixel projections).
   - `rectangular_board.py` is the canonical dynamic rectangular-board layout/rendering helper for single-board tile tasks.
   - `tile_colors.py` is the tile-domain wrapper over `trace/tasks/shared/named_colors.py`; keep tile-specific naming/query helpers there, but keep the canonical palette itself in the shared layer.
   - `named_color_board.py` is the canonical named-color board sampling/rendering layer shared across tile task groups, and it now owns the shared query-annotated scene-entity builder for named-color boards.
   - `reachability_board.py` is the canonical blocked-board reachability sampler for tile tasks that need one start tile plus reachable/unreachable open-cell partitions before task-specific target/path selection.
   - Concrete tile tasks live flat under `trace/tasks/tile/<task_group>_<task_name>.py`; keep reusable helpers under `trace/tasks/tile/shared/` instead of creating task-group wrapper packages for tile.
   - `color_board_common.py` now provides count-task adapters plus reusable per-color component analysis for flat tile tasks.
   - `complexity.py` is the shared tile-domain complexity layer; it owns normalized `[0,1]` helper transforms, complexity-weight resolution, and weighted-mean `TaskComplexity` construction, while each tile task still owns its task-local raw-to-normalized difficulty mapping.
8. Icons: `trace/tasks/icons/shared/defaults.py`, `icon_assets.py`, `icon_noise.py`, `icon_scene.py`, `icon_task_rendering.py`, `icon_style.py`, `icon_transform.py`, `icon_grid_scene.py`, `icon_sequence_scene.py`, `icon_single_panel_labeled_grid_scene.py`, `icon_pair_grid_scene.py`, `icon_overlap_grid_scene.py`, `icon_labeled_grid_scene.py`, `anchor_marking.py`, `complexity.py`
   - `icon_assets.py` is the canonical loader for the curated Prism icon bundle copied into `assets/icons/`; resolve pool membership through manifests rather than reconstructing SVG paths from task-local filename guesses.
   - `defaults.py` centralizes fallback defaults shared across icon task groups; keep shared panel/layout/noise defaults there instead of importing them from one task-group-named module once another icon family reuses them.
   - `icon_noise.py` centralizes Prism-style per-icon subtle-noise sampling/application while preserving the icon alpha mask; use it for icon-instance perturbations instead of repurposing post-composite image noise helpers.
   - `icon_scene.py` provides the reusable two-panel `Reference` + `Scene` layout, panel geometry trace payloads, panel chrome rendering, random overlap-capped icon placement, explicit nominal-size support for tasks that reason about icon scale, and reading-order bbox canonicalization for sibling icon tasks.
   - Reuse `random_paste_bbox(...)`, `overlap_fraction_smaller(...)`, and `max_overlap_with_existing(...)` from `icon_scene.py` when a second icon task needs custom constrained placement rather than cloning overlap math task-locally.
   - `icon_task_rendering.py` provides shared render-param resolution (including labeled-cell chrome defaults used by sequence and pattern tasks), common icon-style trace serialization, and deterministic per-instance noise sampling across icon task groups; keep those helpers here rather than under a `counting`-named module once relation/sequence/transformation/pattern tasks reuse them.
   - `icon_style.py` provides curated-icon palette helpers that sample per-instance tints with Lab-distance separation from the panel/background chrome; keep Prism-style icon color policy there instead of re-implementing task-local palette samplers.
   - `icon_style.sample_single_icon_tint(...)` is the canonical single-color sampler for icon tasks that intentionally keep one shared tint across the whole scene.
   - `icon_transform.py` is the canonical home for D4 transform ids and image-space transform application; use it for icon rotation/mirror families instead of encoding transform names task-locally.
   - `icon_grid_scene.py` provides reusable compact labeled-grid slot layouts, explicit fixed-grid slot layouts, plus horizontal row slot layouts for icon tasks whose semantic unit is the cell rather than one free-placed icon.
   - `icon_sequence_scene.py` provides the reusable single-panel sequence-row renderer for icon tasks that show a horizontal row of cell boxes; keep row-cell placement, dynamic row-box sizing, visible cell-label chrome, one-box `?` rendering, and sequence-cell icon serialization there instead of cloning them inside each sequence task.
   - `icon_single_panel_labeled_grid_scene.py` provides reusable single-panel labeled-grid chrome plus canvas sizing for icon tasks whose semantic unit is a numbered cell in one grid; use it for 2D pattern-style tasks instead of cloning grid chrome from the two-panel relation helpers or stretching the sequence-row renderer beyond its row-only contract.
   - `icon_pair_grid_scene.py` provides the reusable Reference-pair + labeled Scene-grid renderer for icon transformation-style tasks; use cell labels from this renderer as evidence instead of inventing task-local grid containers.
   - `icon_overlap_grid_scene.py` provides the reusable Reference-overlap + labeled Scene-grid renderer for pairwise occlusion-order tasks; use cell labels from this renderer when the semantic target is the whole overlapping pair rather than one icon bbox.
   - `icon_labeled_grid_scene.py` provides reusable two-panel `Reference` + labeled `Scene` grid chrome for icon tasks that render whole cell images task-locally; use it when the task-specific logic is inside each cell rather than in one generic pair/overlap widget, and use its square-cell options when diagonal cell symmetries need square reference/scene boxes without task-local geometry hacks.
   - `anchor_marking.py` provides the reusable highlighted-anchor outline + label renderer for icon relation tasks with visible anchors; once a second icon relation task marks anchors, keep that chrome shared instead of duplicating task-local rounded-box label placement.
   - `complexity.py` provides the icon-domain complexity-weight resolver plus normalized score builders for migrated icon tasks across the active counting, relation, transformation, sequence, and pattern families; keep icon complexity weights in `configs/domains/icons/*` and task-specific criterion measurement in code rather than copying weighted-score math into each task.
9. Charts: `trace/tasks/charts/shared/chart_scene.py`, `labeled_chart_common.py`, `distribution_chart_common.py`, `multiseries_chart_common.py`, `composition_chart_common.py`, `complexity.py`, `visual_defaults.py`
   - `chart_scene.py` is the canonical chart renderer for the active chart families; it owns the shared axis/grid scaffold plus mark/label trace geometry for single-series `area`, `bar`, `pie`, `donut`, `horizontal_bar`, `line`, `radar`, `scatter`, `dot_plot`, and `lollipop`, the active multiseries `grouped_bar`, `grouped_horizontal_bar`, `multi_line`, and `grouped_lollipop` renderers, the stacked-composition `stacked_bar` / `stacked_horizontal_bar` renderers, and the dedicated `histogram` / `boxplot` / `violin` distribution renderers.
   - `labeled_chart_common.py` is the shared construction layer for labeled single-series chart tasks; it owns mark-count/value bounds, balanced semantic/scene variant sampling, randomized label/color sampling, per-slice pie/donut palette assignment, reusable percentage-composition builders for pie/donut, reusable statistic builders, reusable threshold/interval counting dataset builders, reusable two-label readout dataset builders, reusable ordered-sequence trend dataset builders, and the shared pixel-space mark-evidence projection used by chart review overlays.
   - `distribution_chart_common.py` is the shared construction layer for distribution-style chart tasks; it owns histogram bin construction, cumulative/interval count query setup, categorical boxplot summary construction, violin support/mode construction, and the fixed-scene distribution task defaults.
   - `multiseries_chart_common.py` is the shared construction layer for multiseries chart tasks; it owns series/category count bounds, per-series palette sampling, series/category label sampling, pairwise-comparison dataset construction, and category-grounded pixel-space evidence projection for multiseries review overlays.
   - `composition_chart_common.py` is the shared construction layer for composition-style chart tasks; it owns stacked/pie scene compatibility, stacked total/segment builders, combined-share composition builders, stacked mark-spec construction, and whole-stack / whole-chart evidence projection.
   - `complexity.py` is the shared chart-domain complexity layer; it owns the normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction, while each chart task still owns its task-local raw-to-normalized transforms and scene-variant difficulty mapping.
   - Chart mark colors should be sampled once per instance and then reused consistently across all marks in that chart; keep the renderer wired to the resolved per-instance fill/outline colors rather than tracing one style and drawing another.
   - `visual_defaults.py` is the canonical chart-domain background/noise loader layer shared across future chart task groups.
10. Tables: `trace/tasks/tables/shared/table_scene.py`, `table_common.py`, `visual_defaults.py`
   - `table_scene.py` is the canonical styled-table renderer for active table tasks; it owns table cell geometry, row/column region bboxes, the full numeric-table region bbox, and the active `spreadsheet|zebra|ledger|card_table` scene variants.
   - `table_common.py` is the shared construction layer for table tasks; it owns row/column count bounds, row-name/header sampling, row/column/whole-table summary dataset construction, ranking/filtered-subset/relation/counting/readout dataset construction, temporal year-header sampling plus temporal dataset construction, canonical numeric-cell id resolution, render-param resolution, and both cell- and region-level bbox evidence projection.
   - `visual_defaults.py` is the canonical table-domain background/noise loader layer shared across future table task groups.
11. Puzzles: `trace/tasks/puzzles/shared/common.py`, `drawing.py`, `option_panels.py`, `option_layout.py`, `symbol_rendering.py`, `arithmetic_scene.py`, `balance_scene.py`, `grid_scene.py`, `logic_scene.py`, `paper_fold_scene.py`, `overlay_scene.py`, `block_stack_scene.py`, `bead_loop_scene.py`, `assembly_scene.py`, `arithmetic_common.py`, `logic_common.py`, `paper_fold_common.py`, `overlay_common.py`, `spatial_blocks_common.py`, `bead_loop_common.py`, `assembly_common.py`, `complexity.py`, `visual_defaults.py`
   - `common.py` provides canonical puzzle-axis resolution and prompt-facing bbox projection once more than one puzzle family needs the same deterministic variant/evidence helpers.
   - `drawing.py` provides the small centered-text and rounded-rectangle primitives shared by multiple puzzle scene renderers; use it when a second puzzle renderer needs the same deterministic text chrome instead of cloning local `_draw_centered_text` / `_rounded_rect` helpers again.
   - `option_panels.py` provides the reusable labeled image-option panel chrome for puzzle families that answer with `option_letter`; when a second puzzle family needs labeled image options, keep the label/content-box geometry shared here instead of duplicating task-local option-panel layout.
   - `option_layout.py` provides the canonical centered multi-row option layout for puzzle scenes with `5..6` or larger labeled choices; when a second puzzle family needs the same centered `3+2` or `3+3` image-choice layout, keep that row-count logic shared here instead of duplicating it inside another renderer.
   - `symbol_rendering.py` provides the canonical puzzle symbol vocabulary and shape-icon renderer reused across arithmetic and logic puzzle families; do not keep parallel shape palettes or box-icon drawers in task-local modules.
   - `arithmetic_scene.py` is the canonical boxed-slot equation renderer for active arithmetic equation puzzles; it owns slot/operator layout, scene chrome variants, slot bbox tracing, and the `equation_strip|equation_card|equation_outline` scene variants.
   - `balance_scene.py` is the canonical equality-panel arithmetic renderer for active balance-value puzzles; it owns stacked equality-panel layout, symbolic/numeric box rendering, explicit equals-token rendering, highlighted query-box layout, bbox tracing, and the `balance_strip|balance_card|balance_outline` scene variants.
   - `grid_scene.py` is the canonical arithmetic-grid renderer for active rule-grid puzzles; it owns fixed-column grid layout, card/outline scene chrome, cell bbox tracing, and the `grid_strip|grid_card|grid_outline` scene variants.
   - `arithmetic_common.py` is the shared arithmetic-puzzle helper layer; it owns arithmetic answer-bound resolution, task/scene variant resolution, boxed-equation dataset construction, arithmetic-grid dataset construction, equation/grid render-param resolution, and generic ordered puzzle-bbox evidence projection.
   - `logic_scene.py` is the canonical option-based logic-grid renderer for active logic puzzles; it owns square board layout, missing-cell styling, and option/cell bbox tracing for the `logic_strip|logic_card|logic_outline` scene variants while reusing the shared puzzle option-panel chrome.
   - `logic_common.py` is the shared logic-puzzle helper layer; it owns logic board-size bounds, logic render-param resolution, row/column/Latin-style board construction, explicit-rule adjacency board construction, deterministic correct-option placement, and the active logic-grid dataset builders.
   - `paper_fold_scene.py` is the canonical reference-plus-options renderer for active spatial paper-fold result puzzles; it owns the single-sheet layout, explicit fold arrows and fold-line chrome, bare labeled option-image layout, folded-result sheet rendering, and option/reference bbox tracing for the `fold_strip|fold_card|fold_outline` scene variants.
   - `paper_fold_common.py` is the shared paper-fold helper layer; it owns spatial fold-result defaults, scene-variant/render-param resolution, folded-result dataset construction, deterministic back-projection from folded packet to full sheet, and distractor generation for the active folded-result task.
   - `overlay_scene.py` is the canonical reference-plus-options renderer for active transparent-sheet overlay puzzles; it owns the two-source-sheet layout, centered bare option-image layout, plus-sign chrome, source/option mark drawing, and option/source bbox tracing for the `overlay_strip|overlay_card|overlay_outline` scene variants.
   - `overlay_common.py` is the shared transparent-sheet overlay helper layer; it owns source-sheet/grid bounds, overlap-aware union dataset construction, deterministic correct-option placement, distractor generation, and render-param resolution for the active overlay task and later overlay-style siblings.
   - `block_stack_scene.py` is the canonical fixed-view isometric block-comparison renderer for active cube-removal spatial puzzles; it owns visible-face rendering, side-by-side structure layout, captions/arrow chrome, and structure/face bbox tracing for the `stack_strip|stack_card|stack_outline` scene variants.
   - `spatial_blocks_common.py` is the shared block-stack helper layer; it owns stack-footprint/height bounds, per-cube face visibility bookkeeping, cube-removal dataset construction, and render-param resolution for the active cube-removal task and later block-stack siblings.
   - `assembly_scene.py` is the canonical renderer for active spatial assembly puzzles; it owns the top reference-piece row, the bottom labeled silhouette options, polyomino cell drawing, and piece/option bbox tracing for the `assembly_strip|assembly_card|assembly_outline` scene variants.
   - `assembly_common.py` is the shared assembly-puzzle helper layer; it owns piece/option count bounds, polyomino rotation canonicalization, exact rotation-only tiling checks, assembly dataset construction, and render-param resolution for the active assembly task and later cut-and-build siblings.
   - `bead_loop_scene.py` is the canonical reference-plus-options renderer for active topology bead-loop puzzles; it owns the reference-loop panel, bare option-loop image layout, loop/bead drawing, and reference/option bbox tracing for the `loop_strip|loop_card|loop_outline` scene variants.
   - `bead_loop_common.py` is the shared topology-puzzle helper layer; it owns bead-loop defaults, render-param resolution, cyclic-rotation equivalence checks, deterministic valid/invalid option construction, and the active bead-equivalence dataset builder.
   - `complexity.py` is the shared puzzle-domain complexity layer; it owns the normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction.
   - `visual_defaults.py` is the canonical puzzle-domain background/noise loader layer shared across future puzzle task groups.
12. Physics: `trace/tasks/physics/shared/circuit_scene.py`, `optics_scene.py`, `complexity.py`, `style.py`, `support_sampling.py`, `visual_defaults.py`
   - `circuit_scene.py` is the shared physics-domain resistor-network renderer; it owns terminal drawing, resistor-box rendering, optional red `?` missing-resistor rendering, wire layout, local-scene origin offsets, and prompt-facing bbox projection for active circuits tasks and later circuit siblings.
   - `optics_scene.py` is the shared physics-domain optics-board renderer; it owns board/grid rendering, source + mirror + target drawing, hidden solved-ray projection, and prompt-facing point grounding for optics tasks.
   - `complexity.py` is the shared physics-domain complexity layer; it owns normalized `[0,1]` score construction, complexity-weight resolution, and family builders for active physics tasks (currently mechanics, circuits, and optics reasoning, including spring-proportionality scenes).
   - `style.py` is the shared physics-domain named-theme layer; it owns reusable accent-color palettes for non-semantic physics styling (currently mechanics, spring cards, resistor-network scenes, and optics boards) so new physics tasks do not hardcode separate per-task color mixes.
   - `support_sampling.py` is the shared physics-domain integer-support resolver layer; use it when multiple physics tasks need the same deterministic support-list parsing and balanced answer cycling behavior instead of keeping parallel local helpers. When a physics task has a tiny fixed answer support and review collection samples consecutive seeds, prefer the helper's direct `instance_seed` cycling option over a hashed namespace-only cycle so per-variant distributions stay flat under task review; when a task balances multiple axes under the same review `_sampling_index`, use the helper's namespace-specific explicit-index decorrelation so scene/query cycling does not alias the answer support.
   - `visual_defaults.py` is the canonical physics-domain background/noise loader layer shared across future mechanics / circuits / optics task groups.
13. Games: `trace/tasks/games/shared/dots_boxes_common.py`, `dots_boxes_scene.py`, `bingo_common.py`, `bingo_scene.py`, `card_scene.py`, `domino_scene.py`, `reversi_common.py`, `reversi_scene.py`, `connect_four_common.py`, `connect_four_scene.py`, `checkers_common.py`, `checkers_scene.py`, `mancala_common.py`, `mancala_scene.py`, `morris_common.py`, `morris_scene.py`, `sampling.py`, `complexity.py`, `style.py`, `visual_defaults.py`
   - `dots_boxes_common.py` is the shared dots-and-boxes construction layer; it owns grid-edge geometry, forced-turn capture-chain construction, and deterministic captured-box witness projection for active dots-and-boxes tasks and later siblings.
   - `dots_boxes_scene.py` is the canonical dots-and-boxes renderer for active games dots-and-boxes tasks; it owns paper-board chrome, highlighted-edge drawing, dot/edge layout, and traced box/edge bbox maps.
   - `bingo_common.py` is the shared bingo-card construction layer; it owns `5 x 5` number-grid sampling, query-specific marked-cell construction, and deterministic completed-line witness projection for active bingo tasks and later bingo siblings.
   - `bingo_scene.py` is the canonical bingo-card renderer for active games bingo tasks; it owns card chrome, `B I N G O` headers, marked-cell drawing, and traced cell/column bbox maps.
   - `card_scene.py` is the shared games-domain face-up card-hand renderer; it owns centered one-row / two-row card layout, `REF` banner rendering, continuation-cue chrome, and card bbox tracing for card-hand tasks.
   - `domino_scene.py` is the shared games-domain domino renderer; it owns top-chain plus loose-tableau layout, pip drawing, `REF` tag / open-end highlight chrome, and domino bbox tracing for domino-chain tasks.
   - `reversi_common.py` is the shared games-domain Reversi rules helper layer; it owns board constants, legal-move evaluation, coordinate ids, and other rule-level helpers so future Reversi tasks reuse one canonical implementation.
   - `reversi_scene.py` is the shared games-domain Reversi renderer; it owns board layout, player badge rendering, disc chrome, marked-move overlays, and board-square bbox tracing for Reversi tasks.
   - `connect_four_common.py` is the shared games-domain Connect Four rules helper layer; it owns board constants, legal-drop evaluation, immediate-win detection, coordinate ids, and completed-line tracing so future Connect Four tasks reuse one canonical implementation.
   - `connect_four_scene.py` is the shared games-domain Connect Four renderer; it owns board layout, player badge rendering, disc chrome, marked-landing overlays, and board-square bbox tracing for Connect Four tasks.
   - `checkers_common.py` is the shared games-domain Checkers rules helper layer; it owns board constants, non-king movement/capture evaluation, coordinate ids, and other rule-level helpers so future Checkers tasks reuse one canonical implementation.
   - `checkers_scene.py` is the shared games-domain Checkers renderer; it owns board layout, player badge rendering, checker-piece chrome, and board-square bbox tracing for Checkers tasks.
   - `mancala_common.py` is the shared games-domain Mancala rules helper layer; it owns the canonical Blue-to-move sowing cycle, extra-turn detection, capture detection, and stable pit/store ids so future Mancala tasks reuse one visible-board semantics implementation.
   - `mancala_scene.py` is the shared games-domain Mancala renderer; it owns the wooden board layout, side-store/pit chrome, centered stone-count labels, player badge rendering, and pit/store bbox tracing for Mancala tasks.
   - `morris_common.py` is the shared nine-men's-morris construction layer; it owns the canonical `24`-node board geometry, mill definitions, feasible counted-piece supports, and deterministic visible board sampling for active Morris tasks and later siblings.
   - `morris_scene.py` is the canonical nine-men's-morris renderer for active games Morris tasks; it owns board-line drawing, node placement, piece rendering, and traced piece/node bbox maps.
   - `sampling.py` is the shared games-domain axis sampler layer; it owns the reusable balanced `query_variant` and named-axis resolution used across games task groups.
   - `complexity.py` is the shared games-domain complexity layer; it owns normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction for games tasks.
   - `style.py` is the shared games-domain theme layer; it owns reusable bingo / dots-and-boxes / card / domino / Reversi / Connect Four / Checkers / Mancala / Morris chrome, shadow, and highlight styling so new games tasks do not hardcode separate palettes.
   - `visual_defaults.py` is the canonical games-domain background/noise loader layer shared across future games task groups.
14. Diagrams: `trace/tasks/diagrams/shared/common.py`, `complexity.py`, `visual_defaults.py`, `flow_common.py`, `flow_scene.py`, `hierarchy_common.py`, `hierarchy_scene.py`, `cycle_common.py`, `cycle_scene.py`, `set_common.py`, `set_scene.py`, `schematic_common.py`, `schematic_scene.py`
   - `common.py` provides canonical diagrams-axis resolution, prompt-facing bbox projection, and shared panel/title helpers for diagram tasks that sample semantic and visual variants deterministically.
   - `complexity.py` is the shared diagrams-domain complexity layer; it owns the normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction.
   - `visual_defaults.py` is the canonical diagrams-domain background/noise loader layer shared across future diagrams task groups.
   - `flow_common.py` is the shared flow-diagram helper layer; it owns task/scene variant resolution, short visible process-label sampling, reusable topology templates, dataset construction, and render-param resolution for active flow tasks.
   - `flow_scene.py` is the canonical flowchart/swimlane renderer for active diagrams flow tasks; it owns panel/lane chrome, node and edge drawing, branch-label rendering, and traced lane/node/edge-label bbox maps.
   - `hierarchy_common.py` is the shared hierarchy-diagram helper layer; it owns task/scene variant resolution, reusable org-chart templates, deterministic label assignment, ancestor-query construction, and render-param resolution for active hierarchy tasks.
   - `hierarchy_scene.py` is the canonical org-chart renderer for active diagrams hierarchy tasks; it owns tree layout, connector routing, node drawing, and traced node/edge bbox maps.
   - `cycle_common.py` is the shared cycle-diagram helper layer; it owns task/scene variant resolution, short visible stage-label sampling, `5..10` stage ring construction, `k`-step before/after query construction, and render-param resolution for active cycle tasks.
   - `cycle_scene.py` is the canonical cycle-ring renderer for active diagrams cycle tasks; it owns panel/title chrome, clockwise badge rendering, directed edge drawing, stage placement, and traced stage/edge bbox maps.
   - `set_common.py` is the shared set-diagram helper layer; it owns task/scene variant resolution, numeric region-sum dataset construction, Lab-separated base set palette sampling, and render-param resolution for active set-diagram tasks.
   - `set_scene.py` is the canonical set-overlap renderer for active diagrams set tasks; it owns panel/title chrome, blended overlap-region drawing, set-label placement, digit placement, and traced region/digit bbox maps.
   - `schematic_common.py` is the shared schematic-diagram helper layer; it owns task/scene variant resolution, part-slot templates, annotated part/callout dataset construction, and render-param resolution for active schematic tasks.
   - `schematic_scene.py` is the canonical annotated schematic renderer for active diagrams schematic tasks; it owns chassis chrome, part drawing, callout-circle placement, leader routing, and traced part/callout/leader bbox maps.
15. Documents: `trace/tasks/documents/shared/common.py`, `complexity.py`, `visual_defaults.py`, `text_generation.py`, `document_common.py`, `sectioned_document_common.py`, `arithmetic_common.py`, `layout_common.py`, `relation_common.py`, `selection_common.py`, `document_scene.py`
   - `common.py` provides canonical documents-axis resolution and prompt-facing bbox evidence projection helpers for document tasks that sample semantic and visual variants deterministically.
   - `common.py` also owns the canonical field-spec and section-spec builders for structured document tasks that derive prompt/trace fields from typed visible values.
   - `complexity.py` is the shared documents-domain complexity layer; it owns the normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction.
   - `visual_defaults.py` is the canonical documents-domain background/noise loader layer shared across future document task groups.
   - `text_generation.py` is the shared typed field-value generator layer; it owns deterministic names, IDs, dates, contact strings, currency text, and coherent scene-level field-value sets for early structured documents.
   - `document_common.py` is the shared structured-document helper layer for document tasks; it owns task/scene variant resolution, the canonical scene-title mapping, readout scene field templates, document dataset construction for active field-lookup tasks, and render-param resolution for the shared form/invoice/receipt grammar.
   - `sectioned_document_common.py` is the shared section-aware field-template layer for the structured documents grammar reused by arithmetic and layout tasks; it owns the canonical sectioned field templates, target amount-section mapping, field-count bounds, and typed visible-value builders for grouped document scenes.
   - `arithmetic_common.py` is the shared section-local arithmetic helper layer; it owns supported arithmetic variants, expression-operator contracts, and deterministic expression-dataset construction for active document arithmetic tasks.
   - `layout_common.py` is the shared document-layout helper layer; it owns supported section-membership variants and deterministic dataset construction for tasks that answer with a section title based on a queried field cue.
   - `relation_common.py` is the shared section-local relation helper layer; it owns supported relation variants, scene-compatibility rules, section-local dataset construction, and deterministic winning-value selection for active document relation tasks.
   - `selection_common.py` is the shared checkbox-selection helper layer; it owns supported selection variants, scene-specific checkbox-group templates, typed context-field generation, and deterministic checkbox-state assignment for active document selection tasks.
   - `document_scene.py` is the canonical structured-document renderer for active documents tasks; it owns the form/invoice/receipt page grammars, fitted field-label/value rendering, optional section chrome, checkbox-section rendering, and page/section/field/checkbox bbox tracing.

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

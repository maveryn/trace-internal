# TRACE Shared Utilities

Use this document to prevent duplicate helper implementations.

## 1) Placement policy
Choose the narrowest reusable layer:
1. `trace/core/*` — cross-system infrastructure (hashing, seeds, validation, build).
2. `trace/tasks/shared/*` — cross-domain task logic.
3. `trace/tasks/<domain>/shared/*` — domain/scene logic.
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
   - Canonical bbox helpers for task-level pixel geometry: `round_bbox(...)`,
     `bbox_union(...)`, `bbox_union_many(...)`, raw/non-normalizing union
     adapters, `bbox_center(...)`, and projection adapters from entity ids to
     public point/bbox evidence.
   - Use these before adding task-local bbox rounding or union helpers.
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
   - Use `normalize_rgb(...)` / `coerce_rgb(...)` before adding local RGB clamping or fallback helpers.
   - Global defaults live here (`color_min_distance=60`, `color_distance_space=lab`) and can be overridden by task params/config hierarchy.
12. `trace/tasks/shared/color_format.py`
   - Canonical prompt-facing color text helpers (`#RRGGBB` formatting and `name [#RRGGBB]` labels) for any task that queries or names colors in the prompt.
13. `trace/tasks/shared/prompt_json_example.py`
   - Canonical deterministic JSON-example builder/resolver for prompt slots (`answer_only` + `answer_and_evidence`) that preserves active evidence schema shape/cardinality.
   - For point-based evidence payloads, it emits small canonical non-degenerate layouts so prompt examples remain visually/semantically valid.
14. `trace/tasks/shared/deterministic_sampling.py`
   - Canonical deterministic index selection for target-support cycling.
   - Use namespaced hashes so target-answer selection does not accidentally correlate with other seed-driven decisions.
   - `uniform_probability_map(...)` is the canonical helper for trace-facing finite-support probability maps once a second task needs the same deterministic support serialization.
15. `trace/tasks/shared/comparison_sampling.py`
   - Canonical winner/runner-up gap metrics for comparison-style tasks.
   - Use `compute_comparison_gap_metrics(...)` and `comparison_gap_is_valid(...)` when a task needs one shared ambiguity rule over ranked scalar values.
16. `trace/tasks/shared/counting_sampling.py`
   - Canonical object-count / target-count balancing for counting-style tasks across domains.
   - Use `resolve_counting_cardinality_pair(...)` when the count answer itself should be sampled from the global feasible support before object-count/layout choice.
   - `resolve_counting_target_and_distractor_triplet(...)` also supports target-conditioned distractor floors via `distractor_margin_over_target` when one family needs more negatives than positives for readable scenes.
17. `trace/tasks/shared/variant_sampling.py`
   - Canonical deterministic query-id override/weight/balancing helpers across domains.
   - Use `resolve_variant(...)` plus `apply_balanced_variant_sampling(...)` instead of keeping parallel per-domain variant samplers.
   - Balanced cycling must respect positive-probability variants only; zero-weight variants are disabled and should not re-enter through deterministic cycling.
   - Use `sampling_namespace=...` when one task needs more than one independently balanced variant axis (for example semantic variant plus scene variant).
   - Use `resolve_compatible_scene_query_ids(...)` when a task exposes constrained `scene_variant` + `query_id` axes; do not keep that resolver trapped inside one domain once a second domain needs it.
   - Use separate namespaces for scene/query axes so equal-size axes do not alias one-to-one.
18. `trace/tasks/shared/support_sampling.py`
   - Canonical deterministic integer-support parsing and balanced support cycling across domains.
   - Use this when a second domain needs the same support-list resolution / balanced answer-choice behavior instead of copying a domain-local helper.
   - When a task balances multiple axes, give each axis a separate namespace instead of reusing one raw seed stream.
19. `trace/tasks/shared/named_colors.py`
   - Canonical repo-wide named-color palette plus deterministic sampling helpers shared across domains.
   - Use this when a second domain needs the same stable prompt/render color inventory instead of reaching into another domain's helper layer.
20. `trace/tasks/shared/name_assets.py`
   - Canonical shared loader for vendored repo-wide label/name manifests reused across domains.
   - `assets/labels/` is the shared place for people, place, organization, synthetic, and mixed label pools with source/license metadata in `assets/labels/sources.json`; see `docs/workflows/SHARED_LABEL_ASSETS.md`.
   - Use `load_label_manifest(...)` plus task-local filters for length, spaces, and punctuation when a task needs visible labels, categories, names, edge labels, node labels, or legend strings.
   - Keep `load_short_name_manifest(...)` for the chart short-name manifest; new cross-domain label needs should prefer `assets/labels/`.
21. Shared context text assets
   - `assets/context_text/` is the shared place for non-answer visual chrome,
     captions, source notes, sidebar notes, callouts, decorative metric snippets,
     and distractor paragraphs with source/license metadata in
     `assets/context_text/sources.json`; see
     `docs/workflows/SHARED_CONTEXT_TEXT_ASSETS.md`.
   - Use these manifests for chart/page/graph context layers instead of
     hardcoding task-local filler text or downloading text at generation time.
   - When the first renderer consumes these manifests, add one shared loader at
     `trace/tasks/shared/context_text_assets.py`; do not create separate
     domain-local manifest parsers.
   - Every drawn context string must be recorded with role, bbox, manifest, and
     explicit answer-exclusion metadata unless the task verifier scopes it into
     the answer contract.
22. Shared font assets
   - `assets/fonts/` is the shared place for vendored permissively licensed font
     families with source/license metadata in `assets/fonts/sources.json`; see
     `docs/workflows/SHARED_FONT_ASSETS.md`.
   - Use `trace/tasks/shared/font_assets.py` to sample font families
     deterministically from seed/namespace and `trace/tasks/shared/text_rendering.py`
     to render them.
   - Meaningful text blocks should use internally consistent sampled fonts
     rather than per-word/per-glyph randomization. Record sampled families in
     render metadata for answer-bearing text.
23. `trace/tasks/shared/drawing.py`
   - Canonical small drawing primitives (`draw_arrow`, `draw_dashed_line`, `draw_centered_text`, `draw_centered_text_with_auto_stroke`, `draw_rounded_rect`) once a second domain needs the same deterministic vector/text chrome.
   - If a domain-local wrapper remains, keep it as a thin re-export rather than a second implementation.
24. `trace/tasks/shared/isometric_projection.py`
   - Canonical cross-domain 3D-to-2D isometric projection helper reused by geometry analytical 3D rendering and puzzle spatial block-stack rendering.
   - Promote new isometric-view consumers here instead of duplicating projection math inside a domain-shared module.
25. `trace/tasks/shared/graph_point_evidence.py`
   - Canonical cross-domain graph-paper-to-pixel point projection helpers for labeled graph maps, singleton points, unordered pixel point sets, and empty pixel point-set witnesses.
   - Use this when a second domain needs graph-paper points projected into public pixel evidence instead of importing geometry-local evidence helpers across domains.
26. `trace/tasks/shared/fixed_query.py`
   - Canonical public fixed-query wrapper helper for tasks backed by internal query branches.
   - Use `force_query_id_params(...)` when a domain wrapper needs to force one internal branch before generation.
   - Use `rewrite_public_query_output(...)` to expose the public wrapper contract: populated `query_id`, optional public `task_id` / `scene_id` rewrites, domain-selected probability metadata in `query_spec`, `execution_trace`, optional `render_spec`, scene relation metadata, optional scene-root identity metadata, and internal `query_id` replay metadata.
   - Domain-local modules such as `charts/shared/fixed_query_task.py`, `games/shared/fixed_query_task.py`, `geometry/shared/fixed_query_task.py`, `graph/shared/fixed_query_task.py`, `physics/shared/fixed_query_task.py`, `puzzles/shared/fixed_query_task.py`, `icons/shared/public_query_task.py`, `pages/shared/public_query_task.py`, and `puzzles/cell_board/merged_tasks.py` should be thin policy/name adapters over this helper, not independent rewrite implementations.

### Domain-shared (current)
1. Three-D: `trace/tasks/three_d/shared/color_variation.py`, `trace/tasks/three_d/shared/object_resources.py`, `trace/tasks/three_d/shared/task_support.py`
   - `color_variation.py` owns deterministic non-semantic object fill variation for synthetic 3D scenes. Use it when multiple three_d renderers need broader object color variety, and record resolved `fill_rgb` values in scene entities.
   - `object_resources.py` is the canonical named-object registry for the `three_d` domain. It owns object-scene shape pools, room wall/floor object pools, street object/context pools, warehouse object/context pools, prompt-facing display names, base dimensions, default non-semantic colors, canonical ids, scene-role profiles, resource-kind categories, support/mounting annotations, and reusable render-attribute pools such as warehouse robot/shelf style/color choices.
   - `task_support.py` owns repeated three_d sampling/scoring mechanics: scalar normalization, render/default scalar coercion, balanced axis-variant resolution, and integer count-support resolution. Scene geometry, camera construction, and object placement constraints stay in the scene/task modules.
   - Three-D scene modules may keep task-local placement slots, camera constraints, visibility thresholds, and verifier-specific filters, but reusable object identities, names, dimensions, non-semantic object colors, render-style axes, and allowed object subsets should come from `object_resources.py` instead of duplicated scene-local literals.
   - `ThreeDObjectProfile.resource_kind` distinguishes standalone resources from mounted, composite, variant, and semantic reference resources. Keep review inventories split by these categories so supported tabletop/wall variants are not confused with standalone small/large object classes.
2. Geometry: `trace/tasks/geometry/shared/graph_paper.py`, `graph_panel_layout.py`, `graph_rendering.py`, `single_object_scene.py`, `angle_geometry.py`, `multi_angle_scene.py`, `polygon_geometry.py`, `slope_geometry.py`, `shape_style.py`, `diagram_style.py`, `background_defaults.py`, `noise_defaults.py`, `render_variation.py`, `annotation_values.py`, `labeled_point_evidence.py`, `point_labels.py`, `prompt_text.py`, `measurement_rendering.py`, `coordinate_panel_grid.py`, `function_graph_scene.py`, `complexity.py`, `consolidated_sampling.py`, `consolidated_source.py`
   - `graph_paper.offset_point_by_grid_vector` is the canonical pixel-space translation helper for lattice vector offsets.
   - `graph_panel_layout.py` is the canonical bounded graph-paper panel placement layer for full coordinate-plane scenes. Use it to resolve `graph_panel_bbox_px`, `graph_content_bbox_px`, `graph_origin_px`, `graph_spacing_px`, and `layout_placement` before projecting graph-unit geometry or evidence.
   - `background_defaults.load_geometry_background_defaults(...)` is the canonical geometry-domain loader for background defaults (domain baseline with optional task-group override).
   - `noise_defaults.load_geometry_noise_defaults(...)` is the canonical geometry-domain loader for post-image noise defaults (domain baseline with optional task-group override).
   - `shape_style.py` is the canonical geometry ink-style sampler and applies Lab-distance constraints against background anchor colors.
   - `diagram_style.py` is the geometry-domain adapter over shared `technical_diagram_style`; use it to map shared technical roles onto graph-paper specs, geometry ink, labels, guides, and backgrounds instead of importing puzzle/game panel adapters.
   - `render_variation.py` is the canonical integer render-range sampler (for example line-width ranges).
   - `annotation_values.py` provides canonical value formatting + structured annotation->value evidence map helpers for analytical geometry tasks.
   - `labeled_point_evidence.py` provides canonical graph-paper witness adapters that expose public pixel `point_set` evidence for labeled maps, singleton points, unlabeled point sets, and zero-witness geometry count tasks.
   - `point_labels.py` provides overlap-aware labeled-point rendering helpers reused by conic/point-evidence tasks, including avoidance of blocked segments and nearby point markers so labels stay off the figure itself when a clean placement exists.
   - `graph_rendering.graph_units_to_pixel(...)` is the canonical graph-unit-to-pixel projection helper once more than one task group needs hidden graph-unit layout coordinates.
   - `single_object_scene.py` owns the shared full-scene graph-paper render context and creates a `graph_paper_panel` background: graph paper is rendered only inside the resolved framed panel, while evidence coordinates are projected from the final panel origin.
   - `prompt_text.py` provides canonical prompt-fragment helpers such as `append_required_labels_clause(...)` so label-list suffixes keep consistent punctuation across geometry tasks.
   - `measurement_rendering.py` provides shared measurement-scene bbox formatting, clamp/pad/point-bbox helpers, one-decimal measurement formatting, and centered measurement-label drawing. Use it for geometry measurement tasks before adding local `_bbox_to_list`, `_clamp_bbox`, `_pad_bbox`, `_bbox_from_points`, `_round1`, `_fmt_number`, `_fmt_measure`, or `_draw_label` copies.
   - `coordinate_panel_grid.py` provides reusable small-multiple coordinate-panel layout, axis/grid rendering, graph-to-pixel projection, and point-marker drawing for analytical geometry panel-label tasks.
   - `slope_geometry.py` provides reusable slope-line feasibility/sampling helpers for graph-paper slope tasks.
   - `multi_angle_scene.py` provides reusable target-conditioned multi-angle geometry construction plus object-label placement for sibling angle tasks across geometry task groups.
   - `multi_polygon_scene.py` provides reusable outline + object-label rendering for sibling multi-polygon scenes across geometry task groups.
   - `quadrilateral_prototypes.py` provides reusable centered quadrilateral-class samplers/classifiers shared by quadrilateral counting scenes and future mixed shape-type scenes.
   - `function_graph_scene.py` provides reusable graph-paper plotted-function rendering helpers for graphing-family geometry tasks; keep floating-point graph-unit projection, function polyline drawing, and dashed horizontal guide-line rendering there instead of rebuilding those helpers task-locally.
   - `complexity.py` is the shared geometry-domain complexity layer; it owns normalized `[0, 1]` score construction, config-weight resolution, and the active family builders for migrated geometry tasks (currently comparison, counting, measurement, analytical, coordinate, circle, and graphing), while task modules still own the task-local raw-to-normalized measurements that feed those shared builders.
   - `consolidated_sampling.py` is the canonical scene/query-axis resolver for consolidated geometry tasks; use it when a geometry family exposes constrained `scene_variant` + `query_id` sampling instead of re-implementing filtering per task.
   - `consolidated_source.py` is the canonical adapter layer for consolidated geometry tasks that delegate to source geometry generators while rewriting trace metadata to the active `scene_variant` / `query_id` contract, including the review-facing `query_id` probability fields that inspection/distribution tooling reads back later.
   - `polygon_transformations.py` is the canonical lattice-polygon transform helper for geometry tasks that reason over rigid transforms or similarity; keep asymmetric template sampling plus rigid/uniform/anisotropic polygon transforms and congruence/similarity checks there instead of encoding those transforms directly inside each geometry task.
   - `polygon_scene_helpers.py` is the canonical graph-paper polygon projection/reference-rendering helper for geometry families that reuse the same Reference-plus-candidates scaffold; keep point projection, polygon visibility checks, and `Reference` label rendering there instead of cloning those task-local helpers.
2. Geometry measurement task-group: `trace/tasks/geometry/measurement/defaults.py`, `shape_measure_base.py`, `trace/tasks/geometry/shared/measurement_rendering.py`, `trace/tasks/geometry/shared/conic_geometry.py`, `trace/tasks/geometry/shared/length_geometry.py`
   - `defaults.py` centralizes task-group fallback defaults reused by measurement tasks.
   - `shape_measure_base.py` provides the shared generation/output pipeline for shape variants (polygon + conic) used by area/perimeter tasks.
   - `measurement_rendering.py` provides reusable pixel-bbox and label-drawing helpers for measurement scenes; keep rendering/evidence primitive math there when multiple measurement tasks share it.
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
5. Graph: `trace/tasks/graph/shared/graph_sampling.py`, `graph_scene.py`, `label_assets.py`, `prompt_examples.py`, `pipe_junction_scene.py`, `pipe_junction_task.py`, `metro_route_scene.py`, `metro_route_task.py`, `task_support.py`, `style.py`, `visual_defaults.py`, `complexity.py`
  - `graph_sampling.py` is the canonical simple-graph topology sampler for graph-domain tasks; keep degree-support feasibility probes, disconnected-component construction, directed-reachability construction, unique-shortest-path construction, unicyclic/cycle samplers, bridge samplers, weighted-MST samplers, and articulation-point / unique-largest-component samplers there instead of cloning rejection loops per task.
  - `graph_scene.py` is the canonical labeled node-link graph renderer for graph-domain tasks; keep node/edge pixel geometry, panel chrome, layout fallback logic, and optional edge-weight label rendering there instead of task-local drawing.
  - `label_assets.py` is the graph-domain adapter over repo-wide label manifests. Keep graph-specific label variants, character caps, eligible-bucket filtering, and edge-label support sampling there instead of reimplementing named label pools inside individual graph tasks.
  - `prompt_examples.py` owns graph-domain JSON example schema mechanics for repeated node/edge point-evidence prompt examples; keep task-specific semantic example choices in the task or prompt bundle.
  - `pipe_junction_scene.py` and `pipe_junction_task.py` own the pipe-junction graph scene grammar: grid-placed labeled junctions, open/blocked pipe rendering, open-pipe graph sampling, and shared public-task plumbing for pipe path/relation/counting tasks.
  - `metro_route_scene.py` and `metro_route_task.py` own the metro-route graph scene grammar: colored schematic routes, labeled stations, route-membership metadata, transfer-station evidence projection, and shared public-task plumbing for future metro route tasks.
  - `task_support.py` is the canonical graph-task support layer for balanced style-axis resolution, finite integer support parsing, node-color theme selection, semantic node-color style metadata, edge-label trace metadata, edge-edit/query probability adapters, and shared graph render-parameter defaults; if a second graph task needs the same node-shape / named-color / label-support / layout-transform plumbing, promote it there instead of copying task-local resolution code.
  - `style.py` is the canonical graph-domain visual-theme helper; keep named-color graph palettes and other non-semantic whole-image graph styling there instead of re-deriving per-task RGB themes.
  - `information_style.py` is the graph-domain adapter over shared `information_scene_style`; use it to map shared structured-information roles onto graph backgrounds, panels, titles, neutral edges, and labels while preserving topology and task-owned semantic node/edge colors.
  - `visual_defaults.py` is the canonical graph-domain background/noise loader layer shared across future graph task groups.
  - `complexity.py` is the shared graph-domain complexity layer; it owns normalized `[0,1]` score construction, config-weight resolution, and weighted-mean `TaskComplexity` construction, while graph tasks still own their task-local raw-to-normalized difficulty measurements.
6. Time artifacts: `trace/tasks/shared/time_format.py`, `time_artifact_style.py`, `time_artifact_task_support.py`, `time_artifact_complexity.py`, `time_artifact_fixed_query.py`, plus scene helpers in `trace/tasks/pages/shared/{calendar_scene.py,schedule_scene.py,timeline_scene.py}` and `trace/tasks/puzzles/shared/clock_scene.py`
   - `time_format.py` is the canonical helper layer for 12-hour clock normalization, schedule/day-time formatting, timeline month/day labels, minute offsets, and reusable calendar/date labels such as weekday abbreviations or ordinal strings; keep wraparound and date-label rules there instead of re-encoding them per task.
   - `calendar_scene.py`, `schedule_scene.py`, `timeline_scene.py`, and `clock_scene.py` own the reusable render geometry and trace projections for the page and puzzle time-artifact scenes.
   - `time_artifact_style.py` owns shared named-color palettes and non-semantic clock/calendar/schedule/timeline styling.
   - `time_artifact_task_support.py`, `time_artifact_fixed_query.py`, and `time_artifact_complexity.py` own shared sampling, narrowed-query policy adapters, and compact complexity construction for these scenes. The actual public-query metadata rewrite should delegate to `trace/tasks/shared/fixed_query.py`.
7. Shared visual styling: `trace/tasks/shared/visual_style/`, with panel adapters in `trace/tasks/puzzles/shared/scene_style.py` and `trace/tasks/games/shared/scene_style.py`, technical-diagram adapters in `trace/tasks/geometry/shared/diagram_style.py` and `trace/tasks/physics/shared/diagram_style.py`, and structured-information adapters in `trace/tasks/charts/shared/information_style.py`, `trace/tasks/pages/shared/information_style.py`, and `trace/tasks/graph/shared/information_style.py`
   - `visual_style/panel.py` owns the reusable non-semantic panel/canvas treatment registry for puzzle/game/icon-like scenes. The current registry has 20 treatments spanning plain canvases, paper/worksheet panels, board-like mats, lab panels, arcade screens, and terminal screens. `visual_style/palette.py` owns the matching 20 shared palette definitions and compatibility tags.
   - Puzzle/game/icon domains should reuse the shared panel-style implementation instead of copying treatment drawing code. Domain adapters should only map shared style roles onto scene-specific boards, cells, HUDs, option cards, labels, and evidence-bearing geometry.
   - Use the puzzle adapter names (`resolve_puzzle_scene_style(...)`, `make_puzzle_scene_background(...)`, `draw_puzzle_panel_chrome(...)`, `draw_puzzle_grid_cell(...)`, and `draw_puzzle_option_card(...)`) from puzzle tasks, and the game adapter names from games tasks. Both adapters call the same global shared implementation.
  - `visual_style/technical_diagram.py` owns the reusable non-semantic technical diagram treatment/palette registry for geometry and physics. The current registry has 20 treatments spanning bare/off-white sheets, graph/engineering/millimeter paper, blueprint/chalkboard variants, notebooks, worksheet/exam/textbook/presentation surfaces, scan/print textures, and lab cards, plus 20 palettes with compatibility tags and contrast metadata. It also owns independent technical frame modes (`none`, `plain_outline`, `matching_outline`) with default weights `0.5/0.25/0.25`.
  - Geometry and physics domains should share `technical_diagram_style` through their domain adapters. Do not reuse the puzzle/game `panel_scene_style` adapter for math/physics diagrams.
  - `visual_style/information_scene.py` owns the reusable non-semantic structured-information treatment/palette registry for charts, pages, and graph. The current registry has 20 treatments spanning clean report sheets, dashboard/app-window tiles, editorial/publication figures, infographic/poster/callout panels, source-note/scan sheets, compact small multiples, data-table reports, presentation slides, and dark analytics boards, plus 20 palettes with compatibility tags, semantic-color protection, contrast metadata, and independent chrome modes (`none`, `thin_frame`, `accent_frame`) with default weights `0.5/0.25/0.25`.
  - Charts, pages, and graph should share `information_scene_style` through thin domain adapters. Style sampling must happen before rendering, must be recorded under `render_spec`, and must not alter semantic chart marks, document values, graph topology, or task-owned color evidence.
8. Puzzles/cell_board implementation: `trace/tasks/puzzles/cell_board/shared/grid_graph.py`, `visual_defaults.py`, `maze_sampling.py`, `grid_layout.py`, `maze_scene.py`, `maze_rendering.py`, `tile_scene.py`, `tile_evidence.py`, `rectangular_board.py`, `tile_colors.py`, `named_color_board.py`, `reachability_board.py`, `board_size_sampling.py`, `trace/tasks/puzzles/cell_board/shared/color_board_common.py`, `complexity.py`
   - `grid_graph.py` is the canonical 4-neighbor rectangular-tile graph helper layer (stable `cell_id`, open-grid adjacency, shortest-path adapters, and active-cell connected-components helpers).
   - `visual_defaults.py` is the canonical background/noise loader layer shared across `puzzles/cell_board` implementation modules.
   - `tile_scene.py` is the canonical dense-board `tile_cell` entity builder for non-maze cell-board tasks.
   - `tile_evidence.py` is the canonical cell-board evidence helper layer: it exposes public pixel `point_set` / `point_sequence` evidence at tile centers while retaining private grid coordinates and stable tile ids for verification.
   - `rectangular_board.py` is the canonical dynamic rectangular-board layout/rendering helper for single-board cell-board tasks.
   - `tile_colors.py` is the cell-board wrapper over `trace/tasks/shared/named_colors.py`; keep board-specific naming/query helpers there, but keep the canonical palette itself in the shared layer.
   - `named_color_board.py` is the canonical named-color board sampling/rendering layer shared across cell-board tasks, and it now owns the shared query-annotated scene-entity builder for named-color boards.
   - `reachability_board.py` is the canonical blocked-board reachability sampler for cell-board tasks that need one start tile plus reachable/unreachable open-cell partitions before task-specific target/path selection.
   - `board_size_sampling.py` resolves fixed `rows`/`cols` overrides or deterministic square-board side-length ranges for cell-board tasks.
   - Concrete cell-board tasks and wrappers live under `trace/tasks/puzzles/cell_board/`; keep reusable helpers under `trace/tasks/puzzles/cell_board/shared/`.
   - `color_board_common.py` now provides count-task adapters plus reusable per-color component analysis for flat tile tasks.
   - `complexity.py` is the shared cell-board complexity layer; it owns normalized `[0,1]` helper transforms, complexity-weight resolution, and weighted-mean `TaskComplexity` construction, while each task still owns its task-local raw-to-normalized difficulty mapping.
9. Icons: `trace/tasks/icons/shared/defaults.py`, `evidence.py`, `icon_assets.py`, `icon_noise.py`, `icon_scene.py`, `icon_task_rendering.py`, `icon_style.py`, `icon_transform.py`, `icon_grid_scene.py`, `icon_sequence_scene.py`, `icon_single_panel_labeled_grid_scene.py`, `icon_pair_grid_scene.py`, `icon_overlap_grid_scene.py`, `icon_labeled_grid_scene.py`, `procedural_named_icon_field_scene.py`, `anchor_marking.py`, `complexity.py`
   - `icon_assets.py` is the canonical loader for the curated icon bundle under `assets/icons/`; resolve pool membership through manifests rather than reconstructing SVG paths from task-local filename guesses.
   - `defaults.py` centralizes fallback defaults shared across icon task groups; keep shared panel/layout/noise defaults there instead of importing them from one task-group-named module once another icon family reuses them.
   - `icon_noise.py` centralizes per-icon subtle-noise sampling/application while preserving the icon alpha mask; use it for icon-instance perturbations instead of repurposing post-composite image noise helpers.
   - `icon_scene.py` provides the reusable two-panel `Reference` + `Scene` layout, panel geometry trace payloads, panel chrome rendering, random overlap-capped icon placement, explicit nominal-size support for tasks that reason about icon scale, and reading-order bbox canonicalization for sibling icon tasks.
   - Reuse `random_paste_bbox(...)`, `overlap_fraction_smaller(...)`, and `max_overlap_with_existing(...)` from `icon_scene.py` when a second icon task needs custom constrained placement rather than cloning overlap math task-locally.
   - `icon_task_rendering.py` provides shared render-param resolution (including labeled-cell chrome defaults used by sequence and pattern tasks), common icon-style trace serialization, and deterministic per-instance noise sampling across icon task groups; keep those helpers here rather than under a `counting`-named module once relation/sequence/transformation/pattern tasks reuse them.
   - `icon_style.py` provides curated-icon palette helpers that sample per-instance tints with Lab-distance separation from the panel/background chrome; keep icon color policy there instead of re-implementing task-local palette samplers.
   - `icon_style.sample_single_icon_tint(...)` is the canonical single-color sampler for icon tasks that intentionally keep one shared tint across the whole scene.
   - `icon_transform.py` is the canonical home for D4 transform ids and image-space transform application; use it for icon rotation/mirror families instead of encoding transform names task-locally.
   - `evidence.py` provides shared public-evidence projection helpers for icon tasks; use it when a task samples semantic cell labels but must expose pixel-space evidence boxes.
   - `icon_grid_scene.py` provides reusable compact labeled-grid slot layouts, explicit fixed-grid slot layouts, plus horizontal row slot layouts for icon tasks whose semantic unit is the cell rather than one free-placed icon.
   - `icon_sequence_scene.py` provides the reusable single-panel sequence-row renderer for icon tasks that show a horizontal row of cell boxes; keep row-cell placement, dynamic row-box sizing, visible cell-label chrome, one-box `?` rendering, and sequence-cell icon serialization there instead of cloning them inside each sequence task.
   - `icon_single_panel_labeled_grid_scene.py` provides reusable single-panel labeled-grid chrome plus canvas sizing for icon tasks whose semantic unit is a numbered cell in one grid; use it for 2D pattern-style tasks instead of cloning grid chrome from the two-panel relation helpers or stretching the sequence-row renderer beyond its row-only contract.
   - `icon_pair_grid_scene.py` provides the reusable Reference-pair + labeled Scene-grid renderer for icon transformation-style tasks; use cell labels from this renderer for private semantic matching and project matching cells to public pixel boxes.
   - `icon_overlap_grid_scene.py` provides the reusable Reference-overlap + labeled Scene-grid renderer for pairwise occlusion-order tasks; use cell labels from this renderer for private semantic matching and project matching cells to public pixel boxes.
   - `icon_labeled_grid_scene.py` provides reusable two-panel `Reference` + labeled `Scene` grid chrome for icon tasks that render whole cell images task-locally; use it when the task-specific logic is inside each cell rather than in one generic pair/overlap widget, and use its square-cell options when diagonal cell symmetries need square reference/scene boxes without task-local geometry hacks.
   - `procedural_named_icon_field_scene.py` provides the reusable procedural named-icon field renderer plus shared named-icon support helpers for integer bounds, fill-style support/probabilities, uniform string probability maps, rotatable-shape sampling, common bbox geometry, and planned-sprite rendering. Use it for named-icon field/count/relation tasks before copying `_bounds`, `_fill_style_support`, `_fill_style_probabilities`, `_uniform_string_probability_map`, `_rotation_for_shape`, or local named-icon bbox helpers.
   - `anchor_marking.py` provides the reusable highlighted-anchor outline + label renderer for icon relation tasks with visible anchors; once a second icon relation task marks anchors, keep that chrome shared instead of duplicating task-local rounded-box label placement.
   - `complexity.py` provides the icon-domain complexity-weight resolver plus normalized score builders for migrated icon tasks across the active counting, relation, transformation, sequence, and pattern families; keep icon complexity weights in `configs/domains/icons/*` and task-specific criterion measurement in code rather than copying weighted-score math into each task.
9. Charts: `trace/tasks/charts/shared/chart_scene.py`, `label_assets.py`, `labeled_chart_common.py`, `distribution_chart_common.py`, `multiseries_chart_common.py`, `complexity.py`, `visual_defaults.py`
   - `chart_scene.py` is the canonical chart renderer for the active chart families; it owns the shared axis/grid scaffold plus mark/label trace geometry for single-series `area`, `bar`, `pie`, `donut`, `horizontal_bar`, `line`, `radar`, `scatter`, `dot_plot`, and `lollipop`, the active multiseries `grouped_bar`, `grouped_horizontal_bar`, `multi_line`, and `grouped_lollipop` renderers, and the dedicated `histogram`, `boxplot`, and `violin` distribution renderers.
   - `label_assets.py` is the chart-domain adapter over repo-wide `assets/labels/` manifests. Use it for richer chart axis labels, legend labels, category bins, and named series/rows instead of hardcoding task-local label lists or defaulting every chart to alphabet letters.
   - `labeled_chart_common.py` is the shared construction layer for labeled single-series chart tasks; it owns mark-count/value bounds, balanced semantic/scene variant sampling, randomized label/color sampling, per-slice pie/donut palette assignment, reusable percentage-composition builders for pie/donut, reusable statistic builders, reusable threshold/interval counting dataset builders, reusable two-label readout dataset builders, reusable ordered-sequence trend dataset builders, and the shared pixel-space mark-evidence projection used by chart review overlays.
   - `distribution_chart_common.py` is the shared construction layer for distribution-style chart tasks; it owns histogram bin construction, cumulative/interval count query setup, categorical boxplot summary construction, violin density construction, and the fixed-scene distribution task defaults.
   - `multiseries_chart_common.py` is the shared construction layer for multiseries chart tasks; it owns series/category count bounds, per-series palette sampling, series/category label sampling, pairwise-comparison, derived-delta, and conditional-gap dataset construction, and category-grounded pixel-space evidence projection for multiseries review overlays.
   - `complexity.py` is the shared chart-domain complexity layer; it owns the normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction, while each chart task still owns its task-local raw-to-normalized transforms and scene-variant difficulty mapping.
   - Chart mark colors should be sampled once per instance and then reused consistently across all marks in that chart; keep the renderer wired to the resolved per-instance fill/outline colors rather than tracing one style and drawing another.
   - `information_style.py` is the chart-domain adapter over shared `information_scene_style`; use it to map shared structured-information roles onto axis, grid, text, plot surface, guide, and background roles while leaving semantic mark colors intact.
   - `visual_defaults.py` is the canonical chart-domain background/noise loader layer shared across future chart task groups.
10. Data-table charts: `trace/tasks/charts/table/shared/table_scene.py`, `table_common.py`, `visual_defaults.py`
   - `table_scene.py` is the canonical styled-table renderer for active table tasks; it owns numeric/string table cell geometry, row/column region bboxes, the full numeric-table region bbox, non-semantic table visual-style axes, and the active `spreadsheet|zebra|ledger|card_table` scene variants.
   - `table_common.py` is the shared construction layer for table tasks; it owns row/column count bounds, row-name/header sampling, row/column/whole-table summary dataset construction, ranking/filtered-subset/relation/counting/readout dataset construction, temporal year-header sampling plus temporal dataset construction, canonical numeric-cell id resolution, render-param/style resolution, render-style trace serialization, and both cell- and region-level bbox evidence projection.
   - `visual_defaults.py` is the canonical chart table background/noise loader layer shared across future table task groups.
11. Puzzles: `trace/tasks/puzzles/shared/common.py`, `drawing.py`, `option_panels.py`, `option_layout.py`, `symbol_rendering.py`, `arithmetic_scene.py`, `balance_scene.py`, `grid_scene.py`, `logic_scene.py`, `paper_fold_scene.py`, `overlay_scene.py`, `block_stack_scene.py`, `solid_view_scene.py`, `bead_loop_scene.py`, `assembly_scene.py`, `tangram_scene.py`, `arithmetic_common.py`, `logic_common.py`, `paper_fold_common.py`, `paper_fold_cut_common.py`, `overlay_common.py`, `spatial_blocks_common.py`, `bead_loop_common.py`, `assembly_common.py`, `shape_complement_common.py`, `complexity.py`, `visual_defaults.py`
   - `common.py` provides canonical puzzle-axis resolution, prompt-facing bbox projection, repeated integer param/range resolution, and task-default loading once more than one puzzle family needs the same deterministic variant/evidence/config helpers.
   - `drawing.py` provides the small centered-text and rounded-rectangle primitives shared by multiple puzzle scene renderers; use it when a second puzzle renderer needs the same deterministic text chrome instead of cloning local `_draw_centered_text` / `_rounded_rect` helpers again.
   - `option_panels.py` provides the reusable labeled image-option panel chrome for puzzle families that answer with `option_letter`; when a second puzzle family needs labeled image options, keep the label/content-box geometry shared here instead of duplicating task-local option-panel layout.
   - `option_layout.py` provides the canonical centered multi-row option layout for puzzle scenes with `5..6` or larger labeled choices; when a second puzzle family needs the same centered `3+2` or `3+3` image-choice layout, keep that row-count logic shared here instead of duplicating it inside another renderer.
   - `symbol_rendering.py` provides the canonical puzzle symbol vocabulary and shape-icon renderer reused across arithmetic and logic puzzle families; do not keep parallel shape palettes or box-icon drawers in task-local modules.
   - `shape_complement_common.py` owns the rectangular missing-piece cell-trace sampler reused by the polyomino arrangement task's rectangle-complement variant; rendering stays in the active polyomino renderer.
   - `arithmetic_scene.py` is the canonical boxed-slot equation renderer for active arithmetic equation puzzles; it owns slot/operator layout, scene chrome variants, slot bbox tracing, and the `equation_strip|equation_card|equation_outline` scene variants.
   - `balance_scene.py` is the canonical equality-panel arithmetic renderer for active balance-value puzzles; it owns stacked equality-panel layout, symbolic/numeric box rendering, explicit equals-token rendering, highlighted query-box layout, bbox tracing, and the `balance_strip|balance_card|balance_outline` scene variants.
   - `grid_scene.py` is the canonical arithmetic-grid renderer for active rule-grid puzzles; it owns fixed-column grid layout, card/outline scene chrome, cell bbox tracing, and the `grid_strip|grid_card|grid_outline` scene variants.
   - `arithmetic_common.py` is the shared arithmetic-puzzle helper layer; it owns arithmetic answer-bound resolution, task/scene variant resolution, boxed-equation dataset construction, arithmetic-grid dataset construction, equation/grid render-param resolution, and generic ordered puzzle-bbox evidence projection.
   - `logic_scene.py` is the canonical option-based logic-grid renderer for active logic puzzles; it owns square board layout, missing-cell styling, and option/cell bbox tracing for the `logic_strip|logic_card|logic_outline` scene variants while reusing the shared puzzle option-panel chrome.
   - `logic_common.py` is the shared logic-puzzle helper layer; it owns logic board-size bounds, logic render-param resolution, row/column/Latin-style board construction, explicit-rule adjacency board construction, deterministic correct-option placement, and the active logic-grid dataset builders.
   - `paper_fold_scene.py` is the canonical reference-plus-options renderer for active spatial paper-fold and fold-cut result puzzles; it owns the single-sheet layout, explicit fold arrows and fold-line chrome, labeled option-image layout, folded-result or unfolded-result sheet rendering, and option/reference bbox tracing for the `fold_strip|fold_card|fold_outline` scene variants.
   - `paper_fold_common.py` is the shared paper-fold helper layer; it owns spatial fold-result defaults, scene-variant/render-param resolution, folded-result dataset construction, deterministic back-projection from folded packet to full sheet, and distractor generation for the active folded-result task.
   - `paper_fold_cut_common.py` owns the fold-cut dataset construction layer: task/scene variant resolution, center-fold sequence construction, cut-cell expansion through folded paper layers, unfolded hole-pattern option construction, and deterministic correct-option placement for fold-cut result tasks.
   - `overlay_scene.py` is the canonical reference-plus-options renderer for active transparent-sheet overlay puzzles; it owns the two-source-sheet layout, centered bare option-image layout, plus-sign chrome, source/option mark drawing, and option/source bbox tracing for the `overlay_strip|overlay_card|overlay_outline` scene variants.
   - `overlay_common.py` is the shared transparent-sheet overlay helper layer; it owns source-sheet/grid bounds, overlap-aware union dataset construction, deterministic correct-option placement, distractor generation, and render-param resolution for the active overlay task and later overlay-style siblings.
   - `block_stack_scene.py` is the canonical fixed-view isometric block-comparison renderer for active cube-removal spatial puzzles; it owns visible-face rendering, side-by-side structure layout, captions/arrow chrome, and structure/face bbox tracing for the `stack_strip|stack_card|stack_outline` scene variants.
   - `solid_view_scene.py` provides cube-stack sampling plus isometric/orthographic rendering helpers for active solid-view spatial puzzles; keep cube occupancy growth, orthographic projection-cell derivation, and query-panel bbox projection there instead of rebuilding them inside each task.
   - `spatial_blocks_common.py` is the shared block-stack helper layer; it owns stack-footprint/height bounds, per-cube face visibility bookkeeping, cube-removal dataset construction, and render-param resolution for the active cube-removal task and later block-stack siblings.
   - `assembly_scene.py` is the canonical renderer for the polyomino arrangement buildable-target variant; it owns the top reference-piece row, the bottom labeled silhouette options, polyomino cell drawing, and piece/option bbox tracing for the `assembly_strip|assembly_card|assembly_outline` scene variants.
   - `assembly_common.py` is the shared polyomino assembly helper layer; it owns piece/option count bounds, polyomino rotation canonicalization, exact rotation-only tiling checks, assembly dataset construction, and render-param resolution for the polyomino arrangement buildable-target variant and later cut-and-build siblings.
   - `tangram_scene.py` is the canonical renderer/sampler for tangram-style polygon-piece puzzles; it owns traced polygon assemblies, loose option panels, missing/marked region bboxes, edge-contact witnesses, and visual scene variants for `tangram_assembly_panel`.
   - `bead_loop_scene.py` is the canonical reference-plus-options renderer for active topology cyclic-order loop puzzles; it owns the reference-loop panel, option-loop image layout, loop/token drawing, loop path styles, and reference/option bbox tracing for `necklace_board|charm_card_grid|route_loop_diagram|token_ring_outline`.
   - `bead_loop_common.py` is the shared topology-puzzle helper layer; it owns cyclic-order loop defaults, render-param resolution, `token_render_style` and `loop_path_style` axes, cyclic-rotation equivalence checks, deterministic valid/invalid option construction, and the active cyclic-order dataset builder.
   - `complexity.py` is the shared puzzle-domain complexity layer; it owns the normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction.
   - `visual_defaults.py` is the canonical puzzle-domain background/noise loader layer shared across future puzzle task groups.
12. Illustrations: `trace/tasks/illustrations/shared/object_catalog.py`, `object_schema.py`, `object_registry.py`, `scene_objects.py`, `object_library.py`, `render_geometry.py`, `task_support.py`, `*_rendering.py` scene-renderer modules, drawing-free `*_scene.py` public interfaces, and scene-specific task common helpers
   - `object_catalog.py` is the single source for illustration drawable vocabularies: object/fixture/region/background ids, public names, labels, renderer-facing variant ids, render layer, size class, placement tags, scene tags, and renderer ids. Use its tag, scene, render-layer, and size-class helpers instead of re-declaring scene-local object pools.
   - `object_schema.py`, `object_registry.py`, and `scene_objects.py` are the canonical illustration object-record layer. Keep public object ids, display names, families, semantic-vs-visual attribute separation, and cross-scene object-record extraction there instead of duplicating scene-local object vocabularies.
   - `object_library.py` is the canonical reusable glyph drawing layer for mixed-object and environment-style illustration tasks; keep shared object glyphs, semantic part records, and object bbox tracing there instead of task-local drawers.
   - `render_geometry.py` owns renderer-level pixel scaling helpers for bbox and point coordinates. Use it before adding local `_scale_bbox` or `_scale_points` copies in illustration renderers.
   - `task_support.py` owns repeated illustration task sampling/config mechanics: integer bounds, query/string support, count sampling, string probability maps, scene setting/style weights, render-param prefix resolution, and standard task RNG spawning. Keep scene-specific semantic supports in the scene task-common modules.
   - Scene renderer modules such as `environment_object_rendering.py`, `indoor_room_rendering.py`, `urban_market_rendering.py`, `library_rendering.py`, `park_playground_rendering.py`, `transit_terminal_rendering.py`, and `construction_site_rendering.py` own PIL drawing for scene backgrounds, fixtures, scene-specific objects, and final pixel bbox projection for their scene family.
   - Scene interface modules such as `environment_object_scene.py` and `urban_market_scene.py` remain drawing-free scene boundaries. Do not add PIL imports, `Image.new`, `ImageDraw.Draw`, or `_draw_*` helpers to `*_scene.py`.
   - Scene task-common modules, including `construction_task_common.py`, own narrow scene-local sampling/render-param helpers once multiple tasks share one illustration scene.
   - Illustration verifiers should consume renderer records, normalized `object_record` payloads, and projected bboxes from the shared scene helper; do not infer object, part, zone, or surface membership from pixels.
13. Physics: `trace/tasks/physics/shared/circuit_scene.py`, `optics_scene.py`, `complexity.py`, `style.py`, `diagram_style.py`, `support_sampling.py`, `visual_defaults.py`
   - `circuit_scene.py` is the shared physics-domain resistor-network renderer; it owns terminal drawing, resistor-box rendering, optional red `?` missing-resistor rendering, wire layout, local-scene origin offsets, and prompt-facing bbox projection for active circuits tasks and later circuit siblings.
   - `optics_scene.py` is the shared physics-domain optics-board renderer; it owns board/grid rendering, source + mirror + target drawing, hidden solved-ray projection, and pixel point grounding for optics tasks.
   - `complexity.py` is the shared physics-domain complexity layer; it owns normalized `[0,1]` score construction, complexity-weight resolution, and family builders for active physics tasks (currently mechanics, circuits, fluids, and optics reasoning, including spring-proportionality, pulley mechanical-advantage, and hydraulic-piston scenes).
   - `style.py` is the shared physics-domain named-theme layer; it owns reusable accent-color palettes for non-semantic physics styling (currently mechanics, spring cards, pulley systems, hydraulic pistons, resistor-network scenes, and optics boards) so new physics tasks do not hardcode separate per-task color mixes.
   - `diagram_style.py` is the physics-domain adapter over shared `technical_diagram_style`; use it to map shared technical roles onto apparatus diagrams, graph/plot surfaces, field maps, labels, guides, and backgrounds while preserving task-owned semantic colors such as charge signs or missing-value markers.
   - `support_sampling.py` is the shared physics-domain integer-support resolver layer; use it when multiple physics tasks need the same deterministic support-list parsing and balanced answer cycling behavior instead of keeping parallel local helpers. When a physics task has a tiny fixed answer support and review collection samples consecutive seeds, prefer the helper's direct `instance_seed` cycling option over a hashed namespace-only cycle so per-variant distributions stay flat under task review; when a task balances multiple axes, use separate namespaces so scene/query cycling does not alias the answer support.
   - `visual_defaults.py` is the canonical physics-domain background/noise loader layer shared across future mechanics / circuits / fluids / optics task groups.
14. Games: `trace/tasks/games/shared/dots_boxes_common.py`, `dots_boxes_scene.py`, `bingo_common.py`, `bingo_scene.py`, `card_scene.py`, `domino_scene.py`, `darts_scene.py`, `reversi_common.py`, `reversi_scene.py`, `connect_four_common.py`, `connect_four_scene.py`, `checkers_common.py`, `checkers_scene.py`, `chess_common.py`, `chess_scene.py`, `morris_common.py`, `morris_scene.py`, `go_common.py`, `go_scene.py`, `minesweeper_common.py`, `snake_common.py`, `snake_scene.py`, `sampling.py`, `complexity.py`, `style.py`, `visual_defaults.py`
   - `dots_boxes_common.py` is the shared dots-and-boxes construction layer; it owns grid-edge geometry, forced-turn capture-chain construction, and deterministic captured-box witness projection for active dots-and-boxes tasks and later siblings.
   - `dots_boxes_scene.py` is the canonical dots-and-boxes renderer for active games dots-and-boxes tasks; it owns paper-board chrome, highlighted-edge drawing, dot/edge layout, and traced box/edge bbox maps.
   - `bingo_common.py` is the shared bingo-card construction layer; it owns `5 x 5` number-grid sampling, query-specific marked-cell construction, and deterministic completed-line witness projection for active bingo tasks and later bingo siblings.
   - `bingo_scene.py` is the canonical bingo-card renderer for active games bingo tasks; it owns card chrome, `B I N G O` headers, marked-cell drawing, and traced cell/column bbox maps.
   - `card_scene.py` is the shared games-domain face-up card renderer; it owns centered row layout, optional row labels, card badges such as `REF` / `MOVE` / player labels, continuation-cue chrome, and card bbox tracing for card-hand tasks.
   - `domino_scene.py` is the shared games-domain domino renderer; it owns top-chain plus loose-tableau layout, pip drawing, `REF` tag / open-end highlight chrome, and domino bbox tracing for domino-chain tasks.
   - `reversi_common.py` is the shared games-domain Reversi rules helper layer; it owns board constants, legal-move evaluation, coordinate ids, and other rule-level helpers so future Reversi tasks reuse one canonical implementation.
   - `reversi_scene.py` is the shared games-domain Reversi renderer; it owns board layout, player badge rendering, disc chrome, marked-move overlays, and board-square bbox tracing for Reversi tasks.
   - `connect_four_common.py` is the shared games-domain Connect Four rules helper layer; it owns board constants, legal-drop evaluation, immediate-win detection, coordinate ids, and completed-line tracing so future Connect Four tasks reuse one canonical implementation.
   - `connect_four_scene.py` is the shared games-domain Connect Four renderer; it owns board layout, player badge rendering, disc chrome, marked-landing overlays, and board-square bbox tracing for Connect Four tasks.
   - `checkers_common.py` is the shared games-domain Checkers rules helper layer; it owns board constants, non-king movement/capture evaluation, coordinate ids, and other rule-level helpers so future Checkers tasks reuse one canonical implementation.
   - `checkers_scene.py` is the shared games-domain Checkers renderer; it owns board layout, player badge rendering, checker-piece chrome, and board-square bbox tracing for Checkers tasks.
   - `chess_common.py` is the shared games-domain Chess rules helper layer; it owns board constants, piece movement/attack helpers, capture-target extraction, coordinate ids, and JSON-safe board serialization for single-step Chess tasks.
   - `chess_scene.py` is the shared games-domain Chess renderer; it owns board layout, marked-square chrome, chess-piece glyph rendering, and board-square/piece bbox tracing for Chess tasks.
   - `darts_scene.py` is the shared games-domain darts renderer; it owns labeled dartboard geometry, sector/ring drawing, dart-marker chrome, and dart bbox tracing for darts tasks.
   - `morris_common.py` is the shared nine-men's-morris construction layer; it owns the canonical `24`-node board geometry, mill definitions, feasible counted-piece supports, and deterministic visible board sampling for active Morris tasks and later siblings.
   - `morris_scene.py` is the canonical nine-men's-morris renderer for active games Morris tasks; it owns board-line drawing, node placement, piece rendering, and traced piece/node bbox maps.
   - `go_common.py` is the shared Go construction layer; it owns the fixed `7 x 7` board geometry, connected-group/liberty helpers, legality-preserving distractor placement, feasible liberty-count supports, and deterministic visible board sampling for active Go tasks and later Go siblings.
   - `go_scene.py` is the canonical Go renderer for active games Go tasks; it owns wood-board chrome, intersection placement, highlighted-group stone rendering, and traced intersection/stone bbox maps.
   - `sudoku_common.py` is the shared Sudoku construction/rules layer; it owns `9 x 9` solution generation, row/column/box helpers, candidate/missing/repeated digit logic, and deterministic visible-grid sampling for Sudoku tasks and later siblings.
   - `sudoku_scene.py` is the canonical Sudoku-grid renderer for active games Sudoku tasks; it owns grid layout, highlighted-unit and marked-cell chrome, digit rendering, and traced cell bbox maps.
   - `snake_common.py` is the shared Snake construction/rules layer; it owns cardinal moves, one-step and planned-sequence simulation, safe-direction evaluation, coordinate ids, and sample validation for active Snake tasks and later siblings.
   - `snake_scene.py` is the canonical Snake-grid renderer for active games Snake tasks; it owns square-board layout, head/body/food drawing, style palettes, and traced cell bbox maps.
   - `sampling.py` is the shared games-domain axis sampler layer; it owns the reusable balanced `query_id` and named-axis resolution used across games task groups.
   - `complexity.py` is the shared games-domain complexity layer; it owns normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction for games tasks.
   - `style.py` is the shared games-domain theme layer; it owns reusable bingo / dots-and-boxes / card / domino / Reversi / Connect Four / Checkers / Morris / Go / Sudoku chrome, shadow, and highlight styling so new games tasks do not hardcode separate palettes.
   - `visual_defaults.py` is the canonical games-domain background/noise loader layer shared across future games task groups.
15. Pages: `trace/tasks/pages/shared/common.py`, `complexity.py`, `visual_defaults.py`, `text_generation.py`, `gui_render_params.py`, `document_common.py`, `sectioned_document_common.py`, `arithmetic_common.py`, `document_scene.py`, and diagram-structured helpers under `trace/tasks/pages/shared/diagram/`
   - `common.py` provides canonical page-axis resolution and prompt-facing bbox evidence projection helpers for page tasks that sample semantic and visual variants deterministically.
   - `common.py` also owns the canonical field-spec and section-spec builders for structured page tasks that derive prompt/trace fields from typed visible values.
   - `complexity.py` is the shared pages-domain complexity layer; it owns the normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction.
   - `visual_defaults.py` is the canonical pages-domain background/noise loader layer shared across future page task groups.
   - `text_generation.py` is the shared typed field-value generator layer; it owns deterministic names, IDs, dates, contact strings, currency text, and coherent scene-level field-value sets for structured page/form scenes.
   - `gui_render_params.py` owns the repeated GUI-window integer render-parameter resolver used by page tasks with app-window/control-grid chrome.
   - `document_common.py` is the shared structured-page helper layer for form/receipt/invoice tasks; it owns task/scene variant resolution, the canonical scene-title mapping, readout scene field templates, page dataset construction for active field-lookup tasks, and render-param resolution for the shared form/invoice/receipt grammar.
   - `sectioned_document_common.py` is the shared section-aware field-template layer for the structured page grammar reused by arithmetic and layout tasks; it owns the canonical sectioned field templates, target amount-section mapping, field-count bounds, and typed visible-value builders for grouped page scenes.
   - `information_style.py` is the pages-domain adapter over shared `information_scene_style`; use it to map shared structured-information roles onto page fill, page outline, field boxes, labels, values, dividers, shadows, and background roles while preserving visible text/value semantics.
   - `diagram/map_common.py` is the shared printed-map construction layer; it owns map task/scene variant resolution, connected grid-backed landmark sampling, route/zone query construction, and render-param resolution for map-navigation page tasks.
   - `diagram/map_scene.py` is the shared printed-map renderer; it owns zone fills, walking paths, highlighted routes, landmark boxes, compass chrome, and trace-backed bbox maps for map-navigation evidence.
   - `arithmetic_common.py` is the shared section-local arithmetic helper layer; it owns supported arithmetic variants, expression-operator contracts, and deterministic expression-dataset construction for active page arithmetic tasks.
   - `reconciliation_common.py` is the shared cross-form reconciliation helper layer; it owns matched item-code sampling, quantity/unit-value constraints, variant-specific answer construction, and render-param resolution for paired-form page tasks.
   - `reconciliation_scene.py` is the shared cross-form renderer; it owns side-by-side form panels, header fields, line-item rows, and traced cell-value bbox maps.
   - `document_scene.py` is the canonical structured-page renderer for active page tasks; it owns the form/invoice/receipt page grammars, fitted field-label/value rendering, optional section chrome, checkbox-section rendering, and page/section/field/checkbox bbox tracing.
   - `shared/diagram/common.py` provides canonical diagram-axis resolution, prompt-facing bbox projection, and shared panel/title helpers for page tasks that use diagram-like visual structure.
   - `shared/diagram/complexity.py` owns normalized `[0,1]` scoring helpers, complexity-weight resolution, and weighted-mean `TaskComplexity` construction for diagram-like page tasks.
   - `shared/diagram/visual_defaults.py` owns background/noise loader defaults for diagram-like page task groups.
   - `shared/diagram/hierarchy_common.py` and `hierarchy_scene.py` own rooted-tree count construction, tree layout, connector routing, node drawing, and traced node/edge bbox maps.
   - `shared/diagram/cycle_common.py` and `cycle_scene.py` own directed-cycle construction, direction sampling, stage placement, and traced stage/edge bbox maps.

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

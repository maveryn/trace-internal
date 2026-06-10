# Geometry Scene-Package Migration Roadmap

This is the tracked migration roadmap for migrating the `geometry` domain under
`docs/workflows/SCENE_PACKAGE_MIGRATION/README.md`.
Use it together with:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/SCENE_REFACTOR_GUIDELINES.md
docs/workflows/SCENE_PACKAGE_MIGRATION/GEOMETRY_SCENE_REFACTOR_GUIDELINES.md
docs/workflows/SCENE_PACKAGE_MIGRATION/DOMAIN_AUDIT_PLAYBOOK.md
docs/domains/GEOMETRY_TASK_SETUP.md
```

Do not treat the current geometry source layout as proof that the domain is
migrated. The current repo has geometry scene folders and per-task-looking
files, but the previous migration attempt was partly structural and must be
reviewed scene by scene for objective ownership, shared helper boundaries,
prompt/config hygiene, and stale generated artifacts.

## Status

- Domain: `geometry`
- Current static source inventory: 46 scene folders and 192 public-looking task
  files under `trace/tasks/geometry/<scene_id>/`.
- Registry check status: currently blocked by non-geometry import debt in the
  global task import path. Use source inventory for this plan, then re-run the
  registry check after global imports are healthy.
- Proposed task count: keep 192 unless a scene-level contract review finds a
  genuine merge/split need. This roadmap is a structural and ownership
  migration plan, not a coverage expansion.
- Migration state: not complete. Geometry should be treated as structurally
  routed but objective-ownership pending until every scene passes the gates
  below.

## Geometry-Specific Migration Model

Geometry scenes are different from games. Most scenes do not need game
mechanics, legal move enumerators, or board-state transitions. The reusable
layers are usually diagram construction, geometry relations, rendering,
measurement label placement, style/layout variation, and annotation projection.

The public task file still owns the objective program. A geometry task file
should make it clear which theorem, relation, measurement, comparison, or
construction is being asked; which operands are sampled; how the final answer
is bound; and which visible witnesses are annotated.

### Scene-Local Shared Split

Use only the files that fit the scene. Do not create empty placeholders.

```text
trace/tasks/geometry/<scene_id>/
  <objective_contract>.py
  shared/
    defaults.py
    state.py
    construction.py
    relations.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Suggested roles:

- `defaults.py`: fallback supports, scene dimensions, and small resolver
  constants. Prompt wording, static slots, examples, and required slot
  declarations belong in prompt assets.
- `state.py`: scene dataclasses, entity ids, symbolic specs, intrinsic
  constants.
- `construction.py`: reusable diagram construction primitives, candidate
  layout generation, shape/solid/curve scene specs.
- `relations.py`: pure geometry formulas, theorem relations, transformation
  functions, validators.
- `sampling.py`: neutral random-axis selection and candidate generation that
  does not decide a public objective.
- `rendering.py`: drawing, style, label placement, final layout jitter, and
  render maps.
- `annotations.py`: point/bbox/keyed annotation projection primitives.
- `prompts.py`: thin prompt artifact assembly from prompt assets and
  task-provided dynamic slots.
- `output.py`: optional final `TaskOutput` assembly only after a task file has
  already bound answer, annotation, dynamic prompt slots, and task trace. If it
  chooses objective semantics, move that code back to the task file.

### Public Task File Owns

Each `trace/tasks/geometry/<scene_id>/<objective_contract>.py` file must own:

1. the registered public task class;
2. objective-specific query/parameter selection;
3. semantic target construction and uniqueness constraints;
4. final answer binding;
5. final `annotation_gt` binding, including role keys when roles matter;
6. task-specific dynamic prompt slots and prompt metadata;
7. task-specific trace fields and validation checks.

It must not:

1. be a wrapper around a shared source task;
2. copy the full old scene module into every sibling task file;
3. contain sibling public task ids/classes;
4. call a shared full-output dispatcher that branches by objective;
5. hide answer and annotation binding in shared code for multiple objectives.

## Non-Negotiable Gates

Before `geometry` can be marked migrated:

1. `trace.tasks` imports all active geometry tasks.
2. Registered/default geometry task count matches the source inventory and
   domain docs.
3. Every active task id maps to
   `trace/tasks/geometry/<scene_id>/<objective_contract>.py`.
4. Every public task file defines exactly one registered public task class and
   one active public task id.
5. Public task files are not wrappers and are not near-exact copies of sibling
   task files.
6. Scene `shared/` modules do not return complete `TaskOutput` objects for
   multiple public objectives.
7. Scene `shared/` modules do not branch over public objective contracts to
   choose answer/annotation programs.
8. Domain shared contains only cross-scene geometry helpers, not scene-local
   helpers.
9. Geometry code/config/docs/prompts/review artifacts use annotation
   terminology.
10. Geometry code/config/docs/prompts do not use legacy group routing as active
    runtime, metadata, or compatibility behavior.
11. Configs are scene-keyed under `configs/domains/geometry/<scene_id>.yaml`.
12. Prompt assets under `prompts/geometry/<scene_id>/` contain only bundles used
    by that scene.
13. Retired ids, stale docs, stale prompt bundles, stale configs, and stale
    review folders are deleted, not kept as compatibility aliases.
14. Review artifacts are regenerated under `review/task-reviews/geometry/`.
15. Enforcement tests include wrapper/copy-split/shared-dispatch checks.

## Preflight Fixes Before Scene Loop

Do these once before migrating scenes:

1. Demote `geometry` from completed migration status until the domain is
   actually complete. It is currently listed in
   `MIGRATED_SCENE_PACKAGE_DOMAINS`; remove it there before implementation.
2. If runtime routing needs geometry scene-package behavior during cleanup,
   add all geometry scenes to `MIGRATED_SCENE_PACKAGE_SCENES["geometry"]` and
   `SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_PENDING_SCENES["geometry"]`.
3. Add/extend enforcement checks for geometry:
   - exact and near-duplicate sibling public task files;
   - wrapper-only public task files;
   - public task files importing source-task wrappers or fixed-query mixins;
   - public task files defining sibling public ids/classes;
   - scene shared modules importing `TaskOutput`;
   - scene shared modules containing public task ids or objective dispatch;
   - prompt/config/doc literal scrub for active legacy routing and historical
     evidence terminology.
4. Restore a reliable registry import path before using registry counts as
   source of truth.
5. Record the baseline source inventory and current review artifact inventory.
6. Do not start by promoting helpers into `trace/tasks/geometry/shared/`.
   Clean scene-local ownership first; promote only in the final checkpoint.

## Domain Shared Boundary

Keep in `trace/tasks/geometry/shared/` only narrow helpers reused by two or
more cleaned scenes:

- vector and point geometry primitives;
- polygon formulas and transformation primitives;
- annotation artifact helpers for common point/bbox/keyed patterns;
- scene rotation/jitter utilities;
- diagram style, font, text, and label placement primitives that are genuinely
  scene-neutral;
- graph-paper/grid coordinate helpers reused by graph-paper-like scenes.

Move out of domain shared during the final checkpoint:

- helpers that mention one scene id or one scene's vocabulary;
- scene-local renderers;
- full task generators;
- prompt assemblers that assume one scene;
- theorem dispatchers used by only one scene;
- any helper whose only caller is one scene after cleanup.

## One-Pass Execution Model

1. Preflight the domain.
2. Process every scene in the order below.
3. For each scene, complete source cleanup, config/prompt/docs/test sync,
   review artifact regeneration, and local checks before moving on.
4. After all scenes pass local gates, do one domain-shared consolidation
   checkpoint.
5. Run whole-domain validation and only then mark geometry migrated.

## Per-Scene Completion Checklist

Each completed scene should get a note in this file:

```text
Completion note:
- source ownership:
- split/merge decision:
- scene shared helpers:
- domain shared candidates deferred:
- config/prompt/docs updated:
- task reviews regenerated/stale folders purged:
- checks:
- final post-migration review:
- blockers:
```

## Scene Loop Order

Start with small scenes to establish the geometry conventions, then move into
larger families:

1. `area_partition`
2. `bearing_route`
3. `circle_centerline_overlap`
4. `circle_pair_tangents`
5. `concentric_chord`
6. `cone_net`
7. `paper_fold`
8. `pythagorean_dissection`
9. `pythagorean_tree`
10. `cylinder_wrap`
11. `right_triangle_altitude_theorem`
12. `parallel_segment_proportion`
13. `polygon_angle_chase`
14. `angle_relations`
15. `split_triangle_angle_chase`
16. `split_triangle_trig_chain`
17. `triangle_congruence_correspondence`
18. `triangle_relations`
19. `special_quadrilateral`
20. `incircle_tangents`
21. `circle_polygon_composite`
22. `circle_theorem`
23. `sector`
24. `tangent_packing`
25. `regular_polygon_decomposition`
26. `marked_polygon_equation`
27. `similar_figure_measure_transfer`
28. `shape_gallery`
29. `measuring_tools`
30. `coordinate_composite`
31. `coordinate_panels`
32. `coordinate_plane`
33. `graph_paper`
34. `function_graph`
35. `function_panels`
36. `composite_shape`
37. `container_volume_transfer`
38. `rectangular_solid`
39. `cuboid_views`
40. `solid_formula`
41. `solid_cross_section`
42. `solid_revolution`
43. `volume_equivalence_conversion`
44. `wire_shape_conversion`
45. `survey_traverse`
46. `trapezoid_extension`

## Per-Scene Roadmap

### `area_partition`

- Tasks: `total_area_value`.
- Scene contract: partitioned 2D region with an outer container and one or more
  shaded/target subregions.
- Shared scene helpers: region construction, area arithmetic primitives,
  rendering, keyed region annotation projection.
- Public task ownership: choose area relation, bind numeric total area answer,
  bind keyed annotation roles for outer/known/target regions where needed.
- Migration action: use as first reference scene; keep it minimal and
  objective-owned.

### `bearing_route`

- Tasks: `endpoint_position_label`, `final_bearing_value`.
- Scene contract: routed polyline with bearing labels and endpoint/position
  candidates.
- Shared scene helpers: route geometry, compass/bearing math, point projection,
  route renderer, label placement.
- Public task ownership:
  - `endpoint_position_label`: construct candidate endpoints, bind option
    label and candidate/route annotation.
  - `final_bearing_value`: compute final bearing from visible route, bind
    integer answer and point/segment annotation.
- Migration action: avoid a shared output builder that chooses label versus
  numeric objective.

### `circle_centerline_overlap`

- Tasks: `segment_length_value`.
- Scene contract: collinear circle centers with overlapping/tangent circle
  spans and visible segment labels.
- Shared scene helpers: circle placement, centerline segment computations,
  renderer, center/segment annotation projection.
- Public task ownership: choose missing segment relation, solve numeric
  length, bind annotation to the minimal circle/segment witnesses.

### `circle_pair_tangents`

- Tasks: `center_distance_value`, `common_tangent_length_value`.
- Scene contract: two circles with centerline/radii/tangent construction.
- Shared scene helpers: tangent geometry, circle pair construction, rendering,
  point/segment annotation projection.
- Public task ownership:
  - `center_distance_value`: solve center distance from radii/tangent inputs.
  - `common_tangent_length_value`: solve tangent segment length from radii and
    center distance.
- Migration action: formulas can be shared; target relation and annotation
  roles stay in each task file.

### `concentric_chord`

- Tasks: `chord_length_from_radii`, `inner_radius_from_chord`.
- Scene contract: concentric circles with chord/radius construction.
- Shared scene helpers: concentric circle construction, chord formulas,
  renderer, keyed point/segment annotation.
- Public task ownership: each file owns the missing-value relation and
  annotation roles.

### `cone_net`

- Tasks: `base_radius_from_sector_angle`, `height_from_sector_angle`.
- Scene contract: cone net with circular sector and base circle/labels.
- Shared scene helpers: sector/cone formulas, net geometry, rendering,
  annotation projection.
- Public task ownership: choose which cone dimension is missing and bind answer
  plus relevant sector/base witnesses.

### `paper_fold`

- Tasks: `paper_fold_angle_value`.
- Scene contract: folded paper/ray diagram with angle labels.
- Shared scene helpers: fold construction, angle relation formulas, rendering,
  point annotation.
- Public task ownership: bind target angle answer and minimal ray/fold
  annotation.

### `pythagorean_dissection`

- Tasks: `pythagorean_square_area_value`.
- Scene contract: right-triangle/square dissection diagram.
- Shared scene helpers: right-triangle construction, square-area formulas,
  renderer, region annotation.
- Public task ownership: choose target square/area relation and bind answer.

### `pythagorean_tree`

- Tasks: `missing_square_area_value`.
- Scene contract: Pythagorean tree-style square construction.
- Shared scene helpers: square tree layout, Pythagorean area relation,
  rendering, region annotation.
- Public task ownership: choose missing square and bind area answer.

### `cylinder_wrap`

- Tasks: `surface_path_length_value`, `wrapped_mark_position_label`.
- Scene contract: cylinder plus unwrapped rectangle surface view.
- Shared scene helpers: cylinder-to-net mapping, wrap geometry, renderer,
  net/cylinder annotation projection.
- Public task ownership:
  - `surface_path_length_value`: solve path length.
  - `wrapped_mark_position_label`: select wrapped mark option.

### `right_triangle_altitude_theorem`

- Tasks: `altitude_to_hypotenuse_value`, `leg_projection_length_value`.
- Scene contract: right triangle with altitude to hypotenuse and projection
  segments.
- Shared scene helpers: altitude/projection formulas, triangle construction,
  renderer, point/segment annotation projection.
- Public task ownership: each theorem relation stays in its objective file.

### `parallel_segment_proportion`

- Tasks: `segment_length_value`, `variable_value`.
- Scene contract: parallel-line proportional segment diagram.
- Shared scene helpers: transversal layout, proportion solver, renderer,
  keyed segment annotation.
- Public task ownership:
  - `segment_length_value`: numeric segment length.
  - `variable_value`: algebraic variable solve.

### `polygon_angle_chase`

- Tasks: `parallel_line_angle_value`, `polygon_interior_angle_value`,
  `symmetry_angle_value`.
- Scene contract: polygon/line angle-chase diagram with visible angle labels.
- Shared scene helpers: polygon generation, angle equations, renderer, angle
  point annotation.
- Public task ownership: each task owns its angle relation family and prompt
  slots.

### `angle_relations`

- Tasks: `algebraic_angle_value`, `parallel_supplement_angle`,
  `triangle_exterior_angle`.
- Scene contract: ray/line/triangle angle relation diagrams.
- Shared scene helpers: angle construction, expression formatting, theorem
  relation helpers, renderer.
- Public task ownership: objective file owns which relation is solved and
  which target angle is annotated.
- Migration note: first cleaned geometry v2 scene. The two prior algebraic
  extension public task ids are retired and represented as query ids under
  `algebraic_angle_value`.

### `split_triangle_angle_chase`

- Tasks: `target_angle_value`.
- Scene contract: split/dual triangle angle-chase setup.
- Shared scene helpers: split-triangle construction, angle relation solver,
  renderer, annotation projection.
- Public task ownership: bind target angle value and witnesses.

### `split_triangle_trig_chain`

- Tasks: `side_length_value`.
- Scene contract: split triangle with chained trigonometric relations.
- Shared scene helpers: triangle construction, trig relation formulas,
  renderer, annotation projection.
- Public task ownership: bind target side-length answer and role annotation.

### `triangle_congruence_correspondence`

- Tasks: `algebraic_side_value`, `corresponding_angle_value`,
  `corresponding_side_value`.
- Scene contract: paired congruent triangles with standard markings.
- Shared scene helpers: triangle pair construction, correspondence mapping,
  mark rendering, annotation projection.
- Public task ownership:
  - side/angle transfer tasks bind the corresponding part relation;
  - algebraic side task binds expression solve.

### `triangle_relations`

- Tasks: `angle_bisector_segment_value_angle_bisector_base_length`,
  `angle_bisector_segment_value_angle_bisector_split_length`,
  `angle_bisector_variable_value`, `angle_of_elevation_value`,
  `centroid_median_segment_value_centroid_vertex_segment_length`,
  `centroid_median_segment_value_centroid_whole_median_length`,
  `parallel_section_base_length`, `parallel_section_cross_length`,
  `pythagorean_length_value_chained_rectangle_diagonal_length`,
  `pythagorean_length_value_rectangle_triangle_shared_height_length`,
  `right_triangle_inverse_trig_angle_angle_from_adjacent_hypotenuse`,
  `right_triangle_inverse_trig_angle_angle_from_opposite_adjacent`,
  `right_triangle_inverse_trig_angle_angle_from_opposite_hypotenuse`,
  `right_triangle_missing_side_value_ground_from_angle_and_height`,
  `right_triangle_missing_side_value_ground_from_angle_and_hypotenuse`,
  `right_triangle_missing_side_value_height_from_angle_and_ground`,
  `right_triangle_missing_side_value_height_from_angle_and_hypotenuse`,
  `right_triangle_missing_side_value_hypotenuse_from_angle_and_height`,
  `similar_triangles_side_length`.
- Scene contract: heterogeneous triangle theorem diagrams. This scene may need
  subfamily shared modules under `shared/` such as `right_triangle.py`,
  `angle_bisector.py`, `centroid.py`, `parallel_section.py`, and
  `pythagorean.py`.
- Migration action: do not create one giant triangle dispatcher. Split shared
  theorem primitives by subfamily, and keep each objective file responsible for
  answer/annotation binding.

### `special_quadrilateral`

- Tasks: `algebraic_angle_value`, `diagonal_angle_value`,
  `segment_length_value`.
- Scene contract: special quadrilateral with marked sides/angles/diagonals.
- Shared scene helpers: quadrilateral prototypes, marking renderer, relation
  formulas, annotation projection.
- Public task ownership: separate angle, diagonal-angle, and segment-length
  objective programs.

### `incircle_tangents`

- Tasks: `incircle_radius_from_area_value`,
  `incircle_tangent_perimeter_value`.
- Scene contract: tangential polygon/triangle with incircle and tangent
  segments.
- Shared scene helpers: incircle construction, tangent/perimeter formulas,
  renderer.
- Public task ownership: bind target metric and annotation roles.

### `circle_polygon_composite`

- Tasks: `square_circle_tangent_angle_value`,
  `tangential_quadrilateral_side_sum_value`.
- Scene contract: circle-polygon composite theorem diagrams.
- Shared scene helpers: circle/polygon placement, tangency formulas, renderer,
  annotation projection.
- Public task ownership: each file owns its theorem relation.

### `circle_theorem`

- Tasks: `chord_length_from_radius_angle_value`,
  `cyclic_quadrilateral_angle_value`,
  `diameter_perpendicular_chord_length_value`,
  `external_secant_angle_value`,
  `inscribed_angle_value_central_angle_from_inscribed`,
  `inscribed_angle_value_inscribed_angle_from_arc`,
  `inscribed_angle_value_inscribed_angle_from_central`,
  `intersecting_chords_arc_measure_value`, `multi_step_angle_value`,
  `secant_secant_length_value`,
  `tangent_chord_angle_value_tangent_chord_angle_from_arc`,
  `tangent_chord_angle_value_tangent_chord_angle_from_inscribed`,
  `tangent_radius_right_triangle_length_value`,
  `tangent_secant_length_value`.
- Scene contract: circle theorem diagrams with radii/chords/secants/tangents.
- Shared scene helpers: circle construction primitives, theorem formulas,
  label placement, rendering, point/segment annotation projection.
- Migration action: likely the highest-risk theorem dispatcher scene. Extract
  formula/render primitives, but keep every theorem objective file readable as
  that theorem's answer and annotation program.

### `sector`

- Tasks: `angle_from_sector_measure_angle_from_arc_length_and_radius`,
  `angle_from_sector_measure_angle_from_area_and_radius`,
  `arc_length_value_arc_length_from_area_and_radius`,
  `arc_length_value_arc_length_from_radius_and_supplement_angle`,
  `related_angle_from_sector_measure_complement_angle_from_arc_length`,
  `related_angle_from_sector_measure_remaining_angle_from_sector_measure`,
  `related_angle_from_sector_measure_supplement_angle_from_area`,
  `sector_area_value_area_from_arc_length_and_radius`,
  `sector_area_value_area_from_radius_and_complement_angle`.
- Scene contract: sector/circle diagram with arc length, radius, area, and
  related angle relations.
- Shared scene helpers: sector formulas, sector renderer, angle/arc annotation.
- Public task ownership: each objective owns target metric and relation.

### `tangent_packing`

- Tasks: `circle_in_square_gap_area`, `circle_in_square_radius_from_gap_area`,
  `square_in_circle_gap_area`, `square_in_circle_side_from_gap_area`,
  `two_circles_in_rectangle_gap_area`,
  `two_circles_in_rectangle_radius_from_gap_area`.
- Scene contract: tangent packed shapes with gap area or missing dimension.
- Shared scene helpers: packed-shape construction, area relations, renderer,
  region annotation.
- Public task ownership: answer target and annotation witnesses stay local to
  each file.

### `regular_polygon_decomposition`

- Tasks: `central_angle_value`, `perimeter_value`, `piece_area_value`,
  `side_length_value`.
- Scene contract: regular polygon decomposed into equal pieces/triangles.
- Shared scene helpers: regular polygon geometry, decomposition renderer,
  piece/side annotation.
- Public task ownership: target metric objective stays in the task file.

### `marked_polygon_equation`

- Tasks: `angle_value`, `angle_variable_value`, `side_length_value`,
  `side_variable_value`.
- Scene contract: polygon with standard equality marks and algebraic/number
  labels.
- Shared scene helpers: marked polygon construction, equation solver,
  renderer, keyed mark/side/angle annotation.
- Public task ownership: numeric side/angle and variable side/angle solves
  should remain distinct objective programs.

### `similar_figure_measure_transfer`

- Tasks: `area_scale_side_length_value`, `corresponding_side_value`,
  `scale_factor_value`, `side_length_from_expression_value`,
  `variable_value`.
- Scene contract: similar figures with corresponding marks and scale/area
  relations.
- Shared scene helpers: similar figure construction, correspondence maps,
  scale relations, renderer.
- Public task ownership: each target metric or algebraic solve owns answer and
  annotation binding.

### `shape_gallery`

- Tasks: `congruent_count`, `reflection_match`, `rotation_match`,
  `similar_count`, `translation_match`.
- Scene contract: gallery of shapes/options with geometric transformations.
- Shared scene helpers: shape generation, transforms, option layout, renderer,
  bbox annotation projection.
- Public task ownership: count versus match tasks own different answer schemas
  and annotation contracts.

### `measuring_tools`

- Tasks: `shape_angle_value_quadrilateral_vertex_protractor_reading`,
  `shape_angle_value_triangle_vertex_protractor_reading`,
  `shape_length_value_circle_radius_ruler_reading`,
  `shape_length_value_polygon_side_ruler_reading`.
- Scene contract: geometric shape drawn with a visible ruler/protractor tool.
- Shared scene helpers: instrument renderer, tool calibration, shape layout,
  readout annotation.
- Public task ownership: angle and length readout tasks own the target tool
  placement and answer binding.

### `coordinate_composite`

- Tasks: `intersection_point_count`.
- Scene contract: coordinate-plane composite with multiple plotted objects.
- Shared scene helpers: coordinate grid, object plotting, intersection
  computation, point annotation.
- Public task ownership: choose intersection predicate and bind count answer.

### `coordinate_panels`

- Tasks: `quadrilateral_shape_match_label`.
- Scene contract: multiple coordinate panels/options for shape matching.
- Shared scene helpers: coordinate panel layout, quadrilateral classifier,
  option rendering, keyed/option annotation.
- Public task ownership: choose target quadrilateral and bind option label.

### `coordinate_plane`

- Tasks: `collinear_point_count`, `locus_panel_match_label`,
  `locus_point_label`, `missing_endpoint_label`, `point_in_polygon_count`,
  `quadrilateral_completion_label`, `reflected_point_label`,
  `rotated_point_label`, `same_quadrant_point_count`, `section_point_label`,
  `segment_relation_count`, `translated_point_label`.
- Scene contract: coordinate grid with points, segments, polygons, transforms,
  and visual options.
- Shared scene helpers: grid renderer, coordinate transforms, point/segment
  classifiers, option layout, point/bbox annotation projection.
- Public task ownership: each transform/count/locus/option objective binds its
  own target and annotation.
- Migration note: this scene is large; split `shared/` by primitive if needed:
  `grid.py`, `points.py`, `transforms.py`, `options.py`, `rendering.py`.

### `graph_paper`

- Tasks: `angle_extremum_label`, `angle_type_count`, `angle_value`,
  `area_extremum_label`, `circle_circumference_value`, `ellipse_area_value`,
  `length_extremum_label`, `line_slope_value`, `perimeter_extremum_label`,
  `polygon_area_value`, `polygon_convexity_count`,
  `polygon_perimeter_value`, `quadrilateral_type_count`,
  `shape_type_count`, `triangle_type_count`.
- Scene contract: graph-paper grid with labeled geometric objects.
- Shared scene helpers: grid renderer, object generation, measurement
  formulas, classifiers, comparison helpers, annotation projection.
- Migration note: this scene already has many nested shared modules. Keep
  measurement/count/comparison primitives shared, but prevent shared modules
  from returning complete outputs for several public objectives.

### `function_graph`

- Tasks: `average_rate_value`, `extremum_count_local_extremum_count`,
  `extremum_count_turning_point_count`, `reference_line_crossing_count`.
- Scene contract: single function graph with axes and reference marks.
- Shared scene helpers: function sampler, curve rendering, axis layout,
  crossing/extremum computation, point annotation.
- Public task ownership: count/value objective stays in each file.

### `function_panels`

- Tasks: `function_status_label`, `intersection_property_label`,
  `one_to_one_status_label`, `range_match_label`, `sign_interval_label`,
  `x_axis_symmetry_label`.
- Scene contract: panel grid of function graphs/options.
- Shared scene helpers: panel dataset sampler, curve renderer, option layout,
  property evaluators, selected-panel annotation.
- Public task ownership: each property objective owns property target and
  option answer binding.

### `composite_shape`

- Tasks: `composite_area_value`, `house_outline_perimeter`,
  `missing_width_from_semicircle_cap_area`,
  `missing_width_from_semicircle_cutout_area`,
  `rectangle_quarter_sector_cutout_area`,
  `rectangle_quarter_sector_cutout_perimeter`,
  `rectangle_semicircle_cap_area`, `rectangle_semicircle_cap_perimeter`,
  `rectangle_semicircle_cutout_area`,
  `rectangle_semicircle_cutout_perimeter`,
  `sector_angle_from_arc_length`, `sector_angle_from_area`,
  `tabbed_rectilinear_perimeter`.
- Scene contract: composite 2D shapes with rectilinear and curved components.
- Shared scene helpers: component geometry, area/perimeter formulas, renderer,
  region/segment annotation.
- Migration note: avoid one broad composite-measurement base that hides all
  objectives. Each metric/objective file should own target formula selection.

### `container_volume_transfer`

- Tasks: `fill_count_value`, `resulting_height_value`,
  `target_capacity_value`, `transferred_volume_value`.
- Scene contract: containers with visible volumes/heights/transfers.
- Shared scene helpers: container specs, volume formulas, renderer, level/shape
  annotation.
- Public task ownership: fill count, resulting height, capacity, and
  transferred-volume objectives remain separate.

### `rectangular_solid`

- Tasks: `cube_edge_from_frame_length_value`, `cuboid_surface_area_value`,
  `cuboid_volume_missing_dimension_value`, `open_box_net_dimension_value`.
- Scene contract: rectangular solids, frames, nets, and labeled dimensions.
- Shared scene helpers: cuboid formulas, isometric/net rendering, dimension
  annotation projection.
- Public task ownership: each solid formula target stays in task file.

### `cuboid_views`

- Tasks: `cuboid_projection_surface_area_value`.
- Scene contract: orthographic cuboid views.
- Shared scene helpers: top/front/side view construction, visible-face area
  formulas, renderer.
- Public task ownership: bind requested projected surface-area answer.

### `solid_formula`

- Tasks: `cylinder_cone_height_from_volume_radius`,
  `cylinder_cone_radius_from_volume_heights`,
  `house_prism_length_from_volume`, `prism_pyramid_height_from_volume`.
- Scene contract: labeled 3D formula solids.
- Shared scene helpers: solid shape specs, formula relations, renderer,
  dimension annotation.
- Public task ownership: each formula relation stays local.

### `solid_cross_section`

- Tasks: `cone_parallel_slice_area`, `square_pyramid_parallel_slice_area`.
- Scene contract: solid with parallel slice/cross-section.
- Shared scene helpers: similar-section formulas, solid/slice renderer,
  slice annotation.
- Public task ownership: bind slice-area target and witnesses.

### `solid_revolution`

- Tasks: `revolution_cone_volume_value`, `revolution_cylinder_volume_value`,
  `revolution_double_cone_volume_value`, `revolution_frustum_volume_value`.
- Scene contract: 2D profile revolved into a 3D solid.
- Shared scene helpers: profile construction, revolution formulas, renderer,
  annotation projection.
- Public task ownership: each solid-of-revolution volume relation stays in its
  objective file.

### `volume_equivalence_conversion`

- Tasks: `equal_volume_option_label`, `missing_dimension_value`.
- Scene contract: pairs/options of equal-volume solids or converted shapes.
- Shared scene helpers: volume formulas, option construction, renderer.
- Public task ownership: option label versus missing dimension have distinct
  answer schemas and annotation binding.

### `wire_shape_conversion`

- Tasks: `frame_edge_length_value`, `missing_dimension_value`,
  `wire_length_value`.
- Scene contract: wire/frame reshaped between geometric forms with conserved
  perimeter/wire length.
- Shared scene helpers: wire-length formulas, shape renderers, annotation.
- Public task ownership: target metric remains local.

### `survey_traverse`

- Tasks: `bearing_angle_value`, `station_elevation_value`,
  `traverse_area_value`.
- Scene contract: surveying sketches, field notes, routes, levels, and area
  diagrams.
- Shared scene helpers: survey math, station geometry, field-note rendering,
  keyed point/bbox annotation projection.
- Public task ownership: bearing, elevation, and traverse-area formulas are
  distinct objective programs.

### `trapezoid_extension`

- Tasks: `extension_from_parallelogram_area`,
  `extension_from_parallelogram_perimeter`,
  `trapezoid_area_from_bases_and_height`,
  `trapezoid_area_from_extension_and_height`,
  `trapezoid_area_from_parallelogram_area`.
- Scene contract: trapezoid plus extension/parallelogram relation diagram.
- Shared scene helpers: trapezoid construction, extension formulas, renderer,
  segment/region annotation.
- Public task ownership: each area/extension/perimeter relation owns answer
  and annotation binding.

## Final Domain-Shared Consolidation Checkpoint

After all scenes pass local gates:

1. Compare scene-local helpers for real duplication.
2. Promote only narrow cross-scene helpers into `trace/tasks/geometry/shared/`.
3. Delete scene-local copies only after callers are updated and tests pass.
4. Re-run enforcement tests to ensure promotion did not recreate dispatchers.
5. Update this roadmap with final promotion decisions.

Likely promotion candidates:

- readout-safe geometry text/label placement;
- single-object rotation/jitter with annotation projection;
- keyed point/bbox annotation helpers;
- option-panel layout for geometry visual MCQ tasks;
- vector/line/circle/polygon formula primitives already used by several
  scenes.

Do not promote:

- one-scene theorem builders;
- one-scene renderers;
- broad formula dispatchers;
- prompt assemblers with one scene's slot vocabulary;
- any helper that constructs final `TaskOutput` for multiple objectives.

## Validation Commands

Use these after each scene or scene wave:

```bash
python -m compileall -q trace/tasks/geometry/<scene_id>
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews
```

Use these after the full domain pass:

```bash
python -m compileall -q trace/tasks/geometry trace/core/scene_package_migration.py trace/tasks/registry.py trace/tasks/__init__.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_scene_package_migration_contracts.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_geometry*.py
```

Reload the review app index after review artifacts change:

```bash
curl -sS -X POST http://127.0.0.1:7860/api/reload
```

## Current Blockers

- Global `trace.tasks` import is currently blocked by non-geometry scene-package
  debt, so registry/default geometry counts must be rechecked after that is
  fixed.
- Geometry has been demoted from domain-level migrated status to scene-level
  structural routing. Non-cleaned scenes remain objective-ownership pending
  until their own v2 pass is complete.
- Current source files include structurally routed but objective-ownership
  suspicious scenes; do not build new scenes from those as design examples
  until they pass the v2 gates.

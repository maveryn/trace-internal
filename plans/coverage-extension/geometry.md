# Geometry Coverage Extension

## Scope

This note tracks **remaining** geometry-domain coverage gaps after the 2026-05
analytical/formula-geometry expansion. It intentionally omits scene families
that are now covered by active tasks, even if they were listed as candidate
gaps in prior reviews.

Geometry should own a task when the verifier source of truth is a synthetic
mathematical object: points, segments, polygons, circles, function graphs,
solids, construction marks, formula annotations, and diagrammatic geometric
relations. Route tasks elsewhere when the main reasoning source is not pure
geometry:

- `physics`: force, torque, optics, circuits, fluids, or other physical laws.
- `three_d`: camera/view/object spatial relations in rendered 3D scenes.
- `puzzles`: state manipulation, tiling, folding-as-puzzle, jigsaw matching,
  rule completion, or missing-piece selection.
- `charts`: empirical or tabular data visualizations rather than mathematical
  function graphs or geometric constructions.

## Current Status

Canonical active-surface source: `docs/domains/GEOMETRY_TASK_SETUP.md`.

As of this update, geometry has 80 active public task ids:

| Task group | Public task count |
|---|---:|
| `measurement` | 42 |
| `circle` | 7 |
| `coordinate` | 11 |
| `counting` | 5 |
| `comparison` | 4 |
| `analytical` | 6 |
| `graphing` | 3 |
| `similarity` | 1 |
| `transformation` | 1 |

The current scene inventory is:

| Task group | Scene id | Public tasks |
|---|---|---:|
| `measurement` | `single_object_graph_paper` | 6 |
| `measurement` | `angle_relation_diagram` | 2 |
| `measurement` | `triangle_special_segment_diagram` | 2 |
| `measurement` | `parallel_section_length_diagram` | 2 |
| `measurement` | `pythagorean_length_diagram` | 1 |
| `measurement` | `pythagorean_square_dissection_diagram` | 1 |
| `measurement` | `rectilinear_composite_shape_diagram` | 2 |
| `measurement` | `curvilinear_composite_shape_diagram` | 4 |
| `measurement` | `sector_formula_diagram` | 2 |
| `measurement` | `right_triangle_trig_diagram` | 2 |
| `measurement` | `paper_fold_measurement_diagram` | 1 |
| `measurement` | `concentric_circle_chord_diagram` | 1 |
| `measurement` | `circle_square_tangent_packing_diagram` | 2 |
| `measurement` | `tangent_polygon_incircle_diagram` | 2 |
| `measurement` | `cone_sector_net_diagram` | 1 |
| `measurement` | `solid_revolution_diagram` | 4 |
| `measurement` | `solid_formula_diagram` | 1 |
| `measurement` | `solid_cross_section_diagram` | 1 |
| `measurement` | `cuboid_orthographic_views_diagram` | 1 |
| `measurement` | `parallelogram_area_partition_diagram` | 1 |
| `measurement` | `triangle_area_partition_diagram` | 1 |
| `measurement` | `trapezoid_extension_to_parallelogram_diagram` | 2 |
| `circle` | `circle_theorem_diagram` | 7 |
| `coordinate` | `coordinate_point_set` | 2 |
| `coordinate` | `coordinate_segment_set` | 1 |
| `coordinate` | `coordinate_polygon_lattice` | 1 |
| `coordinate` | `coordinate_quadrilateral_candidate_diagram` | 1 |
| `coordinate` | `coordinate_quadrilateral_panel_grid` | 1 |
| `coordinate` | `coordinate_algebra_diagram` | 3 |
| `coordinate` | `coordinate_locus_region_diagram` | 2 |
| `counting` | `shape_set_graph_paper` | 5 |
| `comparison` | `multi_object_graph_paper` | 4 |
| `graphing` | `function_graph` | 3 |
| `analytical` | `analytical_function_panel_grid` | 5 |
| `analytical` | `analytical_intersection_panel_grid` | 1 |
| `similarity` | `reference_candidate_similarity_gallery` | 1 |
| `transformation` | `reference_candidate_transformation_gallery` | 1 |

Recent solid expansions include `solid_formula_diagram`, implemented as
compound solid formula reasoning rather than one-step textbook volume. Its active task,
`proposal:geometry/measurement/solid_formula_missing_dimension_value`, is accepted
on `qwen25vl7b` with H/E/Mean/Cap `0.090/0.000/0.178/0.000`.
The next added solid scene is `solid_cross_section_diagram`, implemented for
parallel slices in cones and square pyramids. Its active task,
`proposal:geometry/measurement/solid_cross_section_area_value`, is accepted on
`qwen25vl7b` with H/E/Mean/Cap `0.000/0.000/0.317/0.000`.
The latest coordinate addition is `coordinate_algebra_diagram`, implemented
with midpoint missing-endpoint, section-point, and point-transformation
candidate tasks. It covers midpoint inverse formulas, one-third/two-thirds
section formulas, direct/reference-vector translations, vertical/horizontal
reflections, and 90-degree rotations without overlapping coordinate
measurement or quadrilateral-recognition tasks. All three active tasks are
accepted on `qwen25vl7b`: missing endpoint at H/E/Mean/Cap
`0.080/0.000/0.153/0.000`, section point at
`0.000/0.000/0.344/0.000`, and transformed point at
`0.050/0.030/0.222/0.000`.
The next coordinate addition is `coordinate_locus_region_diagram`, implemented
for shaded coordinate regions defined by circle, annulus, strip, half-plane,
and two-inequality constraints. Its two active tasks are accepted on
`qwen25vl7b`: point membership at H/E/Mean/Cap `0.000/0.050/0.445/0.000`
and panel-region matching at `0.060/0.020/0.285/0.000`.

## Covered Families

The measurement surface now includes the major formula-geometry scene families
added during this pass:

- Curvilinear composites, sector formulas, concentric chord relations,
  incircle tangent polygons, and circle/square tangent-packing.
- Parallel-section/nested-triangle scale, special triangle segments,
  Pythagorean length, Pythagorean square dissection, and area partitions.
- Cone sector nets, solid revolution volumes, compound solid formula diagrams,
  solid cross-sections, cuboid orthographic projection, trapezoid extension to
  parallelogram, and paper-fold measurement.
- Rectilinear composite area/perimeter and basic graph-paper measurements.

Coordinate coverage includes relation/count tasks, quadrilateral completion
and six-panel quadrilateral shape matching, plus coordinate-algebra candidate
tasks for midpoint missing endpoints, section points, translations,
vertical/horizontal reflections, and 90-degree rotations. It also includes
shaded coordinate locus/region tasks for point membership and condition-panel
matching. Circle coverage includes circle theorem tasks and several
formula-first circle measurement scenes.

Function-graph coverage includes count-style graphing, average rate of change,
function/domain-range/symmetry panels, monotonic-interval labels, sign-interval
labels, and intersection-property panels.

## No Longer Considered Coverage Gaps

The following candidate gaps have been addressed enough that they should
not be reopened as standalone coverage items without a more specific new
failure pattern:

| Older gap | Current coverage |
|---|---|
| Curvilinear shaded regions and sector formulas | `curvilinear_composite_shape_diagram`, `sector_formula_diagram` |
| Parallel-section and nested-triangle similarity | `parallel_section_length_diagram` |
| Circle angle/length theorems | `circle_theorem_diagram` |
| Cone net to cone formulas | `cone_sector_net_diagram` |
| Solid of revolution formulas | `solid_revolution_diagram` |
| Direct compound solid formula diagrams | `solid_formula_diagram` |
| Solid cross-section formulas | `solid_cross_section_diagram` |
| Orthographic cuboid formula inference | `cuboid_orthographic_views_diagram` |
| Triangle/parallelogram area-ratio partitions | `triangle_area_partition_diagram`, `parallelogram_area_partition_diagram` |
| Trapezoid completed into a parallelogram | `trapezoid_extension_to_parallelogram_diagram` |
| Circle/square tangency and packing | `circle_square_tangent_packing_diagram` |
| Incircle/tangent-segment triangle formulas | `tangent_polygon_incircle_diagram` |
| Concentric circles with tangent chord | `concentric_circle_chord_diagram` |
| Coordinate quadrilateral completion/recognition | `coordinate_quadrilateral_candidate_diagram`, `coordinate_quadrilateral_panel_grid` |
| Coordinate midpoint, section, and transformation algebra | `coordinate_algebra_diagram` |
| Coordinate locus and shaded-region diagrams | `coordinate_locus_region_diagram` |
| Average-rate and interval property function graphs | `function_graph`, `analytical_function_panel_grid` |

## Remaining Genuine New-Scene Gaps

These are the remaining coverage gaps that would justify new scene ids. They
are listed separately from existing-scene task additions.

### G1. Construction-Mark Equation Diagrams

Status: genuine gap, but risky. The first attempted
`construction_mark_relation_diagram` was rejected and removed.

Current geometry has theorem-specific scenes and some construction marks, but
does not yet have a useful scene where proof marks support nontrivial equation
solving. A future version should avoid pure mark-matching candidate selection
and avoid direct one-step equalities such as `2x+5=17`.

Candidate scene:

- `construction_mark_equation_diagram`

Good task ideas:

- solve a missing value from two or more marked equalities plus a shared
  perimeter, angle-sum, or side-sum constraint,
- solve a variable from congruent angles embedded in a triangle or
  quadrilateral angle-sum relation,
- solve marked equal segment expressions after deriving an intermediate
  expression from a full side or perimeter label.

Implementation constraints:

- Keep marks as semantic metadata, not decorative strokes.
- Evidence should include the target cue plus supporting mark and constraint
  label boxes.
- Do not add a label-only mark matching task unless there is a stronger
  reasoning contract than visual same-mark matching.

## Existing-Scene Extensions

The following are still useful, but they should not be treated as new scene
coverage.

### Function-Graph Query Breadth

Status: partially addressed within existing scenes.

Current graphing/analytical coverage includes crossings, extrema, interval
labels, symmetry labels, intersection-property labels, average rate of change,
monotonic interval selection, and sign interval selection. Additional useful
tasks would extend `function_graph` or `analytical_function_panel_grid`.

Candidate task/query families:

- root/intercept label or count,
- transformed graph match label,
- inverse-style graph relationship label,
- metadata-backed shaded area approximation.

### Worksheet/Exam Rendering Density

Status: cross-cutting rendering gap, not a standalone reasoning scene.

Most geometry scenes are clean technical diagrams. Benchmark diagrams often
look like worksheets: denser labels, extra nonessential marks, problem-number
headers, print-like strokes, local crop variation, and mild scan/noise
artifacts.

Good first targets:

- `circle_theorem_diagram`,
- `parallel_section_length_diagram`,
- `curvilinear_composite_shape_diagram`,
- `circle_square_tangent_packing_diagram`,
- `solid_formula_diagram`.

Implementation constraints:

- Keep evidence metadata projected after any layout or crop transform.
- Do not add visible explanatory text that changes the task.
- Distractor labels must be semantically harmless and recorded in trace
  metadata.
- Calibrate after style changes; existing solve-rate artifacts may not remain
  final if visual difficulty changes.

## Suggested Next Work

Priority order if we continue expanding geometry with genuinely new scenes:

1. `construction_mark_equation_diagram`
   - Worth adding only as a proper multi-step equation scene. Do not use the
     deleted same-mark label task pattern.

Existing-scene follow-ups can proceed independently:

- add root/intercept, transformed-graph, or shaded-area tasks to existing
  function graph scenes,
- add worksheet-style render variants to mature scenes after their task set is
  stable.

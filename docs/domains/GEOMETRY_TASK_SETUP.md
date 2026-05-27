# Geometry Task Setup

Geometry now follows the public taxonomy `domain -> scene_id -> task_id`.
The shared source-style renderers remain grouped by implementation
`task_group`, but default sampling is over public task ids. The exhaustive
active task and scene inventory is generated in
`docs/ACTIVE_TASK_INVENTORY.md`; the table below is a compact contract summary.

## Public Surface
| Task group | Public task count | Primary scene ids | Evidence |
|---|---:|---|---|
| `measurement` | 41 | `graph_paper`, `angle_relations`, `triangle_relations`, `pythagorean_dissection`, `composite_shape`, `sector`, `paper_fold`, `concentric_chord`, `tangent_packing`, `incircle_tangents`, `cone_net`, `solid_revolution`, `solid_formula`, `solid_cross_section`, `cuboid_views`, `area_partition`, `trapezoid_extension` | `point_set`, `bbox_set` |
| `comparison` | 4 | `graph_paper` | `point_set` |
| `counting` | 5 | `graph_paper` | `bbox_set` |
| `coordinate` | 11 | `coordinate_plane`, `coordinate_panels` | `point_set`, `bbox_set` |
| `graphing` | 3 | `function_graph` | `point_set` |
| `similarity` | 1 | `shape_gallery` | `bbox_set` |
| `transformation` | 1 | `shape_gallery` | `point_set` |
| `analytical` | 2 | `function_panels` | `bbox_set` |
| `circle` | 7 | `circle_theorem` | `bbox_set` |

Graph-paper scenes use a bounded framed panel inside the canvas rather than a
full-canvas graph-paper background. The panel bbox is the semantic scene bbox;
graph origin, spacing, plotted objects, labels, and public evidence are
computed after the final panel placement and recorded in `render_spec` as
`layout_placement`, `graph_panel_bbox_px`, `graph_content_bbox_px`,
`graph_origin_px`, `graph_spacing_px`, and `scene_bbox_px`.

The analytical/formula measurement scenes are split by visual grammar.
`angle_relations` covers angle chains and algebraic angle solving.
`triangle_relations` covers angle-bisector and centroid/median
segment relations. `triangle_relations` covers nested triangles
and parallel-section scale relations. `triangle_relations`
covers right-triangle and rectangle-diagonal length formulas without trig.
`composite_shape` covers straight-edged composite area and
perimeter. These tasks use `bbox_set` evidence over the target cue followed by
the supporting labels or constraint marks.

`composite_shape` covers formula-based measurement over
rectangles combined with semicircles, rectangles with quarter-sector cutouts,
and circular sectors. It supports composite area, composite perimeter, missing
side from area, and sector-angle-from-measure tasks; answers are numeric and
rounded to one decimal place using the internal pi value.

`sector` covers standalone circular-sector formula questions.
It supports direct and inverse sector measures, plus sector-angle questions
that may combine an inferred sector angle with complementary, supplementary,
or remaining-circle angle relations. Answers are numeric and rounded to one
decimal place using the internal pi value.

`concentric_chord` covers two concentric circles with a chord of
the outer circle tangent to the inner circle. It supports chord length from the
two radii and inner radius from outer radius plus chord length; answers are
numeric and rounded to one decimal place.

`tangent_packing` covers circles and squares tangent to
square, circular, or rectangular containers. It supports missing length
queries from labeled shaded gap areas plus tangency/packing constraints, and
direct shaded gap-area questions for inscribed or packed shapes; answers are
numeric and rounded to one decimal place.

`incircle_tangents` covers triangle incircle diagrams with
tangent points on all three sides. It supports perimeter from equal tangent
segments and incircle radius from equal tangent segments plus area; answers
are numeric and rounded to one decimal place.

`pythagorean_dissection` covers outer-square dissections with
four congruent right triangles around a central tilted square. It supports
central-square area from visible triangle-leg labels; answers are numeric and
rounded to one decimal place.

`cone_net` covers circular sector nets folded into cones. It
supports cone base radius from sector angle and slant height, plus cone height
after deriving the base radius; answers are numeric and rounded to one decimal
place.

`solid_revolution` covers planar generating shapes rotated 360 degrees
about a marked side or axis to form textbook solids. It supports cylinder
volume from a rectangle with either a direct or derived diameter, cone volume from a right
triangle with a derived radius, double-cone volume from one-cone height and
radius, and frustum volume from a right trapezoid; answers are numeric and
rounded to one decimal place.

`solid_formula` covers direct compound solid diagrams without a
rotation, net, or orthographic projection setup. It supports missing-dimension
queries for stacked cylinder-cone solids, prism-pyramid solids, and
house-shaped compound prisms using visible volume labels plus supporting
dimension labels; answers are numeric and rounded to one decimal place.

`solid_cross_section` covers cones and square pyramids cut by a marked
plane parallel to the base. It supports cross-section area from the full solid
height, distance from apex to slice, and the base radius or side length;
answers are numeric and rounded to one decimal place.

`cuboid_views` covers front, right, and top rectangular
orthographic views of one cuboid. It supports total surface area after
inferring length, width, and height from the three visible view-perimeter
labels; answers are numeric integers.

`area_partition` covers parallelogram area-ratio theorem
diagrams partitioned by both diagonals meeting at the center, with some
variants adding a marked midpoint segment that halves one of the diagonal
quarter regions. It supports total area from a labeled shaded partition
region; answers are numeric integers.

`area_partition` covers triangle area-ratio theorem diagrams
partitioned by a median, a midsegment joining two side midpoints, or by three
medians meeting at a centroid. It supports total area from a labeled shaded
partition region; answers are numeric integers.

`trapezoid_extension` covers a solid trapezoid
completed into a parallelogram by a dashed triangular extension. It supports
extension-length queries from completed-parallelogram area or perimeter, plus
trapezoid-area queries that either use visible bases and height directly or
derive the bottom base from the extension or completed parallelogram area;
answers are numeric integers.

`triangle_relations` covers formula-based right-triangle trigonometry
questions over ramp, flagpole, ladder, and survey-style diagrams. It supports
missing-side and inverse-angle tasks; answers are numeric and rounded to one
decimal place.

`paper_fold` covers a folded paper corner where a visible
crease bisects a marked fold angle between a dashed original edge and a folded
edge. It supports a single angle-value task; answers are numeric and rounded to
one decimal place.

`coordinate_plane` and
`coordinate_panels` cover coordinate-plane quadrilateral
reasoning without measurement formulas. The completion task shows three
unlabeled lattice points plus lettered candidate points and asks which
candidate completes a requested quadrilateral. The panel-match task shows six
mini coordinate panels and asks which panel's four points form the requested
shape. Both tasks keep graph coordinates private and expose pixel-space
`bbox_set` evidence around the selected candidate or panel.

`coordinate_plane` covers coordinate-formula point reasoning without
overlapping polygon area/perimeter, slope-value, or quadrilateral recognition
tasks. It supports midpoint missing-endpoint candidate selection plus
one-third/two-thirds section-point selection, direct and reference-vector
translation, vertical/horizontal reflection, and 90-degree rotation image-point
selection. Answers are option letters, while the exact graph coordinates and
coordinate formula are kept in metadata.

`coordinate_plane` covers shaded coordinate regions defined by
circle, annulus, strip, half-plane, and two-inequality constraints. It supports
single-grid candidate point membership and six-panel region matching from a
visible condition box. Answers are option letters, while the exact region
predicate, panel specs, candidate graph coordinates, and membership flags are
kept in metadata.

`function_graph` now includes count-style graphing queries plus average rate
of change between two marked graph points. The average-rate task uses the two
marked endpoint coordinates as metadata source of truth and returns a numeric
secant slope rounded to one decimal place.

`function_panels` now includes function/one-to-one, domain/range
match, symmetry, monotonic-interval, and sign-interval label tasks. Monotonic
and sign interval tasks keep the mathematical function graph contract separate
from empirical chart trend tasks: the source of truth is the generated relation
metadata, and evidence is the selected panel bbox.

## Wrapper Rule
Each narrowed task emits `query_variant="default"` and records the concrete query
branch in `query_id`. Internal query/scene parameters may still appear in
`query_spec`, `execution_trace`, and `render_spec` for diagnostics and verifier
payloads.

For `circle_theorem`, visible point label `O` is reserved for the
circle center. Non-center point labels are sampled from the remaining capital
letters so generated diagrams do not imply a false center.
The scene covers chord/secant/tangent length theorems, intersecting-chord arc
and angle relations, inscribed-angle relations, and tangent-chord angle
relations.

## Config
Shared knobs stay on internal base ids in `configs/domains/geometry/*.yaml`,
for example `geometry_measurement_value_base` and
`geometry_coordinate_relation_base`. Public task ids should not duplicate those
shared override blocks unless a future task needs a genuinely task-specific
knob.

## Documentation
Every active public geometry task has one `docs/tasks/task_geometry__*.md` file.
Task-review and difficulty-calibration artifacts should be regenerated under
the active public task ids before marking the geometry tasks accepted.

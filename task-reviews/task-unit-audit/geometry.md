# Geometry Task-Unit Audit

Task-unit audit for `domain=geometry` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The geometry domain is mostly healthy, but its consolidation-heavy value tasks need a stricter task-unit check than most other domains.
2. Most geometry tasks still behave like coherent grounding families because they keep one stable visual scaffold and one witness style even when they span many shape families.
3. The clearest task-unit pressure point is `task_geometry_coordinate_relation`, which currently mixes multiple graph-paper grounding families that do not feel uniform enough for equal task-level sampling.
4. Recommended domain outcome:
   - `Keep`: `9`
   - `Split`: `1`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_geometry_analytical_2d_value`
- Outcome: `Keep`
- Why: despite many supported shapes, this remains one coherent annotated-2D-formula family: the solver reads one labeled diagram, uses the visible givens, and solves for one requested analytical quantity.
- Scene variety: high, but still unified by one annotated single-problem scaffold rather than mixed scene grammars.
- Query variety: moderate (`area|length|perimeter|composite_area`) with compatible scene/query pairings.
- Grounding necessity: strong; the model must read the actual diagram annotations from the image.
- Evidence fit: good; `ANNOTATION=VALUE` tokens are consistent across all variants.
- Follow-up: none required now.

### `task_geometry_analytical_3d_value`
- Outcome: `Keep`
- Why: one coherent annotated-solid analytical family over 3D solid diagrams with stable annotation-reading and formula-use behavior.
- Scene variety: moderate across solid types, but still one stable solid-diagram scaffold.
- Query variety: modest but sufficient (`volume|surface_area`)
- Grounding necessity: strong; visible annotations on the solid diagram remain essential.
- Evidence fit: good; symbolic `ANNOTATION=VALUE` `label_set` evidence stays stable across solids and queries.
- Follow-up: none required now.

### `task_geometry_comparison_value`
- Outcome: `Keep`
- Why: one coherent winner-selection family over multiple labeled geometry candidates where the grounding job is always “identify the object with the requested extremum.”
- Scene variety: moderate (`angle|segment|rectangle`) with a stable multi-candidate comparison scaffold.
- Query variety: strong, but still within one winner-picking family.
- Grounding necessity: strong; the model must inspect multiple labeled objects and compare the requested geometric quantity.
- Evidence fit: acceptable; winner-specific geometry evidence changes shape family but preserves the same winner-selection semantics.
- Follow-up: none required now.

### `task_geometry_coordinate_relation`
- Outcome: `Split`
- Why: this task currently mixes several distinct graph-paper grounding families:
  - segment-to-reference relation counting (`parallel_count|perpendicular_count`)
  - point-to-line relation counting (`collinear_count`)
  - point-to-reference-point quadrant counting (`same_quadrant_count`)
  - polygon interior lattice counting (`point_in_shape_count`)
- Scene variety: high, but too mixed for one task unit.
- Query variety: high, but the variants do not share one stable grounding pattern.
- Grounding necessity: strong throughout, but the solver alternates between:
  - reading segment slopes relative to `AB`,
  - testing point-line incidence,
  - testing quadrant membership,
  - counting strict interior lattice points of a polygon.
- Evidence fit: mixed; every variant uses `graph_point_set`, but the witness semantics differ materially across segments, free points, and polygon interiors.
- Follow-up:
  1. Keep `parallel_count|perpendicular_count` together as one segment-relation task.
  2. Keep `collinear_count|same_quadrant_count` together only if we want a point-relation task; otherwise split them further.
  3. Move `point_in_shape_count` into its own polygon-lattice counting task.

### `task_geometry_counting_value`
- Outcome: `Keep`
- Why: one coherent labeled-object classification-counting family, even though the object families vary.
- Scene variety: high but still unified by a stable “count labeled items of type X” job.
- Query variety: high; the counted class changes, but the witness semantics stay stable.
- Grounding necessity: strong; the solver must inspect the shapes/angles themselves rather than only read labels.
- Evidence fit: good; unordered `label_set` evidence is consistent across all counting variants.
- Follow-up: none required now.

### `task_geometry_graphing_count`
- Outcome: `Keep`
- Why: one coherent plotted-function witness-counting family over a single graph-paper plot.
- Scene variety: moderate to high across function families, but still one stable plot-reading scaffold.
- Query variety: strong (`x_intercept_count|horizontal_line_intersection_count|turning_point_count|local_minima_count|local_maxima_count`)
- Grounding necessity: strong; the model must identify visible graph coordinates that satisfy the query.
- Evidence fit: good; unordered witness-point `graph_point_set` remains stable across all variants.
- Follow-up: none required now.

### `task_geometry_measurement_value`
- Outcome: `Keep`
- Why: this is broad, but it still reads as one coherent single-scene measurement family on graph paper rather than a mixture of unrelated grounding jobs.
- Scene variety: high across shape families, but all variants ask the solver to measure one requested quantity from one labeled scene.
- Query variety: strong (`angle|length|area|perimeter|slope`) with compatible scene/query pairings.
- Grounding necessity: strong; the model must inspect coordinates, labeled points, and visible shape structure.
- Evidence fit: acceptable; `graph_point` versus `graph_point_set` varies by measurement type, but both still point at the measured geometric object.
- Follow-up: watch this task if future consolidation adds more scaffolds beyond the current single-scene graph-paper family.

### `task_geometry_similarity_count`
- Outcome: `Keep`
- Why: one coherent reference-vs-candidate polygon matching family.
- Scene variety: moderate (`triangle|quadrilateral`) within one stable reference-plus-candidates scaffold.
- Query variety: modest but sufficient (`congruent_count|similar_count`)
- Grounding necessity: strong; the solver must compare candidate polygons to the `Reference`.
- Evidence fit: good; matching candidate labels are the natural witness.
- Follow-up: none required now.

### `task_geometry_solid_view_count`
- Outcome: `Keep`
- Why: one very clear orthographic-projection counting family with a stable two-panel scaffold.
- Scene variety: narrower than many geometry tasks, but the scaffold is specific and distinctive enough to stand alone.
- Query variety: modest but sufficient (`top|front|right` visible-count variants)
- Grounding necessity: strong; the model must infer the requested projection from the visible cube stack.
- Evidence fit: good; filled query-grid cells are the natural witness.
- Follow-up: none required now.

### `task_geometry_transformation_match`
- Outcome: `Keep`
- Why: one coherent reference-plus-candidates transformation family with a stable cue-driven scaffold.
- Scene variety: moderate (`triangle|quadrilateral`) under one transformation-matching scene grammar.
- Query variety: moderate (`translation_match|reflection_match|rotation_match`)
- Grounding necessity: strong; the solver must apply the shown cue to the visible `Reference`.
- Evidence fit: good; winning polygon vertices are a consistent grounded witness.
- Follow-up: none required now.

## Recommended next action
1. Leave the other geometry tasks unchanged for now.
2. Treat `task_geometry_coordinate_relation` as the first concrete geometry split candidate during benchmark-unit rebalancing.
3. Keep an eye on the broad consolidated value tasks, but only split them if future growth adds genuinely new scene grammars rather than more shapes within the same scaffold.

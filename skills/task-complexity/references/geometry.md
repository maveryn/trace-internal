# Geometry Complexity

## Recommended criteria vocabulary
- `visual_scan`
- `ambiguity`
- `output_burden`

## Domain fallback weights
```yaml
visual_scan: 0.40
ambiguity: 0.35
output_burden: 0.25
```

## Task-group overrides

### `measurement`
```yaml
visual_scan: 0.20
measurement_precision: 0.50
ambiguity: 0.25
output_burden: 0.05
```

Measure:
- closeness to easy canonical values,
- number of visible labels/annotations,
- precision burden (integer vs decimal vs `kπ`),
- evidence cardinality / answer-format burden.

### `comparison`
```yaml
visual_scan: 0.25
comparison_reasoning: 0.35
ambiguity: 0.35
output_burden: 0.05
```

Measure:
- object count,
- winner gap / runner-up closeness,
- direct-vs-derived quantity load,
- graph-point evidence burden (`2` / `3` / `4` points).

### `counting`
```yaml
visual_scan: 0.35
classification_reasoning: 0.35
ambiguity: 0.25
output_burden: 0.05
```

Measure:
- object count,
- class subtlety,
- target-density balance,
- evidence label-set burden,
- boundary cases like overlapping school definitions or near-degenerate shapes.

### `analytical_2d` and `analytical_3d`
```yaml
visual_scan: 0.20
analytical_reasoning: 0.55
ambiguity: 0.20
output_burden: 0.05
```

Measure:
- number of givens/annotations,
- number of inferential steps,
- decomposition complexity,
- answer precision burden,
- measurement-map evidence burden.
- when applicable, additional semantic variant axes such as explicit-vs-derived reasoning mode should raise `analytical_reasoning` / `ambiguity` inside the same family criteria rather than creating a second weighting scheme.

### `transformation`
```yaml
visual_scan: 0.25
transformation_reasoning: 0.40
ambiguity: 0.25
output_burden: 0.10
```

Measure:
- candidate-scan load across the six labeled polygons plus the visible cue,
- cue difficulty (`translation` < `reflection` < `rotation`),
- scene-family bonus when the polygon has more vertices,
- winning-polygon graph-point evidence burden (`3` vs `4` points).

### `similarity`
```yaml
visual_scan: 0.25
similarity_reasoning: 0.35
ambiguity: 0.25
output_burden: 0.15
```

Measure:
- candidate-scan load across the five labeled polygons plus the visible `Reference`,
- predicate difficulty (`congruent_count` < `similar_count`),
- scene-family bonus when the polygon has more vertices,
- target-density balance over the matching subset,
- unordered `label_set` evidence burden (`0..4` labels).

### `coordinate`
```yaml
visual_scan: 0.25
coordinate_reasoning: 0.35
ambiguity: 0.25
output_burden: 0.15
```

Measure:
- visible candidate count across segments, labeled points, or polygon vertices,
- relation difficulty (`same_quadrant_count` < `collinear_count` < `parallel_count` < `point_in_shape_count` < `perpendicular_count`),
- scene-family bonus when the task requires strict interior lattice counting inside a polygon instead of plain quadrant membership,
- witness burden from either matching-segment endpoint coordinates, collinear graph-point sets, same-quadrant graph-point sets, or interior graph-point sets.

### `solid`
```yaml
visual_scan: 0.24
projection_reasoning: 0.46
ambiguity: 0.20
output_burden: 0.10
```

Measure:
- total cube count plus stack height / occlusion load,
- query-view difficulty (`top_view_visible_count` < `front_view_visible_count` ≈ `right_view_visible_count`),
- how much the requested view hides compared with the full cube count,
- prompt-facing `bbox_set` burden from the number of filled query-grid cells.

### `graphing`
```yaml
visual_scan: 0.24
graphing_reasoning: 0.40
ambiguity: 0.22
output_burden: 0.14
```

Measure:
- scene-family difficulty (`quadratic` < `absolute_value` < `piecewise_linear`),
- query difficulty (`x_intercept_count` < `horizontal_line_intersection_count` < `turning_point_count ≈ local_minima_count ≈ local_maxima_count`),
- whether the scene includes one extra dashed horizontal guide line,
- prompt-facing `graph_point_set` burden from the visible witness coordinates.

## Notes
- Domain-level criteria must apply to every geometry task; keep `measurement_precision`, `comparison_reasoning`, `classification_reasoning`, and `analytical_reasoning` at task-group scope rather than forcing them onto unrelated families.
- Geometry usually wants criterion values from explicit `scene_variant` / `query_variant` structure, not from answer magnitude alone.
- Keep raw givens counts, winner gaps, or derivation depth in trace if they help debug the score.
- For analytical geometry, prefer annotation-count, formula-family, and answer-format signals over raw answer magnitude; answer size alone is usually a poor proxy for derivation difficulty.
- In the consolidated geometry surface, use the broad task group to choose the criteria vocabulary, then let `scene_variant` and `query_variant` determine the per-instance component values.
- Geometry transformation tasks should stay evidence-first: if a variant’s cue changes the winning object but not the witness format, keep one family weighting policy and vary only `transformation_reasoning` / `ambiguity` from the resolved cue type.
- Geometry similarity tasks should stay evidence-first too: prefer count/list questions whose witness is the matching candidate-label subset, and keep scale/shape-family difficulty inside `similarity_reasoning` / `ambiguity` rather than splitting the family into separate tiny weight tables.
- Geometry coordinate-relation tasks should keep the evidence contract aligned to the queried object type: segment-count variants should expose coordinate-grounded endpoint evidence for every matching segment, while point-membership/count variants should expose graph-point evidence whenever the visible witness is an unlabeled point set rather than a label identity problem.
- Geometry solid-view tasks should keep difficulty tied to hidden-cube/projection reasoning rather than answer magnitude alone; if the orthographic witness stays the same query-grid `bbox_set`, widen view variants inside the same family instead of splitting one task id per view direction.
- Geometry graphing tasks should keep difficulty tied to plotted-scene/query structure and witness cardinality rather than raw y-values; if the prompt-facing witness stays a coordinate `graph_point_set`, keep intercept / dashed-line / turning-point variants inside one family weighting policy instead of splitting one task id per graph question.

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

## Notes
- Domain-level criteria must apply to every geometry task; keep `measurement_precision`, `comparison_reasoning`, `classification_reasoning`, and `analytical_reasoning` at task-group scope rather than forcing them onto unrelated families.
- Geometry usually wants criterion values from explicit `scene_variant` / `query_variant` structure, not from answer magnitude alone.
- Keep raw givens counts, winner gaps, or derivation depth in trace if they help debug the score.
- For analytical geometry, prefer annotation-count, formula-family, and answer-format signals over raw answer magnitude; answer size alone is usually a poor proxy for derivation difficulty.
- In the consolidated geometry surface, use the broad task group to choose the criteria vocabulary, then let `scene_variant` and `query_variant` determine the per-instance component values.
- Geometry transformation tasks should stay evidence-first: if a variant’s cue changes the winning object but not the witness format, keep one family weighting policy and vary only `transformation_reasoning` / `ambiguity` from the resolved cue type.

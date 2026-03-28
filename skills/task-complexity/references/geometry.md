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
- answer precision burden.

## Notes
- Domain-level criteria must apply to every geometry task; keep `measurement_precision`, `comparison_reasoning`, `classification_reasoning`, and `analytical_reasoning` at task-group scope rather than forcing them onto unrelated families.
- Geometry usually wants criterion values from explicit scene/query structure, not from answer magnitude alone.
- Keep raw givens counts, winner gaps, or derivation depth in trace if they help debug the score.

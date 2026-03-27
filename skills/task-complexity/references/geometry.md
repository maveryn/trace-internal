# Geometry Complexity

## Recommended criteria vocabulary
- `visual_scan`
- `measurement_precision`
- `comparison_reasoning`
- `classification_reasoning`
- `analytical_reasoning`
- `ambiguity`
- `output_burden`

## Domain fallback weights
```yaml
visual_scan: 0.20
measurement_precision: 0.20
comparison_reasoning: 0.15
classification_reasoning: 0.15
analytical_reasoning: 0.20
ambiguity: 0.10
output_burden: 0.00
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
- precision burden (integer vs decimal vs `kπ`).

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
- scene crowding.

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
- Geometry usually wants criterion values from explicit scene/query structure, not from answer magnitude alone.
- Keep raw givens counts, winner gaps, or derivation depth in trace if they help debug the score.

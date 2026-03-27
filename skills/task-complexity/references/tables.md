# Tables Complexity

## Recommended criteria vocabulary
- `row_scan`
- `column_scan`
- `aggregation_reasoning`
- `filter_reasoning`
- `ambiguity`
- `output_burden`

## Domain fallback weights
```yaml
row_scan: 0.30
column_scan: 0.15
aggregation_reasoning: 0.30
filter_reasoning: 0.10
ambiguity: 0.10
output_burden: 0.05
```

## Task-group overrides
### `statistics`
```yaml
row_scan: 0.30
column_scan: 0.15
aggregation_reasoning: 0.35
ambiguity: 0.10
output_burden: 0.10
filter_reasoning: 0.00
```

## Notes
- Tables should usually get harder with more rows, more numeric columns, and more aggregation burden.
- If a future task filters rows/columns before aggregation, shift weight into `filter_reasoning`.
- Keep visible table density and row/column counts as explicit raw diagnostics in trace when they drive the score.

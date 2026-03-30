# Physics Complexity

## Recommended criteria vocabulary
- `visual_scan`
- `force_reasoning`
- `ambiguity`
- `output_burden`

## Domain fallback weights
```yaml
visual_scan: 0.30
diagram_reasoning: 0.45
ambiguity: 0.15
output_burden: 0.10
```

## Task-group overrides

### `mechanics`
```yaml
visual_scan: 0.28
force_reasoning: 0.48
ambiguity: 0.14
output_burden: 0.10
```

Measure:
- arrow/annotation count,
- whether the scene uses a plain free-body box versus extra chrome like a surface or rope,
- query load (`net_*` < `balancing_*`),
- witness-cardinality burden from the queried-axis arrow subset,
- zero-net edge cases that increase ambiguity.

## Notes
- Physics tasks should keep difficulty tied to the visible diagram structure plus the arithmetic/readout burden, not raw answer magnitude alone.
- Early physics tasks usually want one family weighting policy per task group, with `scene_variant` and `query_variant` modulating the per-instance criterion values.

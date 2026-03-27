# Charts Complexity

## Recommended criteria vocabulary
- `visual_scan`
- `aggregation_reasoning`
- `comparison_reasoning`
- `distribution_reasoning`
- `trend_reasoning`
- `composition_reasoning`
- `scene_variant_load`
- `ambiguity`
- `output_burden`

## Domain fallback weights
```yaml
visual_scan: 0.20
aggregation_reasoning: 0.20
comparison_reasoning: 0.15
distribution_reasoning: 0.10
trend_reasoning: 0.10
composition_reasoning: 0.10
scene_variant_load: 0.05
ambiguity: 0.10
output_burden: 0.00
```

## Task-group overrides
- `statistics`
  - emphasize `aggregation_reasoning`, `ambiguity`
- `counting`
  - emphasize `visual_scan`, `aggregation_reasoning`, `scene_variant_load`
- `readout`
  - emphasize `aggregation_reasoning`, `output_burden`
- `multiseries`
  - emphasize `comparison_reasoning`, `visual_scan`
- `distribution`
  - emphasize `distribution_reasoning`, `ambiguity`
- `trend`
  - emphasize `trend_reasoning`, `visual_scan`
- `composition`
  - emphasize `composition_reasoning`, `scene_variant_load`

## Notes
- Use chart-native structure in the score: mark count, series count, bin count, category count, scene variant density, and evidence ordering burden.
- Chart tasks often get harder because of representation load (`scene_variant`) and aggregation semantics, not because the final numeric answer is larger.

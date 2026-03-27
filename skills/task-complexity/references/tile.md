# Tile Complexity

## Recommended criteria vocabulary
- `board_scan`
- `search_depth`
- `state_tracking`
- `pattern_reasoning`
- `spatial_reasoning`
- `ambiguity`
- `output_burden`

## Domain fallback weights
```yaml
board_scan: 0.25
search_depth: 0.20
state_tracking: 0.20
pattern_reasoning: 0.15
spatial_reasoning: 0.10
ambiguity: 0.10
output_burden: 0.00
```

## Task-group overrides
- `count`
  - emphasize `board_scan`, `pattern_reasoning`, `ambiguity`
- `path`
  - emphasize `search_depth`, `state_tracking`
- `reachability`
  - emphasize `board_scan`, `search_depth`
- `relation`
  - emphasize `spatial_reasoning`, `ambiguity`
- `symmetry`
  - emphasize `pattern_reasoning`, `board_scan`
- `transition`
  - emphasize `state_tracking`, `search_depth`

## Notes
- Tile complexity should usually come from board size, obstacle density, path depth, and witness uniqueness.
- Avoid using answer size alone as a difficulty proxy; many tile tasks are harder because of search and state management, not because the final integer is large.

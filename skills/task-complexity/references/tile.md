# Tile Complexity

## Recommended criteria vocabulary
- `visual_scan`
- `reasoning_load`

## Domain fallback weights
```yaml
visual_scan: 0.50
reasoning_load: 0.50
```

## Scope notes
- Tile currently uses one stable board presentation, so do not introduce `scene_variant_load` unless the domain gains real scene-presentation variation later.
- Keep the tile-domain vocabulary broad. Every migrated tile task should be able to score the same criteria.
- Let each task decide how to normalize its own raw knobs into these criteria.
- Use task-group or task-level weight overrides only when a tile family really shifts the relative importance of scan versus reasoning.

## Notes
- Tile complexity should usually come from board size, obstacle density, active-cell count, path depth, component fragmentation, or other board-content semantics.
- `visual_scan` should usually reflect board area plus how many active or relevant cells must be inspected.
- `reasoning_load` should capture the task-specific semantic work: counting grouped components, tracing reachability, following transitions, or comparing structured regions.
- Avoid using answer size alone as a difficulty proxy; many tile tasks are harder because of search or grouping structure, not because the final integer is large.

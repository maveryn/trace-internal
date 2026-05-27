# Three-D Complexity

Use this when scoring task complexity for `domain=three_d`.

## Domain Criteria

- `visual_scan`: number and spread of projected objects or candidates that must be inspected.
- `spatial_reasoning`: amount of 3D relation, distance, height, or occlusion reasoning required.
- `projection_ambiguity`: camera angle, depth compression, overlap, or near-tie projection difficulty.
- `clutter`: projected bbox density, label/object crowding, and background context.

## Default Weight Intent

- `visual_scan`: 0.25
- `spatial_reasoning`: 0.40
- `projection_ambiguity`: 0.25
- `clutter`: 0.10

## Notes

- Complexity must be computed from finalized 3D metadata and projection records, not pixels.
- Good knobs include object count, candidate count, camera yaw/pitch, depth separation, occlusion, bbox overlap, and distance/height margins.
- Keep style, room, and surface variation non-semantic unless a task explicitly reasons over them.

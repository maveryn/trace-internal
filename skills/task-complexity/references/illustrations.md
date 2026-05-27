# Illustrations Complexity

Use this when scoring task complexity for `domain=illustrations`.

## Domain Criteria

- `visual_scan`: number and spread of visible objects or object parts that must be inspected.
- `semantic_match`: difficulty of matching the requested object, part, or attribute to rendered metadata.
- `ambiguity`: target/distractor similarity, partial visibility, occlusion, or relation ambiguity.
- `clutter`: scene density, overlaps, decorative context, and label/part crowding.

## Default Weight Intent

- `visual_scan`: 0.35
- `semantic_match`: 0.30
- `ambiguity`: 0.20
- `clutter`: 0.15

## Notes

- Complexity must come from finalized synthetic scene metadata, not natural-world assumptions.
- Good knobs include object count, part count, target/distractor similarity, occlusion, overlap, and relation or zone ambiguity.
- Do not score invisible canonical facts, such as how many parts a real-world object usually has, unless the rendered trace exposes those parts.

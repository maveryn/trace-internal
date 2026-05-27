# Games Complexity

Use this when scoring task complexity for `domain=games`.

## Domain Criteria

- `visual_scan`: amount of visible board/card/piece state that must be inspected.
- `rules_reasoning`: number and specificity of visible game rules or legal-move constraints.
- `ambiguity`: closeness of distractors, near-miss moves, or candidate outcomes.
- `clutter`: density of pieces, cards, labels, or candidate panels.

## Default Weight Intent

- `visual_scan`: 0.30
- `rules_reasoning`: 0.40
- `ambiguity`: 0.20
- `clutter`: 0.10

## Notes

- Keep complexity within-task normalized.
- Good knobs include board size, candidate count, legal-move branching, route depth, row/column span, and distractor similarity.
- Do not use raw answer magnitude as complexity unless the task's reasoning process genuinely scales with it.
- Keep game rules visible or explicit; hidden convention knowledge should not be a complexity source.

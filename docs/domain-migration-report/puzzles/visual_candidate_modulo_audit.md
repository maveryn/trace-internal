# Visual Candidate-Set Modulo Audit

This report audits modulo use around visual attributes such as colors, styles, labels, shapes, themes, symbols, and option layouts. Random candidate-set selection should use RNG sampling from an explicit support or range. Modulo is acceptable only for deterministic assignment from an already-selected list or for intentional repeat cycling.

## Summary

- Total visual modulo sites: 15
- Random candidate selection needs refactor: 0
- Sampling-time assignment needs review: 0
- Needs manual review: 0
- Likely safe deterministic assignment: 15

## Random Candidate Selection Needs Refactor

None found.

## Sampling-Time Assignment Needs Review

None found.

## Needs Manual Review

None found.

## Likely Safe Deterministic Assignment

| File | Line | Reason | Snippet |
| --- | ---: | --- | --- |
| `trace/core/review_overlays.py` | 282 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 290 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 300 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 309 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 329 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 336 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 345 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 350 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 353 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/tasks/puzzles/cube_net/shared/rendering.py` | 52 | render/review code cycles through an already-selected palette or repeated style list | `face: tuple(colors[index % len(colors)])` |
| `trace/tasks/puzzles/cube_net/shared/rendering.py` | 109 | render/review code cycles through an already-selected palette or repeated style list | `return str(order[(order.index(str(side)) + turns) % len(order)])` |
| `trace/tasks/puzzles/cyclic_order/shared/rendering.py` | 346 | render/review code cycles through an already-selected palette or repeated style list | `next_center = centers[int(gap_index) % len(centers)]` |
| `trace/tasks/puzzles/matchstick/shared/rendering.py` | 303 | render/review code cycles through an already-selected palette or repeated style list | `index = sum(ord(ch) for ch in str(stick_id)) % len(palette)` |
| `trace/tasks/puzzles/maze/shared/rendering.py` | 273 | render/review code cycles through an already-selected palette or repeated style list | `marker_fill = tuple(render_params.exit_palette[int(index) % len(render_params.exit_palette)])` |
| `trace/tasks/puzzles/star_battle/shared/rendering.py` | 311 | render/review code cycles through an already-selected palette or repeated style list | `fill = palette[region_index % len(palette)]` |

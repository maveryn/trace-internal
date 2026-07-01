# Visual Candidate-Set Modulo Audit

This report audits modulo use around visual attributes such as colors, styles, labels, shapes, themes, symbols, and option layouts. Random candidate-set selection should use RNG sampling from an explicit support or range. Modulo is acceptable only for deterministic assignment from an already-selected list or for intentional repeat cycling.

## Summary

- Total visual modulo sites: 18
- Random candidate selection needs refactor: 0
- Sampling-time assignment needs review: 0
- Needs manual review: 0
- Likely safe deterministic assignment: 18

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
| `trace/tasks/illustrations/isometric_harbor/shared/rendering.py` | 488 | render/review code cycles through an already-selected palette or repeated style list | `fill=cargo_colors[index % len(cargo_colors)],` |
| `trace/tasks/illustrations/isometric_harbor/shared/rendering.py` | 910 | render/review code cycles through an already-selected palette or repeated style list | `hull_fill, trim = BOAT_COLOR_PALETTES[int(index) % len(BOAT_COLOR_PALETTES)]` |
| `trace/tasks/illustrations/isometric_harbor/shared/rendering.py` | 1063 | deterministic boat-rank palette assignment | `hull_fill, trim = BOAT_COLOR_PALETTES[int(rank) % len(BOAT_COLOR_PALETTES)]` |
| `trace/tasks/illustrations/pixel_village/shared/rendering.py` | 355 | deterministic pixel-village sprite texture cycle | `draw.rectangle((px, py, px + 15, py + 15), fill=colors[variant % len(colors)])` |
| `trace/tasks/illustrations/pixel_village/shared/rendering.py` | 370 | deterministic pixel-village sprite texture cycle | `draw.rectangle((px, py, px + 15, py + 15), fill=colors[variant % len(colors)])` |
| `trace/tasks/illustrations/pixel_village/shared/rendering.py` | 384 | deterministic pixel-village sprite texture cycle | `draw.rectangle((px, py, px + 15, py + 15), fill=colors[variant % len(colors)])` |
| `trace/tasks/illustrations/shared/object_rendering.py` | 732 | deterministic produce-bin palette cycle | `color = palette[index % len(palette)]` |
| `trace/tasks/illustrations/shared/pixel_farm_rendering.py` | 209 | deterministic pixel-farm texture cycle | `draw.rectangle((px, py, px + 15, py + 15), fill=colors[(x * 5 + y * 3) % len(colors)])` |
| `trace/tasks/illustrations/shared/pixel_world_objects.py` | 533 | deterministic pixel-world object palette cycle | `color = palette[index % len(palette)]` |

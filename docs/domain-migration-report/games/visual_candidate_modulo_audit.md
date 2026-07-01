# Visual Candidate-Set Modulo Audit

This report audits modulo use around visual attributes such as colors, styles, labels, shapes, themes, symbols, and option layouts. Random candidate-set selection should use RNG sampling from an explicit support or range. Modulo is acceptable only for deterministic assignment from an already-selected list or for intentional repeat cycling.

## Summary

- Total visual modulo sites: 24
- Random candidate selection needs refactor: 0
- Sampling-time assignment needs review: 0
- Needs manual review: 0
- Likely safe deterministic assignment: 24

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
| `trace/tasks/games/bowling/shared/rendering.py` | 505 | render/review code cycles through an already-selected palette or repeated style list | `color = path_palette_rgb[int(option.color_index) % len(path_palette_rgb)]` |
| `trace/tasks/games/brick_breaker/shared/rendering.py` | 269 | render/review code cycles through an already-selected palette or repeated style list | `fill = theme.brick_palette_rgb[int(brick.color_index) % len(theme.brick_palette_rgb)]` |
| `trace/tasks/games/crossing/shared/rendering.py` | 438 | render/review code cycles through an already-selected palette or repeated style list | `color = theme.marked_path_rgb if route.label == marked_route_label else theme.path_rgbs[int(route.color_index) % len(theme.path_rgbs)]` |
| `trace/tasks/games/crossing/shared/rendering.py` | 541 | render/review code cycles through an already-selected palette or repeated style list | `fill = theme.vehicle_rgbs[int(vehicle.color_index) % len(theme.vehicle_rgbs)]` |
| `trace/tasks/games/lane_runner/shared/rendering.py` | 307 | render/review code cycles through an already-selected palette or repeated style list | `return palette[int(label_index) % len(palette)]` |
| `trace/tasks/games/mancala_pit_board/shared/rendering.py` | 372 | render/review code cycles through an already-selected palette or repeated style list | `seed_rgb = tuple(theme.seed_rgbs[(pit_index + seed_index) % len(theme.seed_rgbs)])` |
| `trace/tasks/games/minigolf/shared/rendering.py` | 276 | render/review code cycles through an already-selected palette or repeated style list | `fill = theme.obstacle_palette_rgb[int(obstacle.color_index) % len(theme.obstacle_palette_rgb)]` |
| `trace/tasks/games/minigolf/shared/rendering.py` | 472 | render/review code cycles through an already-selected palette or repeated style list | `color = path_palette_rgb[int(path.color_index) % len(path_palette_rgb)]` |
| `trace/tasks/games/pinball_table/shared/rendering.py` | 536 | render/review code cycles through an already-selected palette or repeated style list | `fill = theme.object_palette_rgb[int(obj.color_index) % len(theme.object_palette_rgb)]` |
| `trace/tasks/games/platformer/shared/rendering.py` | 427 | render/review code cycles through an already-selected palette or repeated style list | `fill = theme.platform_palette_rgb[int(platform.color_index) % len(theme.platform_palette_rgb)]` |
| `trace/tasks/games/platformer/shared/rendering.py` | 465 | render/review code cycles through an already-selected palette or repeated style list | `fill = theme.hazard_palette_rgb[int(hazard.color_index) % len(theme.hazard_palette_rgb)]` |
| `trace/tasks/games/platformer/shared/rendering.py` | 507 | render/review code cycles through an already-selected palette or repeated style list | `fill = theme.coin_palette_rgb[int(collectible.color_index) % len(theme.coin_palette_rgb)]` |
| `trace/tasks/games/racing_track/shared/rendering.py` | 472 | render/review code cycles through an already-selected palette or repeated style list | `color = theme.car_palette_rgb[int(index) % len(theme.car_palette_rgb)]` |
| `trace/tasks/games/tetris/shared/rendering.py` | 74 | render/review code cycles through an already-selected palette or repeated style list | `return tuple(int(v) for v in state_colors[index % len(state_colors)])` |
| `trace/tasks/games/tower_defense/shared/rendering.py` | 520 | render/review code cycles through an already-selected palette or repeated style list | `color = tuple(int(value) for value in range_palette[int(index) % len(range_palette)])` |

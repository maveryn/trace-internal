# Semantic Sampling Modulo Audit: First Pass

This report flags source patterns where modulo/index cycling may be standing in for semantic random sampling. Task random sampling should draw from an explicit support or bounded range with uniform or weighted probabilities. It is a static first pass; each refactor site still needs source-level confirmation before editing.

## Summary

- Raw line findings: 31
- Grouped selection sites: 31
- Needs refactor: 0
- Needs manual review: 0
- Review harness stratification / round-robin: 1
- Allowed deterministic visual/layout enumeration: 30

## Needs Refactor

None found.

## Needs Manual Review

None found.

## Review Harness Stratification / Round-Robin

| File | Lines | Kind | Raw Lines | Reason | Snippets |
| --- | ---: | --- | ---: | --- | --- |
| `trace/core/task_review_sampling.py` | 188 | modulo_index | 1 | allowed only because this is explicit review/dataset coverage, not task randomness | `query_id_value = str(pending_query_ids[int(query_id_index) % len(pending_query_ids)])` |

## Allowed Deterministic Visual/Layout Enumeration

| File | Lines | Kind | Raw Lines | Reason | Snippets |
| --- | ---: | --- | ---: | --- | --- |
| `trace/core/review_overlays.py` | 282 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 290 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 300 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 309 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 329 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 336 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 345 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 350 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 353 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/tasks/games/bowling/shared/rendering.py` | 505 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = path_palette_rgb[int(option.color_index) % len(path_palette_rgb)]` |
| `trace/tasks/games/brick_breaker/shared/rendering.py` | 269 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = theme.brick_palette_rgb[int(brick.color_index) % len(theme.brick_palette_rgb)]` |
| `trace/tasks/games/crossing/shared/rendering.py` | 438 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = theme.marked_path_rgb if route.label == marked_route_label else theme.path_rgbs[int(route.color_index) % len(theme.path_rgbs)]` |
| `trace/tasks/games/crossing/shared/rendering.py` | 541 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = theme.vehicle_rgbs[int(vehicle.color_index) % len(theme.vehicle_rgbs)]` |
| `trace/tasks/games/lane_runner/shared/rendering.py` | 307 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `return palette[int(label_index) % len(palette)]` |
| `trace/tasks/games/ludo_board/capture_roll_option_label.py` | 53 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `target_index = (mover_index + distance) % len(MAIN_PATH)` |
| `trace/tasks/games/mancala_pit_board/shared/rendering.py` | 372 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `seed_rgb = tuple(theme.seed_rgbs[(pit_index + seed_index) % len(theme.seed_rgbs)])` |
| `trace/tasks/games/mancala_pit_board/shared/rules.py` | 13 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `return str(LABELS[int(index) % len(LABELS)])` |
| `trace/tasks/games/mancala_pit_board/sowing_landing_option_label.py` | 44 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `source_index = (int(target_index) - int(source_seed_count)) % len(LABELS)` |
| `trace/tasks/games/minigolf/shared/rendering.py` | 276 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = theme.obstacle_palette_rgb[int(obstacle.color_index) % len(theme.obstacle_palette_rgb)]` |
| `trace/tasks/games/minigolf/shared/rendering.py` | 472 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = path_palette_rgb[int(path.color_index) % len(path_palette_rgb)]` |
| `trace/tasks/games/pinball_table/shared/rendering.py` | 536 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = theme.object_palette_rgb[int(obj.color_index) % len(theme.object_palette_rgb)]` |
| `trace/tasks/games/platformer/shared/rendering.py` | 427 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = theme.platform_palette_rgb[int(platform.color_index) % len(theme.platform_palette_rgb)]` |
| `trace/tasks/games/platformer/shared/rendering.py` | 465 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = theme.hazard_palette_rgb[int(hazard.color_index) % len(theme.hazard_palette_rgb)]` |
| `trace/tasks/games/platformer/shared/rendering.py` | 507 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = theme.coin_palette_rgb[int(collectible.color_index) % len(theme.coin_palette_rgb)]` |
| `trace/tasks/games/racing_track/shared/rendering.py` | 472 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = theme.car_palette_rgb[int(index) % len(theme.car_palette_rgb)]` |
| `trace/tasks/games/radial_hunt_board/shared/rules.py` | 74 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `seen.add(edge(coord, line[(index + 1) % len(line)]))` |
| `trace/tasks/games/radial_hunt_board/shared/rules.py` | 111 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `captured = line[(index + direction) % len(line)]` |
| `trace/tasks/games/radial_hunt_board/shared/rules.py` | 112 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `destination = line[(index + (2 * direction)) % len(line)]` |
| `trace/tasks/games/tetris/shared/rendering.py` | 74 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `return tuple(int(v) for v in state_colors[index % len(state_colors)])` |
| `trace/tasks/games/tower_defense/shared/rendering.py` | 520 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = tuple(int(value) for value in range_palette[int(index) % len(range_palette)])` |

# Semantic Sampling Modulo Audit: First Pass

This report flags source patterns where modulo/index cycling may be standing in for semantic random sampling. Task random sampling should draw from an explicit support or bounded range with uniform or weighted probabilities. It is a static first pass; each refactor site still needs source-level confirmation before editing.

## Summary

- Raw line findings: 16
- Grouped selection sites: 16
- Needs refactor: 0
- Needs manual review: 0
- Review harness stratification / round-robin: 1
- Allowed deterministic visual/layout enumeration: 15

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
| `trace/tasks/puzzles/cube_net/shared/rendering.py` | 52 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `face: tuple(colors[index % len(colors)])` |
| `trace/tasks/puzzles/cube_net/shared/rendering.py` | 109 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `return str(order[(order.index(str(side)) + turns) % len(order)])` |
| `trace/tasks/puzzles/cyclic_order/shared/rendering.py` | 346 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `next_center = centers[int(gap_index) % len(centers)]` |
| `trace/tasks/puzzles/matchstick/shared/rendering.py` | 303 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `index = sum(ord(ch) for ch in str(stick_id)) % len(palette)` |
| `trace/tasks/puzzles/maze/shared/rendering.py` | 273 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `marker_fill = tuple(render_params.exit_palette[int(index) % len(render_params.exit_palette)])` |
| `trace/tasks/puzzles/star_battle/shared/rendering.py` | 311 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = palette[region_index % len(palette)]` |

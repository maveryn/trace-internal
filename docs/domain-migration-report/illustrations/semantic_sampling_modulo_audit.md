# Semantic Sampling Modulo Audit: First Pass

This report flags source patterns where modulo/index cycling may be standing in for semantic random sampling. Task random sampling should draw from an explicit support or bounded range with uniform or weighted probabilities. It is a static first pass; each refactor site still needs source-level confirmation before editing.

## Summary

- Raw line findings: 21
- Grouped selection sites: 21
- Needs refactor: 0
- Needs manual review: 0
- Review harness stratification / round-robin: 1
- Allowed deterministic visual/layout enumeration: 20

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
| `trace/tasks/illustrations/isometric_harbor/shared/rendering.py` | 488 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill=cargo_colors[index % len(cargo_colors)],` |
| `trace/tasks/illustrations/isometric_harbor/shared/rendering.py` | 910 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `hull_fill, trim = BOAT_COLOR_PALETTES[int(index) % len(BOAT_COLOR_PALETTES)]` |
| `trace/tasks/illustrations/isometric_harbor/shared/rendering.py` | 1063 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `hull_fill, trim = BOAT_COLOR_PALETTES[int(rank) % len(BOAT_COLOR_PALETTES)]` |
| `trace/tasks/illustrations/isometric_quarry/shared/rendering.py` | 821 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `subtype = str(available_subtypes[(quarry_object_index + int(tile.col) + int(tile.row)) % len(available_subtypes)])` |
| `trace/tasks/illustrations/library/shared/rendering.py` | 268 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `groups[index % len(groups)].append(spec)` |
| `trace/tasks/illustrations/pixel_village/shared/rendering.py` | 355 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `draw.rectangle((px, py, px + 15, py + 15), fill=colors[variant % len(colors)])` |
| `trace/tasks/illustrations/pixel_village/shared/rendering.py` | 370 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `draw.rectangle((px, py, px + 15, py + 15), fill=colors[variant % len(colors)])` |
| `trace/tasks/illustrations/pixel_village/shared/rendering.py` | 384 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `draw.rectangle((px, py, px + 15, py + 15), fill=colors[variant % len(colors)])` |
| `trace/tasks/illustrations/shared/object_rendering.py` | 732 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = palette[index % len(palette)]` |
| `trace/tasks/illustrations/shared/pixel_farm_rendering.py` | 209 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `draw.rectangle((px, py, px + 15, py + 15), fill=colors[(x * 5 + y * 3) % len(colors)])` |
| `trace/tasks/illustrations/shared/pixel_world_objects.py` | 533 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = palette[index % len(palette)]` |

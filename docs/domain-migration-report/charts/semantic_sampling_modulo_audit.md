# Semantic Sampling Modulo Audit: First Pass

This report flags source patterns where modulo/index cycling may be standing in for semantic random sampling. Task random sampling should draw from an explicit support or bounded range with uniform or weighted probabilities. It is a static first pass; each refactor site still needs source-level confirmation before editing.

## Summary

- Raw line findings: 48
- Grouped selection sites: 48
- Needs refactor: 0
- Needs manual review: 0
- Review harness stratification / round-robin: 1
- Allowed deterministic visual/layout enumeration: 47

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
| `trace/tasks/charts/area/shared/rendering.py` | 48 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `_as_rgb(item, DEFAULT_PALETTE[index % len(DEFAULT_PALETTE)])` |
| `trace/tasks/charts/area/shared/rendering.py` | 238 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `_as_rgb(item, DEFAULT_PALETTE[index % len(DEFAULT_PALETTE)])` |
| `trace/tasks/charts/area/shared/rendering.py` | 341 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill_rgb = tuple(int(channel) for channel in palette[int(series_index) % len(palette)])` |
| `trace/tasks/charts/area/shared/rendering.py` | 529 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill_rgb = tuple(int(channel) for channel in palette[int(series_index) % len(palette)])` |
| `trace/tasks/charts/bar_3d/shared/sampling.py` | 32 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `palette = [_as_rgb(item, _DEFAULT_PALETTE[index % len(_DEFAULT_PALETTE)]) for index, item in enumerate(raw_palette)]` |
| `trace/tasks/charts/bar_3d/shared/sampling.py` | 718 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=tuple(int(channel) for channel in palette[int(series_index) % len(palette)]),` |
| `trace/tasks/charts/composition_panels/shared/rendering.py` | 164 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `str(label): SEGMENT_COLORS[index % len(SEGMENT_COLORS)]` |
| `trace/tasks/charts/contour_density/shared/sampling.py` | 199 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/curve_panels/shared/rendering.py` | 188 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = tuple(colors[int(index) % len(colors)])` |
| `trace/tasks/charts/curve_panels/shared/sampling.py` | 383 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/density_curve/shared/sampling.py` | 234 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=tuple(int(channel) for channel in palette[int(index) % len(palette)]),` |
| `trace/tasks/charts/heatmap/shared/rendering.py` | 369 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = palette[int(cell["heat_level"]) % len(palette)]` |
| `trace/tasks/charts/part_whole/shared/sampling.py` | 203 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `(int(start_index) + (int(step) * int(offset))) % len(categories)` |
| `trace/tasks/charts/part_whole/shared/sampling.py` | 377 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `target_index = (int(source_index) + int(step)) % len(categories)` |
| `trace/tasks/charts/radar/shared/sampling.py` | 350 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=tuple(colors[index % len(colors)]),` |
| `trace/tasks/charts/radial_sankey/shared/rendering.py` | 372 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = palette[int(index) % len(palette)]` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 415 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = tuple(int(channel) for channel in palette[int(index) % len(palette)])` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 454 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = tuple(int(channel) for channel in palette[int(index) % len(palette)])` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 749 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = tuple(int(channel) for channel in palette[int(region_spec["bin_index"]) % len(palette)])` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 964 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = tuple(int(channel) for channel in palette[int(bin_index) % len(palette)])` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 972 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = neutral_fills[int(_region_sort_key(region_id)[1]) % len(neutral_fills)] if isinstance(_region_sort_key(region_id)[1], int) else neutral_fills[0]` |
| `trace/tasks/charts/sankey/shared/rendering.py` | 423 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = FLOW_PALETTE_RGB[int(index) % len(FLOW_PALETTE_RGB)]` |
| `trace/tasks/charts/scatter_cluster/shared/data.py` | 125 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/scatter_cluster/shared/data.py` | 415 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/scatter_readout/shared/rendering.py` | 328 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `offset = label_offsets[int(series_index) % len(label_offsets)]` |
| `trace/tasks/charts/shared/cartesian/lines.py` | 97 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `draw_len, gap_len = pattern[int(pattern_index) % len(pattern)]` |
| `trace/tasks/charts/shared/chart_scene_primitives.py` | 448 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `palette_color = muted_palette[(int(index) + int(offset)) % len(muted_palette)]` |
| `trace/tasks/charts/size_encoding/shared/sampling.py` | 170 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `assigned_categories = [panel_categories[index % len(panel_categories)] for index in range(count)]` |
| `trace/tasks/charts/size_encoding/shared/sampling.py` | 356 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `runner_index = int((winner_index + runner_offset) % len(dataset.items))` |
| `trace/tasks/charts/style_legend/shared/sampling.py` | 101 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `return tuple(palette[index % len(palette)] for index in range(int(count)))` |
| `trace/tasks/charts/style_legend/shared/sampling.py` | 103 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `return tuple(palette[index % len(palette)] for index in range(int(count)))` |
| `trace/tasks/charts/style_legend/shared/sampling.py` | 126 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/surface_3d/panel_variation_label.py` | 89 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=PALETTE[int(index) % len(PALETTE)],` |
| `trace/tasks/charts/surface_3d/reference_nearest_label.py` | 72 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=PALETTE[int(index) % len(PALETTE)],` |
| `trace/tasks/charts/surface_3d/series_trend_label.py` | 93 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color_rgb=PALETTE[int(series_index) % len(PALETTE)],` |
| `trace/tasks/charts/table/shared/rendering.py` | 621 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `raw = options[_selection_index(str(key)) % len(options)]` |
| `trace/tasks/charts/table/shared/rendering.py` | 633 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `value = str(options[_selection_index(str(key)) % len(options)])` |
| `trace/tasks/charts/treemap/repeated_leaf_aggregate_value.py` | 67 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `if total % len(matching) != 0:` |

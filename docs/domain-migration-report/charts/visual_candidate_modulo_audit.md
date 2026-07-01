# Visual Candidate-Set Modulo Audit

This report audits modulo use around visual attributes such as colors, styles, labels, shapes, themes, symbols, and option layouts. Random candidate-set selection should use RNG sampling from an explicit support or range. Modulo is acceptable only for deterministic assignment from an already-selected list or for intentional repeat cycling.

## Summary

- Total visual modulo sites: 43
- Random candidate selection needs refactor: 0
- Sampling-time assignment needs review: 0
- Needs manual review: 0
- Likely safe deterministic assignment: 43

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
| `trace/tasks/charts/area/shared/rendering.py` | 48 | render/review code cycles through an already-selected palette or repeated style list | `_as_rgb(item, DEFAULT_PALETTE[index % len(DEFAULT_PALETTE)])` |
| `trace/tasks/charts/area/shared/rendering.py` | 238 | render/review code cycles through an already-selected palette or repeated style list | `_as_rgb(item, DEFAULT_PALETTE[index % len(DEFAULT_PALETTE)])` |
| `trace/tasks/charts/area/shared/rendering.py` | 341 | render/review code cycles through an already-selected palette or repeated style list | `fill_rgb = tuple(int(channel) for channel in palette[int(series_index) % len(palette)])` |
| `trace/tasks/charts/area/shared/rendering.py` | 529 | render/review code cycles through an already-selected palette or repeated style list | `fill_rgb = tuple(int(channel) for channel in palette[int(series_index) % len(palette)])` |
| `trace/tasks/charts/bar_3d/shared/sampling.py` | 32 | default palette normalization before seeded palette shuffle | `palette = [_as_rgb(item, _DEFAULT_PALETTE[index % len(_DEFAULT_PALETTE)]) for index, item in enumerate(raw_palette)]` |
| `trace/tasks/charts/bar_3d/shared/sampling.py` | 718 | deterministic per-series palette assignment from sampled palette | `color_rgb=tuple(int(channel) for channel in palette[int(series_index) % len(palette)]),` |
| `trace/tasks/charts/composition_panels/shared/rendering.py` | 164 | render/review code cycles through an already-selected palette or repeated style list | `str(label): SEGMENT_COLORS[index % len(SEGMENT_COLORS)]` |
| `trace/tasks/charts/contour_density/shared/sampling.py` | 199 | deterministic region-color assignment from sampled palette | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/curve_panels/shared/rendering.py` | 188 | render/review code cycles through an already-selected palette or repeated style list | `color = tuple(colors[int(index) % len(colors)])` |
| `trace/tasks/charts/curve_panels/shared/sampling.py` | 383 | deterministic curve-color assignment from sampled palette | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/density_curve/shared/sampling.py` | 234 | deterministic density-curve color assignment from sampled palette | `color_rgb=tuple(int(channel) for channel in palette[int(index) % len(palette)]),` |
| `trace/tasks/charts/heatmap/shared/rendering.py` | 369 | render/review code cycles through an already-selected palette or repeated style list | `color = palette[int(cell["heat_level"]) % len(palette)]` |
| `trace/tasks/charts/radar/shared/sampling.py` | 350 | deterministic panel-profile color assignment from sampled palette | `color_rgb=tuple(colors[index % len(colors)]),` |
| `trace/tasks/charts/radial_sankey/shared/rendering.py` | 372 | render/review code cycles through an already-selected palette or repeated style list | `color = palette[int(index) % len(palette)]` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 415 | render/review code cycles through an already-selected palette or repeated style list | `fill = tuple(int(channel) for channel in palette[int(index) % len(palette)])` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 454 | render/review code cycles through an already-selected palette or repeated style list | `fill = tuple(int(channel) for channel in palette[int(index) % len(palette)])` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 749 | render/review code cycles through an already-selected palette or repeated style list | `fill = tuple(int(channel) for channel in palette[int(region_spec["bin_index"]) % len(palette)])` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 964 | render/review code cycles through an already-selected palette or repeated style list | `fill = tuple(int(channel) for channel in palette[int(bin_index) % len(palette)])` |
| `trace/tasks/charts/region_map/shared/rendering.py` | 972 | deterministic neutral-region fill cycling from render palette | `fill = neutral_fills[int(_region_sort_key(region_id)[1]) % len(neutral_fills)] if isinstance(_region_sort_key(region_id)[1], int) else neutral_fills[0]` |
| `trace/tasks/charts/sankey/shared/rendering.py` | 423 | render/review code cycles through an already-selected palette or repeated style list | `color = FLOW_PALETTE_RGB[int(index) % len(FLOW_PALETTE_RGB)]` |
| `trace/tasks/charts/scatter_cluster/shared/data.py` | 125 | deterministic cluster-color assignment from sampled palette | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/scatter_cluster/shared/data.py` | 415 | deterministic cluster-color assignment from sampled palette | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/scatter_readout/shared/rendering.py` | 328 | render/review code cycles through an already-selected palette or repeated style list | `offset = label_offsets[int(series_index) % len(label_offsets)]` |
| `trace/tasks/charts/shared/cartesian/lines.py` | 97 | dash/gap line rendering cycles through a selected stroke pattern | `draw_len, gap_len = pattern[int(pattern_index) % len(pattern)]` |
| `trace/tasks/charts/shared/chart_scene_primitives.py` | 448 | deterministic muted violin fill cycling from render palette | `palette_color = muted_palette[(int(index) + int(offset)) % len(muted_palette)]` |
| `trace/tasks/charts/size_encoding/shared/sampling.py` | 170 | deterministic balanced category expansion after shuffled category support | `assigned_categories = [panel_categories[index % len(panel_categories)] for index in range(count)]` |
| `trace/tasks/charts/style_legend/shared/sampling.py` | 101 | deterministic legend color cycling from selected palette mode | `return tuple(palette[index % len(palette)] for index in range(int(count)))` |
| `trace/tasks/charts/style_legend/shared/sampling.py` | 103 | deterministic legend color cycling from selected palette mode | `return tuple(palette[index % len(palette)] for index in range(int(count)))` |
| `trace/tasks/charts/style_legend/shared/sampling.py` | 126 | deterministic series color assignment from selected palette mode | `color_rgb=tuple(colors[int(index) % len(colors)]),` |
| `trace/tasks/charts/surface_3d/panel_variation_label.py` | 89 | deterministic surface-series palette assignment | `color_rgb=PALETTE[int(index) % len(PALETTE)],` |
| `trace/tasks/charts/surface_3d/reference_nearest_label.py` | 72 | deterministic surface-series palette assignment | `color_rgb=PALETTE[int(index) % len(PALETTE)],` |
| `trace/tasks/charts/surface_3d/series_trend_label.py` | 93 | deterministic surface-series palette assignment | `color_rgb=PALETTE[int(series_index) % len(PALETTE)],` |
| `trace/tasks/charts/table/shared/rendering.py` | 621 | render/review code cycles through an already-selected palette or repeated style list | `raw = options[_selection_index(str(key)) % len(options)]` |
| `trace/tasks/charts/table/shared/rendering.py` | 633 | render/review code cycles through an already-selected palette or repeated style list | `value = str(options[_selection_index(str(key)) % len(options)])` |

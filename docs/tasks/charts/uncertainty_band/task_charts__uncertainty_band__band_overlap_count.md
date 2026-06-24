# `task_charts__uncertainty_band__band_overlap_count`

## Public Contract

1. Domain: `charts`
2. Scene: `uncertainty_band`
3. Source file: `trace/tasks/charts/uncertainty_band/band_overlap_count.py`
4. Prompt assets: `prompts/charts/uncertainty_band/charts_uncertainty_band_v1.json`
5. Supported sampled `query_id`: `single`

## Program Contract

- Program schema: `count(x_label where intersects(vertical_interval(series_a_band_at_x), vertical_interval(series_b_band_at_x))); output=integer_value; annotation=point_set(overlap_region_centers); scene=uncertainty_band; scope=band_overlap_count`.
- Program: count visible x-axis positions where the two shaded uncertainty bands overlap in vertical range.
- Answer: `integer`.
- Annotation schema: `point_set`, one centered point inside each counted overlap region.
- The answer and annotation are bound from the same sampled uncertainty-band execution trace.

## Review Notes

This task uses the scene-package layout. The public task file owns overlap construction, answer binding, annotation binding, query metadata, and prompt slots; scene-local shared code only provides uncertainty-band data structures, rendering, prompt, and projection primitives.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `count(x_label where intersects(vertical_interval(series_a_band_at_x), vertical_interval(series_b_band_at_x)))` | `integer_value` | `point_set` |

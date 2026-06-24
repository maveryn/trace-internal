# `task_charts__uncertainty_band__band_width_extremum_x_label`

## Public Contract

1. Domain: `charts`
2. Scene: `uncertainty_band`
3. Source file: `trace/tasks/charts/uncertainty_band/band_width_extremum_x_label.py`
4. Prompt assets: `prompts/charts/uncertainty_band/charts_uncertainty_band_v1.json`
5. Supported sampled `query_id`: `widest_band_x_label`, `narrowest_band_x_label`

## Program Contract

- Program schema: `arg_extreme(x_label, width(vertical_interval(target_series_band_at_x)), direction={widest,narrowest}); output=string_label; annotation=segment(answer_band_lower_upper_span); scene=uncertainty_band; scope=band_width_extremum_x_label`.
- Program: select the visible x-axis label where the requested series has the widest or narrowest shaded band.
- Answer: `string`.
- Annotation schema: `segment`, from the lower band boundary to the upper band boundary at the answer x-axis label.
- The answer and annotation are bound from the same sampled uncertainty-band execution trace.

## Review Notes

This task uses the scene-package layout. The public task file owns target-series selection, extremum direction, answer binding, annotation binding, query metadata, and prompt slots; scene-local shared code only provides uncertainty-band data structures, rendering, prompt, and projection primitives.

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `narrowest_band_x_label` | `argmin_x(width(vertical_interval(target_series_band_at_x)))` | `string_label` | `segment` |
| `widest_band_x_label` | `argmax_x(width(vertical_interval(target_series_band_at_x)))` | `string_label` | `segment` |

# CharXiv-Driven Chart Coverage Report

## Inputs reviewed

- Hugging Face dataset: `princeton-nlp/CharXiv`.
- Linked split focus: `test`; validation is also loaded to align with existing judged TRACE benchmark artifacts.
- Dataset card metadata: 2.32k total rows, validation 1k, test 1.32k, license `cc-by-sa-4.0`.
- Local cache root: `external/datasets/charxiv`.
- Existing descriptive judged sheet: `runs/charxivdesc/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge/CharXiv_descriptive_val_judged_qwen3_32b.xlsx`.
- Existing reasoning judged sheet: `runs/charxivreason/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge/CharXiv_reasoning_val_judged_qwen3_32b.xlsx`.

## Dataset summary

| Split | Rows | Top categories | Top subplot counts |
| --- | --- | --- | --- |
| validation | 1000 | econ=138, math=135, physics=127, cs=126 | 1=386, 2=168, 4=121, 3=89, 6=83, 8=29 |
| test | 1323 | stat=178, q-fin=173, eess=172, physics=167 | 1=510, 2=214, 4=154, 3=130, 6=100, 5=38 |

## Current TRACE chart inventory

- Active chart tasks: 182.
- Active chart scenes: 42.

| Scene | Tasks |
| --- | --- |
| annotated_series | 3 |
| area | 3 |
| bar_3d | 8 |
| boxplot | 4 |
| candlestick | 2 |
| combo_mark | 8 |
| contour_density | 5 |
| curve_panels | 8 |
| dashboard | 9 |
| dumbbell | 3 |
| error_interval | 3 |
| errorbar_series | 3 |
| heatmap | 5 |
| hexbin_density | 1 |
| histogram | 3 |
| marker_map | 2 |
| matrix | 3 |
| multiseries | 7 |
| parallel_coords | 4 |
| part_whole | 6 |
| pictogram | 3 |
| population_pyramid | 2 |
| radar | 4 |
| radial_progress | 4 |
| radial_sankey | 2 |
| region_map | 11 |
| sankey | 4 |
| scatter_cluster | 4 |
| scatter_points | 3 |
| scatter_readout | 3 |
| scientific_axis_frame | 2 |
| single_series | 13 |
| size_encoding | 3 |
| small_multiple | 4 |
| style_legend | 3 |
| sunburst | 4 |
| surface_3d | 4 |
| table | 8 |
| treemap | 2 |
| uncertainty_band | 2 |
| violin | 3 |
| waterfall | 4 |

## Local CharXiv model-failure signal

- Descriptive validation rows: 4000, Qwen3-VL-4B judged accuracy: 0.803.
- Reasoning validation rows: 1000, Qwen3-VL-4B judged accuracy: 0.442.
- Descriptive is comparatively high overall, but still stresses axis ticks, legends, colorbars, subplot layouts, and total tick counts.
- Reasoning is the stronger expansion signal: it is much lower accuracy and concentrates on scientific multi-panel line/scatter/field plots.

### Descriptive qid breakdown

| QID | Interpreted pattern | Rows | Accuracy |
| --- | --- | --- | --- |
| 1 | subplot_title_lookup | 244 | 0.902 |
| 2 | x_axis_label_lookup | 230 | 0.844 |
| 3 | y_axis_label_lookup | 233 | 0.760 |
| 4 | x_axis_leftmost_tick | 257 | 0.895 |
| 5 | x_axis_rightmost_tick | 239 | 0.891 |
| 6 | y_axis_lowest_tick | 249 | 0.799 |
| 7 | y_axis_highest_tick | 234 | 0.825 |
| 8 | x_axis_tick_spacing | 224 | 0.746 |
| 9 | y_axis_tick_spacing | 201 | 0.702 |
| 10 | line_count | 146 | 0.788 |
| 11 | line_intersection_boolean | 175 | 0.777 |
| 12 | legend_label_count | 182 | 0.742 |
| 13 | legend_label_order_list | 219 | 0.817 |
| 14 | colorbar_tick_range | 282 | 0.787 |
| 15 | colorbar_tick_max | 313 | 0.866 |
| 16 | overall_trend_description | 36 | 0.639 |
| 17 | total_axis_tick_count | 224 | 0.545 |
| 18 | subplot_layout_label | 247 | 0.875 |
| 19 | subplot_count | 65 | 0.892 |

### Reasoning failure buckets

| Bucket | Rows | Wrong | Accuracy |
| --- | --- | --- | --- |
| nearest_farthest_reference | 45 | 34 | 0.244 |
| legend_color_marker_style | 28 | 20 | 0.286 |
| surface_or_contour_field | 7 | 5 | 0.286 |
| point_predicate_count | 17 | 12 | 0.294 |
| distribution_shape_or_density | 77 | 49 | 0.364 |
| cross_panel_or_subfigure_comparison | 182 | 109 | 0.401 |
| correlation_or_relation_direction | 22 | 13 | 0.409 |
| axis_or_tick_reasoning | 77 | 43 | 0.442 |
| line_intersection_or_crossing | 38 | 21 | 0.447 |
| trend_decline_slope_compare | 86 | 40 | 0.535 |

### Reasoning chart-type pressure

| Chart type | Rows |
| --- | --- |
| Line Chart | 540 |
| Scatter Plot | 188 |
| Bar Chart | 109 |
| Heatmap | 109 |
| Area Chart | 56 |
| Histogram | 52 |
| Box Plot | 44 |
| Density Plot | 40 |
| Contour Plot | 27 |
| 3D Surface Plot | 26 |
| Choropleth Map | 8 |
| Error Bar Plot | 8 |
| Violin Plot | 8 |
| Bubble Chart | 7 |
| Correlation Matrix | 7 |
| Other | 7 |
| Hexbin Chart | 5 |
| Pie Chart | 5 |

## Coverage interpretation

- TRACE already has broad chart coverage and an existing `curve_panels` scientific multipanel line-grid implementation.
- The main unsupported CharXiv capability is not generic line/bar/scatter charts; it is scientific-paper rendering plus chart-frame metadata and subplot-local reasoning.
- Axis labels, tick values, tick spacing, total tick counts, legend entry order/count, colorbar ticks, and subplot titles are underrepresented because TRACE mostly asks data-mark reasoning.
- CharXiv also pressures dense scientific styles: MATLAB-like colors, black/gray line styles, markers, dashed/dotted curves, outside legends, tight grids, small fonts, and colorbars.

## Recommended expansions

| Priority | Kind | Target | Candidate tasks | Why this is not already covered |
| --- | --- | --- | --- | --- |
| P0 | existing scene/style | paper-like chart visual variation | Apply through the shared chart treatment/palette/render-parameter sampler for line, multiseries, scatter, curve_panels, heatmap, error_interval, uncertainty_band, surface_3d, and other compatible plot-like scenes. | CharXiv figures are arXiv/MATLAB-like: small fonts, thin axes, dense ticks, legends outside/inside, markers, grayscale/dashed variants, colorbars, subplot letters. This is not a new task/query/scene axis. |
| P0 | new scene | scientific_axis_metadata | axis label lookup, tick extremum, tick spacing, total tick count, subplot title lookup. | TRACE mostly asks data reasoning over marks; CharXiv descriptive questions heavily test chart-frame metadata and tick OCR. |
| P0 | existing scene expansion | curve_panels | subplot layout/count, subplot title lookup, cross-panel decline/slope comparison, panel-local point predicate count. | Current curve_panels has method-curve reasoning but not CharXiv-style figure layout and subplot-frame questions. |
| P0 | new scene or heatmap/surface expansion | colorbar_field | colorbar max/min/range/tick spacing; heatmap/contour/surface variants with continuous legends. | Descriptive qids 14/15 and many failures involve continuous legends; current heatmap tasks reason over cells, not colorbar metadata. |
| P1 | new scene | contour_density | densest region label, nearest contour cluster to coordinate, level-set crossing/count, spread/variance option selection. | CharXiv contains density, contour, hexbin, QQ-like scientific plots not represented by current scatter_cluster/readout tasks. |
| P1 | existing scene expansion | error_interval / uncertainty_band | scientific errorbar point predicate count, interval overlap at x, line-with-errorbar extremum. | CharXiv scientific plots often combine markers/lines with error bars; TRACE has interval scenes but not arXiv-style marker-series integration. |
| P1 | new scene | scientific_style_legend | map color/marker/line-style condition to legend label; count legend entries; identify curve by dashed/marker style. | Many arXiv plots use line style and marker shape as semantic encodings, not just color. |
| P2 | existing scene expansion | surface_3d | smoothness/variation option selection, subplot surface transition comparison, colorbar-backed extremum. | Reasoning failures include subjective-but-visual surface comparisons; use rendered options to keep answers verifier-friendly. |

## Implemented coverage from this analysis

The following CharXiv-driven gaps now have active TRACE chart coverage:

- Scientific-paper chart style variants were added through the shared chart style sampler.
- `curve_panels` includes additional subplot-local and cross-panel reasoning tasks.
- `scientific_axis_frame` covers bounded axis/tick metadata readout.
- `heatmap` includes continuous colorbar threshold and interval cell-count tasks.
- `contour_density`, `errorbar_series`, `style_legend`, and `hexbin_density` are active chart scenes.
- `scatter_points` covers raw point threshold counts, categorized category-mean extrema, and categorized threshold point counts over 2D scatter points.

## Implementation cautions

| Area | Guidance |
| --- | --- |
| Licensing | Use CharXiv images only for analysis/inspection. Do not copy arXiv chart images into TRACE assets or training data; synthesize styles/tasks instead. |
| Answer format | Avoid free-form long legend lists as default RLVR tasks unless we define a strict list schema. Prefer count, selected label, option label, or bounded string answer first. |
| Not Applicable | CharXiv frequently uses Not Applicable. TRACE should add explicit unanswerable branches only where distribution and verifier semantics are clean. |
| Prompt options | If a CharXiv-style choice question is adapted, options must be rendered in the image, not listed only in prompt text. |

## Suggested implementation order

1. Extend the existing shared chart style/treatment/palette/render-parameter sampler with paper-like variants and enable it first in existing line/scatter/panel scientific scenes.
2. Add `scientific_axis_metadata` with bounded answer schemas for tick/title/axis/legend/colorbar readout.
3. Expand `curve_panels` with subplot layout/count/title and cross-panel decline/slope comparisons.
4. Add `colorbar_field` or extend heatmap/surface renderers with explicit colorbar readout tasks.
5. Add `contour_density` only after reviewing generated samples, because contour/density questions can become too subjective without rendered options.

## Machine-readable summary

A JSON summary was also written to `external/datasets/charxiv/analysis/charxiv_summary.json`.

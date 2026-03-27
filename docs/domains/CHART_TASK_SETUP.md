# Chart Task Setup

## Purpose
Define the concrete v1 setup for the first chart-domain task families.

This is the chart-domain counterpart to `docs/domains/TILE_TASK_SETUP.md`: a source-of-truth note for the first implementation wave, not just a long-term idea list.

## V1 scope
1. `domain = charts`
2. First active `task_group`s:
   - `statistics`
   - `counting`
   - `readout`
   - `multiseries`
   - `distribution`
   - `composition`
   - `trend`
3. First concrete statistics tasks:
   - `task_charts_statistics_summary_value`
   - `task_charts_statistics_summary_label`
4. First concrete counting task:
   - `task_charts_counting_value_count`
5. First concrete readout task:
   - `task_charts_readout_subset_value`
6. First concrete multiseries task:
   - `task_charts_multiseries_pairwise_comparison_count`
7. First concrete distribution tasks:
   - `task_charts_distribution_histogram_count`
   - `task_charts_distribution_boxplot_label`
   - `task_charts_distribution_density_label`
8. First concrete composition task:
   - `task_charts_composition_subset_value`
9. First concrete trend task:
   - `task_charts_trend_structure_value`
10. First supported single-series chart-type renderings:
   - `area`
   - `bar`
   - `pie`
   - `donut`
   - `horizontal_bar`
   - `line`
   - `radar`
   - `scatter`
   - `dot_plot`
   - `lollipop`
11. First supported multiseries chart-type renderings:
   - `grouped_bar`
   - `grouped_horizontal_bar`
   - `multi_line`
   - `grouped_lollipop`
12. First supported distribution chart-type renderings:
   - `histogram`
   - `boxplot`
   - `violin`
13. First supported composition chart-type renderings:
   - `stacked_bar`
   - `stacked_horizontal_bar`
   - `pie`
   - `donut`

## Taxonomy
1. Keep the normal TRACE split:
   - `domain -> task_group -> task`
2. For the first statistics family:
   - `task_group = statistics`
   - active tasks: `summary_value`, `summary_label`
3. For the first counting family:
   - `task_group = counting`
   - active task: `value_count`
4. For the first readout family:
   - `task_group = readout`
   - active task: `subset_value`
5. For the first multiseries family:
   - `task_group = multiseries`
   - active task: `pairwise_comparison_count`
6. For the first distribution family:
   - `task_group = distribution`
   - active tasks: `histogram_count`, `boxplot_label`, `density_label`
7. For the first composition family:
   - `task_group = composition`
   - active task: `subset_value`
8. For the first trend family:
   - `task_group = trend`
   - active task: `structure_value`
9. The semantic query type is the public `task_variant`.
10. The chart type is the visual `scene_variant`.

### V1 variant axes
1. `task_variant`:
   - `max`
   - `min`
   - `range`
   - `mean`
   - `median`
   - `sum`
   - `mode`
2. Active single-series chart tasks use these `scene_variant` values:
   - `area`
   - `bar`
   - `pie`
   - `donut`
   - `horizontal_bar`
   - `line`
   - `radar`
   - `scatter`
   - `dot_plot`
   - `lollipop`
3. Active multiseries chart tasks currently use these `scene_variant` values:
   - `grouped_bar`
   - `grouped_horizontal_bar`
   - `multi_line`
   - `grouped_lollipop`
4. Active distribution chart tasks currently use fixed `scene_variant` values:
   - `histogram`
   - `boxplot`
   - `violin`
5. Active composition chart tasks currently use these `scene_variant` values:
   - `stacked_bar`
   - `stacked_horizontal_bar`
   - `pie`
   - `donut`
6. Active trend chart tasks currently use these `scene_variant` values:
   - `area`
   - `bar`
   - `horizontal_bar`
   - `line`
   - `dot_plot`
   - `lollipop`

Note:
1. Charts are the first planned domain where one task naturally has both a semantic axis and a chart-type axis.
2. Until the cross-domain `scene_variant` ABI note is fully written in core docs, treat this file as the domain-local contract for that split.
3. `task_charts_statistics_summary_value` currently stays on the axis-based scene variants `area|bar|horizontal_bar|line|scatter|dot_plot|lollipop`; `pie`, `donut`, and `radar` remain enabled only on the tasks where their semantics still fit cleanly.
4. `task_charts_multiseries_pairwise_comparison_count` is the first active multiseries chart task; it uses `2..3` named series, `5..10` labeled categories, category-label `label_set` evidence, and the multiseries scene variants `grouped_bar|grouped_horizontal_bar|multi_line|grouped_lollipop`.
5. The active distribution tasks use fixed `scene_variant` values `histogram`, `boxplot`, and `violin` instead of sampling across the broader chart-variant pool.
6. `task_charts_composition_subset_value` is the first active composition chart task; it uses stacked scenes for `stack_total_at_label|stack_segment_value` and pie/donut scenes for `combined_share_subset`, with ordered `integer_list` evidence over the relevant segment or slice values.
7. `task_charts_trend_structure_value` is the first active trend chart task; it uses ordered single-series charts only and currently supports `area|bar|horizontal_bar|line|dot_plot|lollipop`.

## Scene contract
1. One chart per image.
2. Active single-series chart tasks use one data series per chart in v1.
3. Active multiseries chart tasks use `2..3` named series and `5..10` labeled categories in v1.
4. Active composition chart tasks use one legend label per segment color and, for stacked scenes, one stack per category.
5. Use a clean light background with one chart frame/axis scaffold.
6. Every single-series chart mark must have one visible unique label.
7. In multiseries charts, every category must have one visible unique uppercase label and every series must have one visible legend label.
8. Labels remain the canonical prompt-facing identities for both mark-level and category-level evidence.
9. Sample one random mark color per instance and use it consistently across all bars/points in that single-series chart.
10. In v1, that mark color should be at least Lab distance `40` from white/light chart backgrounds.
11. Pie-like scenes (`pie`, `donut`) are the exception: they use a distinct sampled color per slice, a higher-contrast slice palette than the generic single-series charts, and a right-side legend with framed color swatches that maps slice colors to labels.
12. Composition scenes use their own semantics:
   - stacked charts render one stack per category and print integer segment values inside the segments,
   - pie/donut scenes render positive integer percentages that sum to `100`.
13. Distribution scenes use their own semantics:
   - histograms render contiguous numeric interval bins and treat bar height as count/frequency,
   - boxplots render quartile/whisker summaries per labeled category.

### Chart-type semantics
1. `area`
   - the statistic is computed over the plotted point `y` values, not over `x`.
   - visible point markers should be present so each labeled mark corresponds to one sampled data point.
2. `bar`
   - the statistic is computed over bar heights / bar values.
3. `line`
   - the statistic is computed over the plotted point `y` values, not over `x`.
   - visible point markers should be present so each labeled mark corresponds to one sampled data point.
4. `scatter`
   - the statistic is computed over point `y` values, not over `x`.
5. `horizontal_bar`
   - the statistic is computed over bar lengths on the horizontal axis.
6. `pie`
   - when supported by a task, the numeric contract uses positive integer percentages that sum to `100`.
   - slices use distinct sampled colors, and a legend on the right maps colors to labels.
   - legend swatches should be visually prominent even for lighter slice colors; framed swatches and stronger slice/background contrast are preferred.
   - slice angles are normalized for rendering only; tasks should reason over the printed percentages, not visual angle estimation alone.
7. `donut`
   - when supported by a task, the numeric contract uses positive integer percentages that sum to `100`.
   - slices use distinct sampled colors, and a legend on the right maps colors to labels.
   - legend swatches should be visually prominent even for lighter slice colors; framed swatches and stronger slice/background contrast are preferred.
   - donut hole size is a rendering choice only; tasks should reason over the printed percentages, not visual angle estimation alone.
8. `dot_plot`
   - the statistic is computed over plotted point `y` values, not over `x`.
9. `lollipop`
   - the statistic is computed over plotted point `y` values, not over `x`.
10. `radar`
   - when supported, the numeric contract uses the printed point values near the polygon markers.
   - each label owns one spoke, and the polygon/rings provide the visual radar structure rather than Cartesian axes.
11. `grouped_bar`
   - each category contains one bar per series, and each bar height encodes that series value for the category.
12. `grouped_horizontal_bar`
   - each category contains one horizontal bar per series, and each bar length encodes that series value for the category.
13. `multi_line`
   - each category contains one point per series, and each series point sequence is connected by a colored line.
14. `grouped_lollipop`
   - each category contains one colored lollipop stem/point per series without cumulative stacking.
15. `histogram`
   - the x-axis represents ordered numeric bins rather than arbitrary categories.
   - adjacent bars should visually touch so the scene reads as a real histogram.
16. `boxplot`
   - each label denotes one categorical boxplot.
   - the median is the line inside the box, the box spans `Q1..Q3`, and the whiskers show the minimum and maximum shown.
17. `violin`
   - each label denotes one categorical violin.
   - the widest parts of the violin indicate the modal values of the distribution.
   - `bimodal` queries rely on a clearly two-peaked violin shape rather than hidden statistics.

## Mark labels
1. Every single-series mark uses one unique randomized uppercase label.
2. Labels may be one or two letters.
3. Labels must be assigned independently of:
   - rank,
   - value,
   - left-to-right order,
   - top-to-bottom order.
4. V1 should sample chart labels from a random uppercase subset rather than always starting with `A, B, C, ...`.
5. V1 should keep chart size modest enough that one-letter labels are usually sufficient.
6. Recommended initial mark count: `5..10` for axis-based scenes.
7. `pie` and `donut` should use a tighter default effective mark-count cap such as `5..8` so the legend and printed percentages remain readable.
8. `radar` should use a tighter default effective mark-count cap such as `5..7` so the perimeter labels and printed point values remain readable.
9. Multiseries charts should keep randomized uppercase category labels separate from series legend labels so category evidence and series references never share one identity namespace.
10. Multiseries series labels should come from a short legend-name pool rather than the uppercase category-label pool.

## Value range
1. Axis-based chart marks should use integer values in the range `1..20`.
2. Pie/donut scenes should use positive integer percentages that sum to `100`.
3. Multiseries chart values should also use integer values in the range `1..20` unless a later family needs a stricter bound.
4. Statistic-specific target-answer ranges may still be narrower than the full displayed value range.

## Answer contract
1. `answer_gt.type = integer`
2. All seven statistics should produce integer answers in v1 by construction.

### Per-variant answer meaning
1. `max`: highest displayed value
2. `min`: lowest displayed value
3. `range`: `max - min`
4. `mean`: arithmetic mean of all displayed values
5. `median`: median of all displayed values
6. `sum`: sum of all displayed values
7. `mode`: unique modal value
8. `sum` should use the full feasible support implied by the active mark-count and per-mark value bounds, not an additional narrow task-local cap.

## Evidence contract
1. V1 default `evidence_gt.type` for the statistics family is `label_set`.
2. The evidence is the set of labeled marks that directly witness the requested statistic.
3. Label order must be deterministic.

### Evidence by statistic
1. `max`
   - singleton `label_set` containing the unique maximum mark
2. `min`
   - singleton `label_set` containing the unique minimum mark
3. `range`
   - two-label `label_set` containing the unique minimum mark and unique maximum mark
4. `mean`
   - `label_set` containing all chart marks used in the average
5. `median`
   - singleton `label_set` containing the median mark
6. `sum`
   - `label_set` containing all chart marks used in the sum
7. `mode`
   - `label_set` containing all marks whose value equals the unique modal value

### Why `label_set` in v1
1. The current ABI already supports `label_set`.
2. A chart-native evidence type such as `label_value_map` may be worth adding later, but it should not block the first chart task family.
3. Raw plotted geometry, bar boxes, or point coordinates should stay in trace as derived render projections rather than the public evidence contract for this family.

## Uniqueness and construction rules
1. Final numeric answer must be unique by construction.
2. `max` / `min`
   - require a unique maximum / unique minimum mark.
3. `range`
   - require a unique maximum and unique minimum mark.
   - prefer `range > 0` in v1.
4. `mean`
   - construct the dataset so the mean is an integer.
5. `median`
   - use an odd number of marks in v1.
   - with the current `5..10` mark-count policy, this means the effective median support is `5|7|9`.
   - prefer distinct values in v1 so the median mark is unique and evidence is singleton.
6. `sum`
   - no extra extremum-style uniqueness rule is needed beyond unique final answer.
7. `mode`
   - require one unique modal value.
   - evidence includes every mark with that modal value.

## Sampling policy
1. Global sampling stays at the task level, as elsewhere in TRACE.
2. Inside `task_charts_statistics_summary_value`, sample:
   - `task_variant` from the supported statistics set,
   - `scene_variant` from the supported chart types for that statistic.
3. These two axes should be sampled independently at the policy level, subject to compatibility.
4. Then sample the target answer from feasible support before finalizing the concrete chart data/layout.

## Prompt rules
1. The chart-family prompt layer should establish:
   - that the image is a chart,
   - that marks are labeled,
   - that the answer must be derived from the chart values.
2. The task layer should ask only for the statistic itself.
3. When `scene_variant` is `area`, `line`, `scatter`, `dot_plot`, or `lollipop`, the prompt should make it explicit that the statistic is over the plotted values (`y` values), not over the horizontal positions.
4. When `scene_variant` is `horizontal_bar`, the prompt should make it explicit that values are read from the horizontal axis.
5. When `scene_variant` is `pie` or `donut`, the prompt should make it explicit that the relevant values are the printed percentages shown on the slices and that the legend on the right maps slice colors to labels.
6. When `scene_variant` is `radar`, the prompt should make it explicit that each label owns one spoke and that the relevant values are the printed values near the plotted radar points.
7. Do not phrase chart statistics in category-name terms for this family; the requested output is always the numeric summary value.
8. `answer_and_evidence` prompts should ask for the supporting labeled marks, not pixel boxes or coordinates.

### Recommended task-layer wording
1. `max`
   - ask for the highest value among the labeled marks
2. `min`
   - ask for the lowest value among the labeled marks
3. `range`
   - ask for the difference between the highest and lowest values
4. `mean`
   - ask for the mean (average) value
5. `median`
   - ask for the median value
6. `sum`
   - ask for the total / sum of the values
7. `mode`
   - ask for the mode value

### Recommended prompt slots
1. `object_description_<scene_variant>`
   - describe the chart marks for the chosen chart type
2. `question_text_<task_variant>`
   - one per statistic kind
3. `evidence_hint`
   - should explain that evidence is the set of supporting mark labels
4. `answer_hint`
   - should explain that the answer is a numeric value
5. `json_example_answer_only_<task_variant>`
   - variant-aware examples are preferred
6. `json_example_<task_variant>`
   - variant-aware examples are preferred

## Trace guidance
1. Keep symbolic mark records in trace with:
   - `mark_id`
   - visible `label`
   - numeric `value`
   - chart-type-specific geometry metadata
2. Keep `task_variant` and `scene_variant` explicit in trace/query metadata.
3. Keep derived pixel geometry in trace, not as the source of truth.

## Deferred follow-up
1. Add a chart-native evidence type if `label_set` becomes too weak for later chart families.
2. Formalize the cross-domain `scene_variant` ABI in core docs once charts are implemented.
3. Revisit whether the seven statistic kinds should later split into multiple tasks if charts need more task-level mass.

## Companion label-answer task
1. The first follow-up companion task is `task_charts_statistics_summary_label`.
2. It reuses the same chart scenes and `scene_variant` values (`area|bar|pie|donut|horizontal_bar|line|radar|scatter|dot_plot|lollipop`) but narrows the semantic `task_variant` set to:
   - `argmax`
   - `argmin`
   - `median_label`
3. Its contract is:
   - `answer_gt.type = option_letter`
   - `evidence_gt.type = integer`
4. Prompt-facing evidence is the winning numeric statistic value, while the answer is the visible label of the winning mark.
5. The label-answer task intentionally excludes `mean`, `sum`, `range`, and `mode` because those statistics do not map cleanly to one unique label answer in v1.

## Counting follow-up task
1. The first counting-family task is `task_charts_counting_value_count`.
2. It reuses the same chart scenes and `scene_variant` values (`area|bar|pie|donut|horizontal_bar|line|radar|scatter|dot_plot|lollipop`) but changes the semantic `task_variant` set to:
   - `above_threshold`
   - `below_threshold`
   - `in_interval`
3. Its contract is:
   - `answer_gt.type = integer`
   - `evidence_gt.type = label_set`
4. Threshold queries use strict comparisons (`>` for `above_threshold`, `<` for `below_threshold`).
5. Interval queries use inclusive `[interval_min, interval_max]` bounds.
6. Empty `label_set` evidence is valid when the answer count is `0`.

## Readout follow-up task
1. The first readout-family task is `task_charts_readout_subset_value`.
2. It reuses the same chart scenes and `scene_variant` values (`area|bar|pie|donut|horizontal_bar|line|radar|scatter|dot_plot|lollipop`) and introduces semantic `task_variant` values:
   - `sum_two`
   - `difference_two_abs`
   - `max_two`
   - `min_two`
   - `mean_two`
3. Its contract is:
   - `answer_gt.type = integer`
   - `evidence_gt.type = integer_list`
4. Prompt-facing evidence is the ordered pair of queried values, in the same order the two queried labels appear in the prompt.
5. Readout tasks keep the queried labels in trace/query metadata and keep the full label->value table in trace so the integer-list evidence order remains explicit and auditable.

# Charts Task-Unit Audit

Task-unit audit for `domain=charts` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The charts domain is mostly healthy as a TRACE task-unit inventory.
2. Most chart tasks represent distinct visual-grounding families rather than thin query renamings.
3. The main exception is `task_charts_composition_subset_value`, which currently bundles two different composition-grounding families:
   - stacked-category composition readout,
   - pie/donut subset-share composition.
4. Recommended domain outcome:
   - `Keep`: `9`
   - `Split`: `1`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_charts_statistics_summary_value`
- Outcome: `Keep`
- Why: one stable single-series chart-statistics family with broad scene variation and broad statistic variation.
- Scene variety: strong (`area|bar|horizontal_bar|line|scatter|dot_plot|lollipop`)
- Query variety: strong (`max|min|range|mean|median|sum|mode`)
- Grounding necessity: strong; the model must read multiple marks and aggregate over visually grounded values.
- Evidence fit: good; `label_set` witness stays local and meaningful for all variants.
- Follow-up: none required for task-unit shape.

### `task_charts_statistics_summary_label`
- Outcome: `Keep`
- Why: still one coherent grounding family despite overlapping infrastructure with `summary_value`; the job is label identification from a chart statistic rather than numeric aggregation.
- Scene variety: strong (`area|bar|pie|donut|horizontal_bar|line|radar|scatter|dot_plot|lollipop`)
- Query variety: moderate (`argmax|argmin|median_label`)
- Grounding necessity: strong; the model must identify the winning visible mark rather than only compute a scalar.
- Evidence fit: acceptable; scalar witness value is narrow but still natural for this answer-label family.
- Follow-up: none required now.

### `task_charts_counting_value_count`
- Outcome: `Keep`
- Why: one stable threshold/interval counting family over labeled single-series charts.
- Scene variety: strong (axis-based charts plus pie/donut/radar)
- Query variety: moderate (`above_threshold|below_threshold|in_interval`)
- Grounding necessity: strong; requires reading per-mark values and grounding the qualifying mark set.
- Evidence fit: good; `label_set` of qualifying marks is natural and non-vacuous.
- Follow-up: none required now.

### `task_charts_readout_subset_value`
- Outcome: `Keep`
- Why: one coherent two-label readout family with stable witness semantics across all chart variants.
- Scene variety: strong (same broad single-series chart set as the counting family)
- Query variety: strong (`sum_two|difference_two_abs|max_two|min_two|mean_two`)
- Grounding necessity: strong; requires locating two queried labels and reading their values in the image.
- Evidence fit: good; ordered `integer_list` witness matches the ordered queried labels and stays grounded.
- Follow-up: none required now.

### `task_charts_multiseries_pairwise_comparison_count`
- Outcome: `Keep`
- Why: one distinct multiseries comparison family, not just a thin extension of the single-series counting task.
- Scene variety: strong (`grouped_bar|grouped_horizontal_bar|multi_line|grouped_lollipop`)
- Query variety: modest but sufficient (`series_a_gt_b_count|series_a_lt_b_count`)
- Grounding necessity: strong; requires legend grounding, category grounding, and pairwise comparison across series.
- Evidence fit: good; `label_set` of winning categories is natural and local.
- Follow-up: none required now.

### `task_charts_distribution_histogram_count`
- Outcome: `Keep`
- Why: one stable histogram-specific distribution family with a fixed but visually distinctive scaffold.
- Scene variety: moderate; fixed histogram scaffold, but bin structure, interval labels, and query focus vary substantially.
- Query variety: moderate (`modal_bin_count|interval_mass|cumulative_count_to_bin`)
- Grounding necessity: strong; requires reading numeric bins and counts rather than generic chart heuristics.
- Evidence fit: good; `label_set` of contributing bins is natural.
- Follow-up: none required now.

### `task_charts_distribution_boxplot_label`
- Outcome: `Keep`
- Why: one coherent boxplot-summary family. Narrower than some chart tasks, but still a valid single grounding unit.
- Scene variety: moderate; fixed boxplot scaffold with variable quartile geometry and category count.
- Query variety: moderate (`highest_median|largest_iqr|smallest_iqr`)
- Grounding necessity: strong; requires reading boxplot semantics from the plotted summaries.
- Evidence fit: acceptable; scalar witness is narrow but still tied to the visible winning summary statistic.
- Follow-up: watch only; if charts later rebalance task-unit breadth aggressively, this is a candidate for broadening with additional boxplot summary variants rather than merging.

### `task_charts_distribution_density_label`
- Outcome: `Keep`
- Why: one coherent violin-shape family with visibly different density-shape queries.
- Scene variety: moderate; fixed violin scaffold but meaningful variation in support shape and mode structure.
- Query variety: moderate (`highest_mode|lowest_mode|bimodal_label`)
- Grounding necessity: strong; requires reading the density shape rather than just text or labels.
- Evidence fit: good; `integer_list` of mode values is natural for the answer-label family.
- Follow-up: none required now.

### `task_charts_trend_structure_value`
- Outcome: `Keep`
- Why: one ordered-sequence trend family with stable witness semantics across ordered chart types.
- Scene variety: strong (`area|bar|horizontal_bar|line|dot_plot|lollipop`)
- Query variety: strong (`peak_count|trough_count|longest_increasing_streak|longest_decreasing_streak`)
- Grounding necessity: strong; requires reading chart order and local/global structure over the plotted sequence.
- Evidence fit: good; `label_set` witness of peaks/troughs/streak labels is natural.
- Follow-up: none required now.

### `task_charts_composition_subset_value`
- Outcome: `Split`
- Why: this task currently mixes two distinct grounding families that share a composition theme but not one stable visual-grounding job.
- Scene variety: high, but too mixed rather than uniformly broad.
- Query variety: mixed across incompatible composition jobs:
  - stacked-category composition (`stack_total_at_label`, `stack_segment_value`)
  - pie/donut subset-share composition (`combined_share_subset`)
- Grounding necessity: strong in both halves, but the grounding pattern differs substantially between them.
- Evidence fit: mixed:
  - stacked variants use queried-stack segment values,
  - pie/donut variant uses whole-chart slice percentages.
- Follow-up:
  1. Split into a stacked-composition task and a pie/donut-share task.
  2. Keep stacked scenes with category+legend grounding together.
  3. Keep pie/donut subset-share scenes together as a separate composition family.

## Recommended next action
1. Leave the other chart tasks unchanged for now.
2. Treat `task_charts_composition_subset_value` as the first concrete split candidate when doing benchmark-unit rebalancing.

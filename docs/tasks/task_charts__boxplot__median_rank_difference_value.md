# `task_charts__boxplot__median_rank_difference_value`

## Contract
1. Domain: `charts`
2. Scene id: `boxplot`
3. Source implementation domain/group: `charts/distribution`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.
6. Answer type: `integer`.
7. Evidence type: `keyed_point_map`.

Prompt-facing evidence binds each median witness to a role key:

- `median_top_second_difference_value`: `highest_median_boxplot`, `second_highest_median_boxplot`
- `median_top_third_difference_value`: `highest_median_boxplot`, `third_highest_median_boxplot`
- `median_top_bottom_difference_value`: `highest_median_boxplot`, `lowest_median_boxplot`

## Implementation
1. Registered class: `trace.tasks.charts.distribution.boxplot_label.ChartsDistributionBoxplotMedianRankDifferenceValueTask`
2. Prompt lookup domain/group: `charts/distribution`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

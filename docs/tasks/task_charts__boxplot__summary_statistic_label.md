# `task_charts__boxplot__summary_statistic_label`

## Contract
1. Domain: `charts`
2. Scene id: `boxplot`
3. Source implementation domain/group: `charts/distribution`
4. Query id: `iqr_extremum_label`, `median_reference_label`
5. Semantic query details are recorded in `query_id` and trace params.
6. Answer type: `string`, the exact visible boxplot label.
7. Evidence type:
   - `median_reference_label`: `keyed_point_map` with keys `reference_boxplot` and `answer_boxplot`.
   - `iqr_extremum_label`: `point_set` with one point at the winning boxplot center.

## Implementation
1. Registered class: `trace.tasks.charts.distribution.boxplot_label.ChartsDistributionBoxplotSummaryLabelTask`
2. Prompt lookup domain/group: `charts/distribution`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

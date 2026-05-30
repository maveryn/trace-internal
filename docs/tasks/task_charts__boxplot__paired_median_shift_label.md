# `task_charts__boxplot__paired_median_shift_label`

## Contract
1. Domain: `charts`
2. Scene id: `boxplot`
3. Source implementation domain/group: `charts/distribution`
4. Query id: sampled internally and recorded in `query_id`
5. Semantic query details are recorded in `query_id` and trace params.
6. Answer type: `string`, the exact visible matched label.
7. Evidence type: `keyed_point_map` with keys `before_boxplot` and `after_boxplot`.

Prompt-facing evidence marks the before and after median witnesses for the winning label.

## Implementation
1. Registered class: `trace.tasks.charts.distribution.boxplot_label.ChartsDistributionBoxplotPairedMedianShiftLabelTask`
2. Prompt lookup domain/group: `charts/distribution`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

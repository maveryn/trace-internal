# `task_charts__histogram__bin_count_between_values`

## Contract
1. Domain: `charts`
2. Scene id: `histogram`
3. Source implementation scene package: `charts/histogram`
4. Query id: `single`
5. Semantic query details are recorded in trace params.

## Implementation
1. Registered class: `trace.tasks.charts.histogram.bin_count_between_values.ChartsDistributionHistogramBinCountBetweenValuesTask`
2. Prompt lookup domain/scene: `charts/histogram`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_count`.
2. Annotation schema: `bbox_set`.
3. Annotation marks every histogram bar whose x-axis value lies inside the displayed value interval.
4. Renderer context such as axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `count(bin where inside(value_interval(bin), query_interval)); output=integer_count; annotation=bbox_set(matching_bins); scene=histogram; scope=bin_count_between_values`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `count.interval_membership` | `integer_count` | `bbox_set` |

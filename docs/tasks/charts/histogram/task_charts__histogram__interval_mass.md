# `task_charts__histogram__interval_mass`

## Contract
1. Domain: `charts`
2. Scene id: `histogram`
3. Source implementation scene package: `charts/histogram`
4. Query ids: `inside_interval_mass`, `outside_interval_mass`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.charts.histogram.interval_mass.ChartsDistributionHistogramIntervalMassTask`
2. Prompt lookup domain/scene: `charts/histogram`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `bbox_set`.
3. Annotation marks the histogram bars included in the requested inside/outside interval total.
4. Renderer context such as axes, decorative labels, titles, and distractor text is metadata unless the task explicitly asks for it as annotation.

## Program Contract
- `sum(count(bin) for bin where interval_relation(bin, query_interval, relation={inside,outside})); output=integer_value; annotation=bbox_set(included_bins); scene=histogram; scope=interval_mass`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `inside_interval_mass` | `numeric.interval_mass(relation=inside)` | `integer_value` | `bbox_set` |
| `outside_interval_mass` | `numeric.interval_mass(relation=outside)` | `integer_value` | `bbox_set` |

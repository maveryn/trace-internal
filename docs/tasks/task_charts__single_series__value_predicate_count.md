# `task_charts__single_series__value_predicate_count`

## Contract
1. Domain: `charts`
2. Scene id: `single_series`
3. Source implementation domain/group: `charts/counting`
4. Query id: `in_interval`, `threshold_count`
5. Semantic query details are recorded in `query_id` and trace params.
6. Evidence type: `point_set`.

## Evidence
Prompt-facing evidence is a homogeneous `point_set` over every mark satisfying
the requested value predicate. Evidence cardinality equals the integer answer.

## Implementation
1. Registered class: `trace.tasks.charts.counting.value_count.ChartsCountingValuePredicateCountTask`
2. Prompt lookup domain/group: `charts/counting`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and evidence are produced from the same metadata execution trace.

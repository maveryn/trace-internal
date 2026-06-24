# `task_charts__small_multiple__composition_shift_l1_distance`

## Contract
1. Domain: `charts`
2. Scene id: `small_multiple`
3. Public task id: `task_charts__small_multiple__composition_shift_l1_distance`
4. Query id: `single`

## Implementation
1. Registered class: `trace.tasks.charts.small_multiple.composition_shift_l1_distance.ChartsCompositionSmallMultiplesCompositionShiftL1DistanceTask`
2. Prompt bundle: `charts_small_multiple_v1`
3. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
4. Answers and annotation are produced from the same metadata execution trace.

## Annotation Contract
1. Answer schema: `integer_value`.
2. Annotation schema: `point_map`.
3. Annotation marks corresponding segment-percentage labels in the two compared panels.

## Program Contract
`sum(abs(share(end_panel,segment)-share(start_panel,segment)) for segment in segments); output=integer_value; annotation=point_map(start_end_segment_points); scene=small_multiple; scope=composition_shift_l1_distance`

## Query Details

| Query id | Program signature | Answer schema | Annotation schema |
|---|---|---|---|
| `single` | `sum(abs(share(end_panel,segment)-share(start_panel,segment)) for segment in segments)` | `integer_value` | `point_map` |

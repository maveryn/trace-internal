# `task_symbolic__music_staff__meter_type_count`

## Contract
1. Domain: `symbolic`
2. Scene id: `music_staff`
3. Source implementation domain/group: `symbolic/notation`
4. Task id: `task_symbolic__music_staff__meter_type_count`
5. Objective contract: meter type count.
6. Supported sampled `query_id`: `meter_type_count`
7. `answer_gt.type`: `integer`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: one bbox for each counted measure range; use an empty `bbox_set` when no shown measures match the requested meter type.

## Implementation
1. Registered class: `trace.tasks.symbolic.notation.music_staff.SymbolicMeterTypeCountTask`
2. Prompt lookup domain/group: `symbolic/notation`
3. Prompt bundle: `symbolic_v0`
4. Example sampled scene variant: `exam_scan`

## Notes
1. The scene shows four compact measures in one staff panel, each with a visible measure-local time signature.
2. The prompt asks for the number of shown measures in simple or compound meter.
3. Generation samples the target answer from `0..4`, then constructs exactly that many matching measures.
4. Answers and annotation come from the same metadata execution trace.

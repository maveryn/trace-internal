# `task_symbolic__music_staff__same_pitch_pair_count`

## Contract
1. Domain: `symbolic`
2. Scene id: `music_staff`
3. Source implementation domain/group: `symbolic/notation`
4. Task id: `task_symbolic__music_staff__same_pitch_pair_count`
5. Objective contract: same-pitch pair count.
6. Supported sampled `query_id`: `same_pitch_pair_count`
7. `answer_gt.type`: `integer`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: one bbox for each counted note-pair range; use an empty `bbox_set` when no shown pairs have the same pitch.

## Implementation
1. Registered class: `trace.tasks.symbolic.notation.music_staff.SymbolicSamePitchPairCountTask`
2. Prompt lookup domain/group: `symbolic/notation`
3. Prompt bundle: `symbolic_v0`
4. Example sampled scene variant: `exam_scan`

## Notes
1. The scene shows four labeled note-pair ranges in one staff panel.
2. The prompt asks for the number of pairs whose two notes have the same pitch.
3. Generation samples the target answer from `0..4`, then constructs exactly that many matching pairs.
4. Answers and annotation come from the same metadata execution trace.

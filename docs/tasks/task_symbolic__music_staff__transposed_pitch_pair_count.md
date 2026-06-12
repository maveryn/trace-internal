# `task_symbolic__music_staff__transposed_pitch_pair_count`

## Contract
1. Domain: `symbolic`
2. Scene id: `music_staff`
3. Source implementation domain/group: `symbolic/notation`
4. Task id: `task_symbolic__music_staff__transposed_pitch_pair_count`
5. Objective contract: transposed pitch pair count.
6. Supported sampled `query_id`: `transposed_pitch_pair_count`
7. `answer_gt.type`: `integer`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the counted note-pair ranges; use an empty annotation when the count is zero.

## Implementation
1. Registered class: `trace.tasks.symbolic.notation.music_staff.SymbolicTransposedPitchPairCountTask`
2. Prompt lookup domain/group: `symbolic/notation`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `notebook_staff`

## Notes
1. The scene shows four marked note-pair ranges and asks how many second notes match the requested upward interval from the first note.
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.

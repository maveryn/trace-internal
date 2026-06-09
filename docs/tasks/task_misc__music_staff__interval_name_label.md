# `task_misc__music_staff__interval_name_label`

## Contract
1. Domain: `misc`
2. Scene id: `music_staff`
3. Source implementation domain/group: `misc/notation`
4. Task id: `task_misc__music_staff__interval_name_label`
5. Objective contract: interval name label.
6. Supported sampled `query_id`: `interval_name_label`
7. `answer_gt.type`: `string`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.misc.notation.music_staff.MiscIntervalNameLabelTask`
2. Prompt lookup domain/group: `misc/notation`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `exam_scan`

## Notes
1. This task doc was refreshed during taxonomy-v0 puzzle migration from a retired broader public task id.
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.

# `task_misc__spinner_probability__multi_attribute_or_probability`

## Contract
1. Domain: `misc`
2. Scene id: `spinner_probability`
3. Source implementation domain/group: `misc/probability`
4. Task id: `task_misc__spinner_probability__multi_attribute_or_probability`
5. Objective contract: multi attribute or probability.
6. Supported sampled `query_id`: `single_color_or_shape_probability`
7. `answer_gt.type`: `string`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.misc.probability.spinner.MiscProbabilitySpinnerMultiAttributeOrProbabilityTask`
2. Prompt lookup domain/group: `misc/probability`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `spinner_card`

## Notes
1. This task doc was refreshed during taxonomy-v0 puzzle migration from a retired broader public task id.
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.

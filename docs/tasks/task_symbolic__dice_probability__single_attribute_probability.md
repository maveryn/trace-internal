# `task_symbolic__dice_probability__single_attribute_probability`

## Contract
1. Domain: `symbolic`
2. Scene id: `dice_probability`
3. Source implementation domain/group: `symbolic/probability`
4. Task id: `task_symbolic__dice_probability__single_attribute_probability`
5. Objective contract: single attribute probability.
6. Supported sampled `query_id`: `single_value_set_probability`
7. `answer_gt.type`: `string`
8. `annotation_gt.type`: `keyed_bbox_map`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.symbolic.probability.dice.SymbolicProbabilityDiceSingleAttributeProbabilityTask`
2. Prompt lookup domain/group: `symbolic/probability`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `dice_tray_clean`

## Notes
1. This task doc was refreshed during taxonomy-v0 puzzle migration from a retired broader public task id.
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.

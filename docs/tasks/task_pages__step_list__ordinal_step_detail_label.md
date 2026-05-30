# `task_pages__step_list__ordinal_step_detail_label`

## Taxonomy
1. Domain: `pages`
2. Scene id: `step_list`
3. Task id: `task_pages__step_list__ordinal_step_detail_label`
4. Implementation group: `pages/step_list`

## Contract
Reads one exact visible title or detail from a numbered instructional step-list page.

Query ids: `nth_step_title|nth_step_detail|step_after_named_step`.

Answers are exact visible strings. Evidence is a `keyed_bbox_map` over the minimal visible text witnesses used to identify the answer: `target_title` for title queries, `target_detail` for detail queries, and `source_title` plus `target_title` for `step_after_named_step`.
The model-facing evidence hint is query-specific and names these exact keys rather than using generic role labels.

## Prompt + Trace
1. Prompt bundle: `pages_step_list_v0`
2. Scene key: `step_list`
3. Task key: `step_lookup_query`
4. Trace records step order, title/detail strings, source/target step ids, and title/detail bboxes after final rendering.

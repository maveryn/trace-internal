# `task_symbolic__music_staff__duration_equivalence_label`

## Public Taxonomy
1. Domain: `symbolic`
2. Scene id: `music_staff`
3. Scene: `notation`
4. Task id: `task_symbolic__music_staff__duration_equivalence_label`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id`: `duration_equivalence_label`
3. Prompts ask which image-visible option card has the same duration as the marked note.
4. Internal variation includes eighth, quarter, dotted-quarter, half, dotted-half, and whole durations with `engraved_sheet|exam_scan|notebook_staff` scene variants.

## Answer And Annotation
1. `answer_gt.type = string`
2. `answer_gt.value` is the single capital-letter option label rendered in the image.
3. `annotation_gt.type = bbox_set`
4. Annotation contains the target-duration note bbox and the selected option-card bbox.

## Trace Contract
1. `execution_trace.notation_metadata` records the target duration and option durations.
2. `execution_trace.annotation_item_ids` records the rendered notation item ids used for bbox projection.
3. `render_map.item_bboxes_px` exposes staff-item and option-card bboxes after final layout.

## Prompt Contract
1. Bundle: `symbolic_v0`
2. Scene key: `music_staff`
3. Task key: `music_notation_query`
4. Query key: `duration_equivalence_label`

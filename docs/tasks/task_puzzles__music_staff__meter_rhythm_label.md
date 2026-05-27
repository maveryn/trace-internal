# `task_puzzles__music_staff__meter_rhythm_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `music_staff`
3. Task group: `notation`
4. Task id: `task_puzzles__music_staff__meter_rhythm_label`

## Query Contract
1. Public `query_variant`: `default`
2. `query_id`: `time_signature_label|meter_type_label|articulation_symbol_label`
3. Prompts ask for time signatures, simple/compound meter labels, or articulation-symbol names.
4. Internal variation includes simple and compound time signatures, staccato/tenuto/accent/fermata marks, and `engraved_sheet|exam_scan|notebook_staff` scene variants.

## Answer And Evidence
1. `answer_gt.type = string`
2. `answer_gt.value` is a time-signature string, meter-type string, or articulation-symbol string.
3. `evidence_gt.type = bbox_set`
4. Evidence contains target bars, time signatures, notes, or articulation-symbol bboxes depending on the query.

## Trace Contract
1. `execution_trace.notation_metadata` records durations, time signatures, and articulation labels.
2. `execution_trace.evidence_item_ids` records the rendered notation item ids used for bbox projection.
3. `render_map.item_bboxes_px` exposes staff-item bboxes after final layout.

## Prompt Contract
1. Bundle: `puzzles_notation_v0`
2. Scene key: `music_staff`
3. Task key: `music_notation_query`
4. Query keys match the public `query_id` values.

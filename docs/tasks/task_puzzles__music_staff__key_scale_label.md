# `task_puzzles__music_staff__key_scale_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `music_staff`
3. Task group: `notation`
4. Task id: `task_puzzles__music_staff__key_scale_label`

## Query Contract
1. Public `query_variant`: `default`
2. `query_id`: `key_signature_label|scale_validation_truth_label|scale_degree_function_label`
3. Prompts ask for the key represented by a key signature, whether a displayed scale is correct for a named key, or the scale-degree function of a marked note.
4. Internal variation:
   - major keys with visible synthetic accidentals
   - correct and intentionally altered scale spellings
   - scale-degree functions from tonic through leading tone
   - scene variant: `engraved_sheet|exam_scan|notebook_staff`

## Answer And Evidence
1. `answer_gt.type = string`
2. `answer_gt.value` is a key label, `True|False`, or a scale-degree function string.
3. `evidence_gt.type = bbox_set`
4. Evidence contains key-signature bboxes and the scale-note or marked-note bboxes needed by the query.

## Trace Contract
1. `execution_trace.notation_metadata` records the key, scale-degree, and alteration metadata.
2. `execution_trace.evidence_item_ids` records the rendered notation item ids used for bbox projection.
3. `render_map.item_bboxes_px` exposes key-signature and note bboxes after final layout.

## Prompt Contract
1. Bundle: `puzzles_notation_v0`
2. Scene key: `music_staff`
3. Task key: `music_notation_query`
4. Query keys match the public `query_id` values.

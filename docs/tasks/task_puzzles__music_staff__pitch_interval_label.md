# `task_puzzles__music_staff__pitch_interval_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `music_staff`
3. Task group: `notation`
4. Task id: `task_puzzles__music_staff__pitch_interval_label`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id`: `note_name_label|interval_name_label|same_pitch_truth_label|transposed_pitch_truth_label`
3. Prompts ask for note names, interval names, pitch-equivalence truth values, or transposition truth values on a synthetic staff.
4. Internal variation:
   - clef: currently treble for this first scene family
   - accidentals: natural, sharp, and flat notes
   - scene variant: `engraved_sheet|exam_scan|notebook_staff`

## Answer And Evidence
1. `answer_gt.type = string`
2. `answer_gt.value` is a note name, interval name, or `True|False`.
3. `evidence_gt.type = bbox_set`
4. Evidence contains the marked note, note pair, or source/target transposition note bboxes.

## Trace Contract
1. `execution_trace.notation_metadata` records the generated pitch or interval metadata.
2. `execution_trace.evidence_item_ids` records the rendered notation item ids used for bbox projection.
3. `render_map.item_bboxes_px` exposes note and staff-item bboxes after final layout.

## Prompt Contract
1. Bundle: `puzzles_notation_v0`
2. Scene key: `music_staff`
3. Task key: `music_notation_query`
4. Query keys match the public `query_id` values.

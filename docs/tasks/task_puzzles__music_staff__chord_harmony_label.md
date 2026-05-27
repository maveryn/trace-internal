# `task_puzzles__music_staff__chord_harmony_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `music_staff`
3. Task group: `notation`
4. Task id: `task_puzzles__music_staff__chord_harmony_label`

## Query Contract
1. Public `query_variant`: `default`
2. `query_id`: `chord_quality_label|roman_numeral_label|chord_inversion_label`
3. Prompts ask for chord quality, roman numeral in a named key, or inversion name.
4. Internal variation includes triads, seventh chords, major-key functions, root position, inversions, and `engraved_sheet|exam_scan|notebook_staff` scene variants.

## Answer And Evidence
1. `answer_gt.type = string`
2. `answer_gt.value` is a chord-quality string, roman numeral string, or inversion string.
3. `evidence_gt.type = bbox_set`
4. Evidence contains the marked chord bbox and key-signature bbox where relevant.

## Trace Contract
1. `execution_trace.notation_metadata` records chord roots, qualities, and inversions.
2. `execution_trace.evidence_item_ids` records the rendered notation item ids used for bbox projection.
3. `render_map.item_bboxes_px` exposes chord and key-signature bboxes after final layout.

## Prompt Contract
1. Bundle: `puzzles_notation_v0`
2. Scene key: `music_staff`
3. Task key: `music_notation_query`
4. Query keys match the public `query_id` values.

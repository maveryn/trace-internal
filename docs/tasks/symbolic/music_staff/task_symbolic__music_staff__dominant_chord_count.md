# `task_symbolic__music_staff__dominant_chord_count`

## Public Taxonomy
1. Domain: `symbolic`
2. Scene id: `music_staff`
3. Scene: `notation`
4. Task id: `task_symbolic__music_staff__dominant_chord_count`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id`: `dominant_count_value`
3. Prompts ask for the number of dominant chords in a visible key context.
4. Internal variation includes major-key contexts, chord qualities, dominant-position placement, and `engraved_sheet|exam_scan|notebook_staff` scene variants.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the number of dominant chords.
3. `annotation_gt.type = bbox_set`
4. Annotation contains the key-signature bbox followed by every dominant-chord bbox.

## Trace Contract
1. `execution_trace.notation_metadata` records the key and dominant chord positions.
2. `execution_trace.annotation_item_ids` records the rendered notation item ids used for bbox projection.
3. `render_map.item_bboxes_px` exposes chord and key-signature bboxes after final layout.

## Prompt Contract
1. Bundle: `symbolic_v0`
2. Scene key: `music_staff`
3. Task key: `music_notation_query`
4. Query key: `dominant_count_value`

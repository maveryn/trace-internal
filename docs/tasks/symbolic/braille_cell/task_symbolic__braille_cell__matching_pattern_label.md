# `task_symbolic__braille_cell__matching_pattern_label`

## Public Taxonomy
1. Domain: `symbolic`
2. Scene id: `braille_cell`
3. Scene: `notation`
4. Task id: `task_symbolic__braille_cell__matching_pattern_label`

## Query Contract
1. Query metadata: `query_id`
2. Supported `query_id` values:
   - `matching_pattern_label`
3. Prompts ask which labeled visual option cell has the same raised-dot pattern as the reference Braille cell.
4. The scene always renders exactly six visual options labeled `A..F`.
5. Internal variation includes reference patterns with `1..6` raised dots, distractor patterns, and `clean_card|notebook_card|exam_scan` scene variants.

## Answer And Annotation
1. `answer_gt.type = string`
2. `answer_gt.value` is the single capital-letter option label.
3. `annotation_gt.type = keyed_bbox_map`
4. Annotation contains role-keyed bboxes:
   - `reference_cell`
   - `selected_option`
5. Distractor option bboxes, individual dots, labels, and panel chrome are not prompt-facing annotation.

## Trace Contract
1. `execution_trace.braille_metadata.reference_pattern` records the reference dot pattern.
2. `execution_trace.braille_metadata.correct_option_label` records the answer label.
3. `execution_trace.braille_metadata.option_patterns` records each option label's dot pattern.
4. `render_map.item_bboxes_px` exposes reference and option cell bboxes after final layout.
5. `render_map.dot_centers_px` exposes all dot centers for debugging and replay.

## Prompt Contract
1. Bundle: `symbolic_v0`
2. Scene key: `braille_cell`
3. Task key: `braille_matching_pattern_label`
4. Query key: `matching_pattern_label`
5. Prompt wording must ask for the labeled option matching the reference raised-dot pattern. Options are visual cells in the image, not prompt-only choices.

## Determinism + Constraints
1. Deterministic generation and rendering from `instance_seed`.
2. Unique-answer policy: exactly one option has the same raised-dot pattern as the reference cell.
3. The task does not require knowing Braille alphabet mappings.

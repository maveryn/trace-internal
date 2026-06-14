# `task_symbolic__braille_cell__raised_dot_count`

## Public Taxonomy
1. Domain: `symbolic`
2. Scene id: `braille_cell`
3. Scene: `notation`
4. Task id: `task_symbolic__braille_cell__raised_dot_count`

## Query Contract
1. Query metadata: `query_id`
2. Supported `query_id` values:
   - `raised_dot_count`
3. Prompts ask for the number of raised dots in the marked target Braille cell.
4. V1 answer support is `1..6`.
5. Internal variation includes visible distractor Braille cells and `clean_card|notebook_card|exam_scan` scene variants.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the number of filled raised dots in the marked target cell.
3. `annotation_gt.type = point_set`
4. Annotation contains one center point for every raised dot in the marked target cell.
5. Empty dot guides, distractor cells, target-cell bboxes, labels, and panel chrome are not prompt-facing annotation.

## Trace Contract
1. `execution_trace.braille_metadata.target_cell_id` records the marked target cell.
2. `execution_trace.braille_metadata.target_raised_positions` records the target cell's Braille dot positions.
3. `execution_trace.annotation_dot_ids` records the raised dot ids used for point projection.
4. `render_map.dot_centers_px` exposes all dot centers after final layout.
5. `render_map.raised_dot_centers_px` exposes only filled raised-dot centers.

## Prompt Contract
1. Bundle: `symbolic_v0`
2. Scene key: `braille_cell`
3. Task key: `braille_raised_dot_count`
4. Query key: `raised_dot_count`
5. Prompt wording must ask for raised or filled dots in the marked target cell. It must not require literary Braille letter knowledge.

## Determinism + Constraints
1. Deterministic generation and rendering from `instance_seed`.
2. Unique-answer policy: the target cell's raised-dot pattern is sampled from the requested answer count.
3. The task never counts faint empty-dot guides.

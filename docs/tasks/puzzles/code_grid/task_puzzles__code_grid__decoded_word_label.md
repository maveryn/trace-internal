# `task_puzzles__code_grid__decoded_word_label`

## Program Contract
`decode_word(grid_letters, coordinate_sequence); scene=code_grid; scope=decoded_word_label`

The scene shows a row-letter and column-number code grid. The prompt provides a
coordinate sequence, either compact or spaced as trace metadata. The task reads
the visible cell letters in that coordinate order and returns the decoded word.

## Answer And Annotation
1. `answer_gt.type = string`
2. `answer_gt.value` is the decoded uppercase word.
3. `annotation_gt.type = bbox_sequence`
4. Annotation schema: `bbox_sequence`
5. Annotation is the ordered sequence of grid-cell bounding boxes in coordinate
   decode order.
6. `scalar_annotation_checked = true`; this task has multiple ordered witnesses.

## Query Contract
1. Public `query_id`: `single`
2. Internal generation metadata may vary `coordinate_format = compact|spaced`.
3. Coordinate format does not change the answer schema, annotation schema, or
   reasoning program.

## Prompt Contract
1. Bundle: `puzzles_code_grid_v1`
2. Scene key: `code_grid`
3. Task key: `decoded_word_label_query`
4. Prompt query key: `decoded_word_label`

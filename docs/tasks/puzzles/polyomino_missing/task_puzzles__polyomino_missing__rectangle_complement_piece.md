# `task_puzzles__polyomino_missing__rectangle_complement_piece`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `polyomino_missing`
3. Source scene package: `polyomino_missing`
4. Task id: `task_puzzles__polyomino_missing__rectangle_complement_piece`

## Query Contract
1. Supported `query_id`: `exact_orientation`, `rotation_reflection_allowed`
2. Internal question format: `rectangle_complement_piece`
3. Prompt asks for the labeled polyomino option that completes a rectangular target by filling the black missing region.
4. Query semantics:
   - `exact_orientation`: the option must fit exactly as shown; do not rotate or reflect.
   - `rotation_reflection_allowed`: the option may be rotated or reflected before placement.
5. Internal variation:
   - `scene_variant`: `polyomino_strip|polyomino_card|polyomino_outline`
   - option labels: `A..E` or `A..F`
   - rectangle size, cutout shape, option order, option count, scene treatment, and style are generation/render metadata.

## Program Contract
`select_label(polyomino_option, rule=completes_rectangle_under_prompted_transform_policy); scene=polyomino_missing; scope=rectangle_complement_piece`

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the capital-letter label on the correct option panel.
3. `annotation_gt.type = bbox_map`
4. Annotation schema: `bbox_map`
5. Annotation contains exactly two keys:
   - `selected_option`: bbox around the correct option panel.
   - `missing_region`: bbox around the black missing region in the rectangle.
6. `scalar_annotation_checked = true`; scalar annotation is not used because the selected option and target gap are two distinct witness roles.

## Trace Contract
1. `scene_ir.entities` includes target cells, rectangle cells, the black missing-region cells, and one option panel entity per visible option.
2. `render_map.item_bboxes_px` contains the correct option panel id and `missing_region`, which are projected into `annotation_gt`.
3. `execution_trace.matching_policy` equals the public query branch and records whether rotation/reflection matching is allowed.
4. `execution_trace.option_specs` records each option's visible label, cells, panel id, `is_correct`, and `matches_under_policy`.
5. `execution_trace.variant_payload` records the full target cells, remaining cells, missing cells, cutout cells, target dimensions, option count, and correct option transform.

## Prompt Contract
1. Bundle: `puzzles_polyomino_missing_v1`
2. Scene key: `polyomino_missing`
3. Task key: `rectangle_complement_piece_query`
4. Query keys: `exact_orientation`, `rotation_reflection_allowed`
5. Prompt wording must state whether rotation/reflection is allowed for the option piece before selecting the answer.

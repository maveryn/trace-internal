# `task_puzzles_spatial_cube_removal_count`

## 1) Identity
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles_spatial_cube_removal_count`
4. Objective: answer the exact integer count of cubes that were taken from an original block structure to produce the remaining block structure.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `cube_removal_count`
2. Supported `scene_variant` values:
   - `stack_strip`
   - `stack_card`
   - `stack_outline`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one isometric block-comparison puzzle per image,
   - the left side shows the original block structure and the right side shows the remaining structure,
   - both structures use the same fixed viewpoint and the same rendering scale,
   - only visible cube faces are rendered; the removed cubes are implicit,
   - a caption and transition arrow make the left-to-right comparison explicit,
   - the prompt asks for the number of cubes taken away from the original block,
   - the answer is that removal count as an integer.
6. Generation guarantees:
   - footprint width and depth default to `2..4`,
   - original maximum stack height defaults to `2..5`,
   - total original cubes are capped by config so the structures remain readable,
   - removal count defaults to `1..5`,
   - every accepted scene keeps both structures non-empty and leaves at least one cube in every remaining occupied column,
   - the remaining structure is derived exactly from the original structure by removing whole top cubes from one or more columns.

## 3) Prompt contract
1. Bundle: `puzzles_spatial_v1`
2. `task_family_key`: `spatial_cube_removal_puzzle`
3. `task_key`: `cube_removal_count_query`
4. `task_variant_key`: `cube_removal_count`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/puzzles/spatial.yaml`,
   - deterministic bundle selection from `prompts/puzzles/spatial/puzzles_spatial_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the integer removal count; prompt-facing evidence is the ordered pair of visible structure bboxes `[original block on the left, remaining block on the right]`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly two `bbox_set` items:
   - first bbox: the original block on the left,
   - second bbox: the remaining block on the right.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - two `puzzle_block_structure` entities,
   - two `puzzle_block_caption` entities,
   - one `puzzle_block_arrow` entity,
   - one `puzzle_block_face` entity for each visible rendered face.
4. `render_map` includes:
   - `scene_bbox_px`
   - `original_structure_bbox_px`
   - `remaining_structure_bbox_px`
   - `structure_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `original_height_rows`
   - `remaining_height_rows`
   - `row_count`
   - `row_count_range`
   - `col_count`
   - `col_count_range`
   - `original_max_height`
   - `original_max_height_range`
   - `original_total_cubes`
   - `remaining_total_cubes`
   - `total_cubes_max`
   - `removal_count`
   - `removal_count_range`
   - `changed_column_count`
   - `original_cube_records`
   - `remaining_cube_records`
   - `removed_cube_records`
   - `original_structure_bbox_id`
   - `remaining_structure_bbox_id`
   - `supporting_structure_ids`
   - `solver_trace`
6. Prompt-facing evidence is projected from the ordered structure ids; individual removed cubes are not given fake image-space bboxes because they do not appear in the render.

## 5) Visual policy
1. Background and post-image noise use the merged puzzles-domain visual defaults from `configs/domains/puzzles/base.yaml`.
2. V1 cube-removal scenes use clean light backgrounds only.
3. Scene variants change outer panel chrome and outline treatment while preserving the same fixed isometric comparison grammar.
4. Both structures should occupy enough area to keep the cube faces readable without zooming.
5. Prompt-facing evidence should align to the two visible structure silhouettes rather than to any inferred missing region.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated original/remaining structure pair.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded ordered structure-id projection, not OCR or inferred missing-cube geometry from pixels.

# `task_physics_optics_ray_trace`

## 1) Identity
1. Domain: `physics`
2. Task group: `optics`
3. Task id: `task_physics_optics_ray_trace`
4. Objective: infer one hidden ray path from an initial direction plus diagonal mirrors, then answer one count question.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `single_mirror`
   - `double_mirror`
   - `triple_mirror`
   - `quad_mirror`
2. Supported `query_variant` / emitted `task_variant` values:
   - `bounce_count`
   - `target_hit_count`
3. Compatibility:
   - `single_mirror|double_mirror|triple_mirror` support `target_hit_count`
   - `quad_mirror` supports both query variants
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `graph_point_set`
6. Scene contract:
   - the image shows one square graph-paper board with one initial ray-direction arrow entering from the left,
   - diagonal mirrors sit in board cells,
   - `target_hit_count` scenes also show unlabeled target points as large dots on the board,
   - the full ray path is **not** drawn in the prompt image; it is implied by the initial direction plus the mirrors,
   - one non-semantic `accent_color_name` axis may recolor the board and mirror styling while the implied-ray semantics stay fixed.
7. Query contract:
   - `bounce_count` asks how many mirror reflections happen before the implied ray exits the board,
   - `target_hit_count` asks how many target points the implied ray touches before exit.
8. Answer policy:
   - all answers are non-negative integers,
   - answers are sampled from explicit scene/query supports and realized exactly by construction.

## 3) Prompt contract
1. Bundle: `physics_optics_v1`
2. `task_family_key`: `mirror_ray_diagram`
3. `task_key`: `ray_trace_query`
4. `task_variant_key`: `bounce_count|target_hit_count`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/physics/optics.yaml`
   - deterministic bundle selection from `prompts/physics/optics/physics_optics_v1.json`
   - prompt JSON examples are generated in task code from the active `graph_point_set` schema
7. Modes: `answer_only`, `answer_and_evidence`

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `graph_point_set`:
   - bounce-point coordinates for `bounce_count`
   - hit target-point coordinates for `target_hit_count`
2. `scene_ir.entities` stores:
   - one `physics_optics_source_direction` entity,
   - one `physics_optics_mirror` entity per mirror cell,
   - one `physics_optics_target_point` entity per shown target point,
   - one `physics_optics_bounce_point` entity per realized reflection point
3. `render_map` includes:
   - `board_bbox_px`
   - `graph_origin_px`
   - `graph_spacing_px`
   - `source_direction_px`
   - `mirror_bboxes_px`
   - `target_point_map_px`
   - `bounce_point_map_px`
   - hidden `ray_polyline_px` for trace/debug review
4. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `accent_color_name`
   - `target_answer`
   - `target_answer_support`
   - `source_row`
   - one spec per mirror (`mirror_id`, `col`, `row`, `orientation`, `hit`)
   - one spec per target (`target_id`, `col`, `row`, `graph_point`, `hit`)
   - `path_cells`
   - `bounce_cells`
   - `evidence_graph_points`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged physics-domain visual defaults from `configs/domains/physics/base.yaml`.
2. The prompt image should show only the initial ray direction, not the solved full path.
3. Use a graph-paper presentation with visible coordinate labels so graph-point evidence is grounded on the shown board.
4. `bounce_count` should not draw separate bounce-marker circles in the prompt image.
5. `target_hit_count` should render target points as large unlabeled dots rather than numbered targets.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, `accent_color_name`, and `target_answer` are sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized hidden ray trace.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_answer` outside the active scene/query support,
   - failure to build a non-looping implied path that realizes the requested answer,
   - failure to place off-path mirrors or target points cleanly.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `path_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_physics_optics_ray_trace_contracts.py`
3. Config tests: `tests/test_physics_optics_ray_trace_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`

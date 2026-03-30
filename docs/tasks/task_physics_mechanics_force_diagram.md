# `task_physics_mechanics_force_diagram`

## 1) Identity
1. Domain: `physics`
2. Task group: `mechanics`
3. Task id: `task_physics_mechanics_force_diagram`
4. Objective: answer one simple axis-aligned force-diagram question from the shown force arrows using lightweight integer arithmetic.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `free_body_box`
   - `textured_block`
2. Supported `query_variant` / emitted `task_variant` values:
   - `net_horizontal_force`
   - `net_vertical_force`
   - `balancing_force_horizontal`
   - `balancing_force_vertical`
3. Compatibility:
   - `free_body_box` supports all four query variants,
   - `textured_block` supports all four query variants.
4. `answer_gt.type`: `integer`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - all shown force arrows are axis-aligned and display plain integer magnitudes in the image,
   - the image contains one main block, with `textured_block` adding a subtle cross-hatch texture,
   - the block is sampled near-square with a bounded `1:2` / `2:1` aspect ratio and a slightly taller default footprint than the initial draft,
   - `balancing_force_*` variants add one visible red placeholder arrow marked with `?` in the requested direction, aligned to the same outside lane system as the shown arrows so it reads as one more force arrow on that side of the block.
7. Query contract:
   - `net_horizontal_force` asks for the magnitude of the object's net horizontal force,
   - `net_vertical_force` asks for the magnitude of the object's net vertical force,
   - `balancing_force_horizontal` asks for the force magnitude needed in the marked horizontal direction to make the net horizontal force zero,
   - `balancing_force_vertical` asks for the force magnitude needed in the marked vertical direction to make the net vertical force zero.
8. Answer policy:
   - answers are non-negative integers,
   - net-force variants allow `0`,
   - balancing variants use positive support only.

## 3) Prompt contract
1. Bundle: `physics_mechanics_v1`
2. `task_family_key`: `axis_aligned_force_diagram`
3. `task_key`: `force_diagram_query`
4. `task_variant_key`: `net_horizontal_force|net_vertical_force|balancing_force_horizontal|balancing_force_vertical`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `marked_direction_label` for both balancing variants
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/physics/mechanics.yaml`,
   - deterministic bundle selection from `prompts/physics/mechanics/physics_mechanics_v1.json`,
   - prompt JSON examples are generated in task code from the active `bbox_set` schema, using one-box examples for balancing variants and multi-arrow examples for net-force variants.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt wording is magnitude-only (no signed-force convention) and balancing variants explicitly mention the marked direction.

## 4) Evidence + trace contract
1. Prompt-facing evidence is an unordered `bbox_set` over exactly the shown force arrows that contribute along the queried axis.
2. For `balancing_force_*`, prompt-facing evidence is the single bbox of the marked `?` placeholder arrow rather than the supporting shown arrows.
3. Supporting arrows on the queried axis still remain recorded in trace as the reasoning witness set for balancing variants.
4. `scene_ir.entities` stores:
   - one `physics_object`,
   - one `physics_force_arrow` entity per shown force arrow,
   - zero or one `physics_missing_force_marker`.
5. `render_map` includes:
   - `object_bbox_px`,
   - `arrow_bboxes_px`,
   - `arrow_label_bboxes_px`,
   - `relevant_arrow_ids`,
   - `evidence_entity_ids`,
   - optional `balancing_force_marker_bbox_px`.
6. `execution_trace` records:
   - `scene_variant`
   - `query_variant`
   - `query_axis`
   - `target_force`
   - `dominant_direction`
   - optional `balancing_direction`
   - one spec per shown force arrow (`direction`, `axis`, `magnitude_n`, `relevant_to_query`, `role`)
   - `relevant_arrow_ids`
   - `evidence_entity_ids`

## 5) Visual policy
1. Background and post-image noise use the merged physics-domain visual defaults from `configs/domains/physics/base.yaml`.
2. Scene variants change only the mechanics scaffold around the same force-arithmetic contract.
3. Force labels should stay off the main object and off other arrows whenever the deterministic slot layout allows it.
4. Prompt-facing evidence should stay local to the queried target: queried-axis shown arrows for `net_*`, and the marked `?` arrow for `balancing_force_*`; do not widen it to the full object, surface, or texture fill.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `scene_variant`, `query_variant`, and `target_force` are each sampled through explicit supports/weights with deterministic balancing.
3. Answers and evidence come from the same finalized set of force arrows.
4. No semantic auto-relaxation.
5. Reject/resample conditions:
   - unsupported scene/query combinations,
   - explicit `target_force` outside the active support,
   - failure to construct bounded integer force partitions for the requested target.

## 7) Complexity + tests
1. Complexity definition/components: `visual_scan`, `force_reasoning`, `ambiguity`, `output_burden`
2. Determinism/build tests: `tests/test_physics_mechanics_force_diagram_contracts.py`
3. Config tests: `tests/test_physics_mechanics_force_diagram_task_group_config.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`

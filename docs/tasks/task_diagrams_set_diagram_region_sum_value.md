# `task_diagrams_set_diagram_region_sum_value`

## 1) Identity
1. Domain: `diagrams`
2. Task group: `set_diagram`
3. Task id: `task_diagrams_set_diagram_region_sum_value`
4. Objective: read one numeric `3`-set overlap diagram and return the integer sum of the digits in the queried set regions.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `sum_only_in_named_set`
   - `sum_in_named_set`
   - `sum_in_named_union`
   - `sum_in_named_intersection`
   - `sum_in_exactly_two_sets`
2. Supported `scene_variant` values:
   - `set_diagram`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one set diagram panel is shown on a light background,
   - the panel contains exactly `3` overlapping labeled sets `A`, `B`, and `C`,
   - all `7` visible regions are populated with one unique single-digit number each,
   - the prompt asks for one sum over explicit set semantics such as “only in Set A,” “in Set B,” “in Set A or Set C,” “in both Set A and Set B,” or “in exactly two sets,”
   - the answer is the integer sum of the contributing digits.
6. Generation guarantees:
   - exactly one single digit appears in each visible region,
   - all visible digits are unique within one diagram,
   - the prompt names the relevant sets explicitly whenever the query is not global,
   - the contributing regions are deterministic from the prompt semantics and the answer is unique by construction.

## 3) Prompt contract
1. Bundle: `diagrams_set_diagram_v1`
2. `task_family_key`: `numeric_set_overlap_diagram`
3. `task_key`: `region_sum_query`
4. `task_variant_key`: one of `sum_only_in_named_set|sum_in_named_set|sum_in_named_union|sum_in_named_intersection|sum_in_exactly_two_sets`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/diagrams/set_diagram.yaml`,
   - deterministic bundle selection from `prompts/diagrams/set_diagram/diagrams_set_diagram_v1.json`,
   - task-local JSON examples keyed by the active numeric set-sum variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the integer sum; prompt-facing evidence is the ordered list of contributing digit bboxes.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` with one box per contributing digit:
   - ordered from top to bottom and then left to right.
2. `scene_ir.entities` stores:
   - `diagram_panel`
   - `diagram_title`
   - `diagram_set_region`
   - `diagram_set_label`
   - `diagram_set_number`
3. `render_map` includes:
   - `panel_bbox_px`
   - `title_bbox_px`
   - `region_bboxes_px`
   - `set_label_bboxes_px`
   - `number_bboxes_px`
   - `number_slot_bboxes_px`
4. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `scene_title`
   - `question_text`
   - `set_ids`
   - `set_count`
   - `region_ids`
   - `number_count`
   - `query_focus`
   - `target_sets`
   - `contributing_region_ids`
   - `answer_value`
   - `region_number_map`
   - `number_specs`
   - `supporting_number_bbox_ids`
   - `set_fill_rgb_map`
   - `min_set_color_distance`
   - `color_distance_space`
5. `witness_symbolic` stores the ordered contributing number-bbox ids, while `projected_evidence` stores the same ordered digit bboxes.

## 5) Visual policy
1. Background and post-image noise use the merged diagrams-domain visual defaults from `configs/domains/diagrams/base.yaml`.
2. V1 numeric set diagrams stay schematic and uncluttered:
   - exactly `3` sets only,
   - one large single-digit number per region,
   - no number pills or item cards,
   - short set labels outside the circles.
3. The active set palette must be sampled or validated in Lab space with minimum separation `ΔE*ab >= 50`, and the overlap regions should appear as blended set fills through alpha compositing.
4. Layout reasoning stays local:
   - the prompt names the requested set logic explicitly,
   - the answer is one computed integer,
   - evidence stays on the contributing digits themselves.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact contributing digit set.
4. No semantic auto-relaxation.
5. If a sampled layout cannot keep the digits or set labels separated clearly, reject and resample instead of relaxing the geometry.

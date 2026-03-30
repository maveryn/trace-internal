# `task_diagrams_schematic_callout_target_label`

## 1) Identity
1. Domain: `diagrams`
2. Task group: `schematic`
3. Task id: `task_diagrams_schematic_callout_target_label`
4. Objective: read one annotated schematic and return the visible callout label that points to the queried part.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `callout_for_named_part`
   - `callout_for_highlighted_part`
2. Supported `scene_variant` values:
   - `annotated_schematic`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one annotated schematic panel is shown on a light background,
   - the panel contains a central chassis with `5..7` labeled parts and one external callout circle per part,
   - each callout circle has one unique visible letter and a leader line that points to exactly one part,
   - the prompt either names one part directly or asks about the highlighted part,
   - the answer is the exact visible callout letter for that part.
6. Generation guarantees:
   - part labels are short and unique within one schematic,
   - callout letters are unique within one schematic,
   - exactly one target part is queried,
   - the target callout letter is unique by construction.

## 3) Prompt contract
1. Bundle: `diagrams_schematic_v1`
2. `task_family_key`: `annotated_schematic_diagram`
3. `task_key`: `callout_target_query`
4. `task_variant_key`: one of `callout_for_named_part|callout_for_highlighted_part`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/diagrams/schematic.yaml`,
   - deterministic bundle selection from `prompts/diagrams/schematic/diagrams_schematic_v1.json`,
   - task-local JSON examples keyed by the active schematic query variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the callout letter; prompt-facing evidence is the single bbox of the queried target part.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` with exactly one box:
   - the bbox of the target part itself.
2. `scene_ir.entities` stores:
   - `diagram_panel`
   - `diagram_title`
   - `diagram_schematic_chassis`
   - `diagram_schematic_bus`
   - `diagram_callout_leader`
   - `diagram_schematic_part`
   - `diagram_schematic_part_label`
   - `diagram_schematic_callout`
   - `diagram_schematic_callout_label`
3. `render_map` includes:
   - `panel_bbox_px`
   - `title_bbox_px`
   - `chassis_bbox_px`
   - `part_bboxes_px`
   - `part_label_bboxes_px`
   - `callout_bboxes_px`
   - `callout_label_bboxes_px`
   - `leader_bboxes_px`
4. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `scene_title`
   - `question_text`
   - `part_count`
   - `part_specs`
   - `query_focus`
   - `query_part_label`
   - `highlight_part_id`
   - `answer_part_id`
   - `answer_part_label`
   - `answer_part_bbox_id`
   - `answer_callout_bbox_id`
   - `answer_callout_label`
   - `supporting_part_bbox_ids`
5. `witness_symbolic` stores the single supporting part-bbox id, while `projected_evidence` stores the same one-box `bbox_set`.

## 5) Visual policy
1. Background and post-image noise use the merged diagrams-domain visual defaults from `configs/domains/diagrams/base.yaml`.
2. V1 annotated schematics stay diagram-native and uncluttered:
   - one central schematic chassis,
   - short visible part labels,
   - one leader line and one callout circle per part,
   - no document-like paragraphs, legends, or tables.
3. Layout reasoning stays local:
   - the model must locate the queried part and follow its leader line to the matching callout,
   - the answer is the callout label,
   - evidence stays on the actual target part rather than the answer badge.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact target-part execution trace.
4. No semantic auto-relaxation.
5. If a sampled layout cannot keep parts, callout circles, or leader lines separated clearly, reject and resample instead of relaxing the geometry.

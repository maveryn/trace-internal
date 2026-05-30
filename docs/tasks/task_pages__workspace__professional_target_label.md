# `task_pages__workspace__professional_target_label`

## Contract
1. Domain: `pages`
2. Task group: `relation`
3. Task id: `task_pages__workspace__professional_target_label`
4. Objective: identify the labeled target control matching a visible cue, context row, and coded header in a professional application workspace.
5. Answer type: `option_letter`
6. Evidence type: role-keyed `keyed_bbox_map`

## Variants
1. `toolbar_palette_control_label`
2. `property_panel_control_label`
3. `canvas_workspace_control_label`
4. `code_workspace_control_label`
5. `file_dialog_control_label`

## Scene
1. The screen renders a professional desktop application workspace with a shuffled cue guide, context rows, coded headers, and labeled controls.
2. The prompt references a cue phrase; the visible guide maps that cue to a header code.
3. Active context rows are sampled from `3..5`, with five coded headers.
4. `scene_variant`: `office_document|creative_workspace|developer_ide|cad_workspace|scientific_plotter|os_file_manager`
5. `style_variant`: `standard|compact|contrast|cool|warm|sage`

## Answer And Evidence
1. Answer is the candidate label of the target control.
2. Evidence contains four query-specific role-keyed boxes: the visible cue card, the matched context row, the coded header, and the target control.
3. Role keys are derived from the query branch, for example `tool_cue_card`, `tool_context_row`, `tool_code_header`, `target_toolbar_palette_control`; `ide_cue_card`, `code_target_row`, `ide_code_header`, `target_code_workspace_control`; or `dialog_cue_card`, `dialog_location_row`, `dialog_code_header`, `target_file_dialog_control`.
4. Candidate-label badge bboxes are trace metadata only; prompt-facing evidence uses full support/control bboxes.

## Prompt
1. `prompt_bundle_id`: `pages_relation_v0`
2. `scene_key`: `gui_professional_target_controls`
3. `task_key`: `professional_target_query`
4. Both answer-only and answer-and-evidence modes provide task-specific JSON examples.

## Determinism
1. Generation is deterministic for `instance_seed` plus params.
2. seeded sampling balances query ids, scene variants, style variants, target controls, and answer-label support.
3. The answer and evidence come from the same symbolic control/support trace.

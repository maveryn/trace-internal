# `task_pages__command_matrix__command_intent_target_label`

## Contract
1. Domain: `pages`
2. Task group: `relation`
3. Task id: `task_pages__command_matrix__command_intent_target_label`
4. Objective: identify the labeled command cell matching referenced intent/object cues, a shuffled intent guide, object row cue chips, and coded action header.
5. Answer type: `option_letter`
6. Evidence type: `keyed_bbox_map`

## Variants
1. `query_id=command_intent_target_label`: prompt gives an intent cue and visible object row label.
2. `query_id=dual_guide_command_label`: prompt gives an intent cue and an object cue; the object cue must be mapped through a second visible guide before selecting the row.
3. `intent_category` is sampled as `create_insert|select_choose|view_toggle|edit_transform|format_style`.
4. The intent category controls which guide cue/action header family is queried.

## Scene
1. The screen renders one desktop application window with a command matrix, an intent guide, and for `dual_guide_command_label` object cue chips inside the row headers.
2. The matrix uses `5` object rows and `5` action columns for `25` visible targetable controls.
3. Object row labels, intent-guide cards, and coded action headers are visible support regions.
4. Each intent-guide card maps an intent cue phrase to a short header code; guide cards are shuffled independently from the matrix column order.
5. Each object cue chip maps an object cue phrase to a row label in the dual-guide variant.
6. Matching guide cards and coded action headers share a subtle accent color in addition to the printed key.
7. Matrix action headers show the header code, not the natural-language intent phrase; the prompt references the cue phrase.
8. Command controls use a visible action symbol and a visible candidate label badge.
9. `scene_variant`: `office_document|creative_workspace|developer_ide|cad_workspace|scientific_plotter|os_file_manager`
10. `style_variant`: `standard|compact|contrast|cool|warm|sage`

## Answer And Evidence
1. Answer is the candidate label of the command cell at the requested object/action intersection.
2. Evidence for `command_intent_target_label` is a keyed bbox map with keys `action_cue_guide`, `object_row`, `action_code_header`, and `target_command_cell`.
3. Evidence for `dual_guide_command_label` is a keyed bbox map with keys `action_cue_guide`, `object_cue_guide`, `object_row`, `action_code_header`, and `target_command_cell`.
4. Candidate-label badge bboxes are trace metadata only; prompt-facing evidence uses full support/control bboxes.
5. Prompt text uses short cue phrases, so the visible row/header must be found through the guide-card mappings.

## Prompt
1. `prompt_bundle_id`: `pages_relation_v0`
2. `scene_key`: `gui_command_intents`
3. `task_key`: `command_intent_query`
4. Both answer-only and answer-and-evidence modes provide task-specific JSON examples.

## Determinism
1. Generation is deterministic for `instance_seed` plus params.
2. seeded sampling balances query ids, scene variants, style variants, target controls, and answer-label support.
3. seeded sampling also balances `intent_category` inside each public query id.
4. The answer and evidence come from the same symbolic control/support trace.

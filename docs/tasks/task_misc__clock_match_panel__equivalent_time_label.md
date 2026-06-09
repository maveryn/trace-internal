# `task_misc__clock_match_panel__equivalent_time_label`

## 1) Identity
1. Domain: `misc`
2. Scene id: `clock_match_panel`
3. Source task group: `clock`
4. Task id: `task_misc__clock_match_panel__equivalent_time_label`
5. Objective: match one analog or digital reference time to the equivalent visual option in the other representation.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. Supported `query_id` values:
   - `analog_reference_digital_options`
   - `digital_reference_analog_options`
3. Supported non-semantic visual axes:
   - `scene_variant`: `classic|minimal|outline`
   - `style_variant`: `studio|accented|marker`
   - `accent_color_name`: sampled from the shared clock named-color palette
   - `digital_display_palette`: high-contrast digital display case/screen/text palettes
4. `answer_gt.type`: `string`
5. `annotation_gt.type`: `keyed_bbox_map`
6. Scene contract:
   - one top reference visual labeled `Reference`,
   - six fixed visual option cards labeled `A..F`,
   - `analog_reference_digital_options` shows an analog reference clock and digital-display options,
   - `digital_reference_analog_options` shows a digital reference display and analog-clock options,
   - all option times are distinct,
   - the correct option is unique by construction,
   - shown minutes stay on a 5-minute grid in v0.

## 3) Prompt Contract
1. Bundle: `misc_clock_v0`
2. `scene_key`: `clock_match_panel`
3. `task_key`: `clock_match_query`
4. Query keys match the active `query_id`.
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_annotation`
7. Prompt-facing answer is always the single matching option label.

## 4) Annotation + Trace Contract
1. Prompt-facing annotation is role-keyed:
   - `reference`: bbox around the reference clock/display visual,
   - `correct_option`: bbox around the matching option visual, excluding the option label marker.
2. `projected_annotation` includes `keyed_bbox_map` and `pixel_keyed_bbox_map`.
3. `scene_ir.entities` stores reference and option clock/display entities.
4. `render_map` includes:
   - `reference_bbox_px`
   - `option_visual_bboxes_px`
   - `option_card_bboxes_px`
   - `correct_option_bbox_px`
   - `correct_label`
5. `execution_trace` records:
   - active query id and representations,
   - target time,
   - option labels and option times,
   - correct label,
   - active support ranges and visual axes.

## 5) Visual Policy
1. Option labels are fixed in row-major `A..F` positions.
2. Option annotation marks the option visual, not the label badge.
3. Digital displays use one sampled non-semantic palette recorded in `render_spec.clock_style.digital_display_palette` and `digital_display_colors_rgb`.
4. All clock numerals, option labels, and digital displays use one deterministic readout font family recorded in `render_spec.clock_style.font`.
5. Post-image noise uses the standard match-panel default `apply_prob=0.4`.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Query direction, visual axes, target time, and answer label are sampled internally.
3. Answers and annotation come from the finalized rendered reference/options.
4. No semantic auto-relaxation.
5. Reject conditions:
   - empty feasible time support after hand-gap filtering,
   - too few distractor times under the configured option-gap threshold,
   - duplicate or non-six option label support.

## 7) Complexity + Tests
1. Complexity components: `time_reading`, `visual_scan`, `ambiguity`, `clutter`
2. Behavior/trace/prompt tests: `tests/test_misc_clock_match_panel_tasks.py`
3. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_misc_core_task_group_config.py`

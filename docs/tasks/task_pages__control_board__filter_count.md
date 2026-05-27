# `task_pages__control_board__filter_count`

## Contract
1. Domain: `pages`
2. Task group: `counting`
3. Task id: `task_pages__control_board__filter_count`
4. Objective: count controls or table rows matching a visible GUI filter condition.

## Variants
1. `disabled_controls_in_group_count`: count disabled controls in the named group.
2. `selected_enabled_controls_in_group_count`: count controls that are both selected and enabled in the named group.
3. `selected_rows_with_status_count`: count selected rows whose status matches a quoted target status.
4. `enabled_action_for_type_count`: count rows with a quoted Type value and an enabled quoted action button.
5. `value_threshold_in_group_count`: count rows in a quoted section whose Size is at least the stated MB threshold.

## Scene
1. Control variants render a grouped desktop control board.
2. Table variants render a sectioned GUI data table.
3. `scene_variant`: `office_document|creative_workspace|developer_ide|cad_workspace|scientific_plotter|os_file_manager`
4. `style_variant`: `standard|compact|contrast|cool|warm|sage`

## Answer And Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set`
3. Evidence contains the unordered set of full control or full row bboxes for every counted item.
4. Candidate-label badge bboxes and table cell bboxes are trace metadata only; prompt-facing evidence uses full item bboxes.

## Prompt
1. `prompt_bundle_id`: `pages_counting_v0`
2. Control variants use `scene_key=gui_control_board` and `task_key=control_filter_count_query`.
3. Table variants use `scene_key=gui_table` and `task_key=table_row_filter_count_query`.
4. Both answer-only and answer-and-evidence modes provide task-specific JSON examples.

## Determinism
1. Generation is deterministic for `instance_seed` plus params.
2. seeded sampling balances query variants, scene variants, style variants, and answer support.
3. No semantic constraints are auto-relaxed to force acceptance.

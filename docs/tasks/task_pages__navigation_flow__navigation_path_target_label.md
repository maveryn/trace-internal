# `task_pages__navigation_flow__navigation_path_target_label`

## Contract
1. Domain: `pages`
2. Task group: `relation`
3. Task id: `task_pages__navigation_flow__navigation_path_target_label`
4. Objective: identify the labeled target control reached by a visible GUI navigation path.
5. Answer type: `option_letter`
6. Evidence type: role-keyed `keyed_bbox_map`

## Variants
1. `menu_path_target_label`: follow a visible menu root, submenu, and menu group to a final command.
2. `sidebar_tree_target_label`: follow a visible sidebar section and group to a final item.
3. `ribbon_group_command_label`: follow a visible ribbon tab and group to a final command.

## Scene
1. The screen renders one desktop application window with one variant-specific navigation workspace.
2. Active menu scenes use `2` menu roots, `2` submenus per root, `2` groups per submenu, and sample `3..4` commands per group, constrained to at most `26` labeled controls so candidate labels stay unique.
3. Sidebar scenes use `3` sections, `2` groups per section, and `2` items per group for `12` candidate controls.
4. Active ribbon scenes sample `3..5` tabs, `2..3` groups per tab, and `3..4` commands per group, constrained to at most `26` labeled controls.
5. Menu and ribbon command controls render compact command symbols with a visible legend.
6. Sidebar item controls render compact item symbols with a visible item legend; item names are reused across section/group contexts.
7. Every candidate target control has a visible candidate label badge.
8. `scene_variant`: `office_document|creative_workspace|developer_ide|cad_workspace|scientific_plotter|os_file_manager`
9. `style_variant`: `standard|compact|contrast|cool|warm|sage`

## Answer And Evidence
1. Answer is the candidate label of the final target control.
2. Evidence contains three role-keyed boxes using query-specific visible roles:
   - `menu_path_target_label`: `menu_root`, `menu_group`, and `target_command`
   - `sidebar_tree_target_label`: `sidebar_section`, `sidebar_group`, and `target_item`
   - `ribbon_group_command_label`: `ribbon_tab`, `ribbon_group`, and `target_command`
3. Candidate-label badge bboxes are trace metadata only; prompt-facing evidence uses full support/control bboxes.

## Prompt
1. `prompt_bundle_id`: `pages_relation_v0`
2. `scene_key`: `gui_navigation_paths`
3. `task_key`: `navigation_path_query`
4. Both answer-only and answer-and-evidence modes provide task-specific JSON examples.

## Determinism
1. Generation is deterministic for `instance_seed` plus params.
2. seeded sampling balances query ids, scene variants, style variants, and answer-label support.
3. The answer and evidence come from the same symbolic control/support trace.

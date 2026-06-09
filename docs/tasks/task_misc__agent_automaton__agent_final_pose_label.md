# `task_misc__agent_automaton__agent_final_pose_label`

## Summary
1. Domain: `misc`
2. Task group: `automaton`
3. Task id: `task_misc__agent_automaton__agent_final_pose_label`
4. Scene id: `agent_automaton`
5. Goal: simulate a turning agent automaton and choose the option showing its final cell and direction.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `binary_rule_final_pose|three_state_rule_final_pose`
3. Answer type: `option_letter`
4. Annotation type: `keyed_bbox_map`
5. Annotation target: role-keyed bboxes for `start_marker` and `selected_option`
6. Scene variants: `clean_grid|lab_panel|notebook_grid`
7. Render metadata records the shared panel style, sampled readout font, and scene-local `agent_board.board_style`.

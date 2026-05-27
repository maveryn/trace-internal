# `task_puzzles__agent_automaton__agent_final_pose_label`

## Summary
1. Domain: `puzzles`
2. Task group: `automaton`
3. Task id: `task_puzzles__agent_automaton__agent_final_pose_label`
4. Scene id: `agent_automaton`
5. Goal: simulate a turning agent automaton and choose the option showing its final cell and direction.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `binary_rule_final_pose|three_state_rule_final_pose`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence target: starting-agent bbox followed by selected option bbox
6. Scene variants: `clean_grid|lab_panel|notebook_grid`

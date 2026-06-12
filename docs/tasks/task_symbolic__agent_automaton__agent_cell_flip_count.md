# `task_symbolic__agent_automaton__agent_cell_flip_count`

## Summary
1. Domain: `symbolic`
2. Scene: `automaton`
3. Task id: `task_symbolic__agent_automaton__agent_cell_flip_count`
4. Scene id: `agent_automaton`
5. Goal: simulate a turning agent automaton and count updates inside a marked region.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `marked_region_flip_count`
3. Rule branch: `rule_variant=binary_rule|three_state_rule`
4. Answer type: `integer`
5. Annotation type: `bbox_set`
6. Annotation target: marked-region bbox
7. Scene variants: `clean_grid|lab_panel|notebook_grid`
8. Render metadata records the shared panel style, sampled readout font, and scene-local `agent_board.board_style`.

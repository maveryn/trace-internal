# `task_puzzles__rubiks_net__rubiks_move_result_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__rubiks_net__rubiks_move_result_label`
4. Scene id: `rubiks_net`
5. Goal: choose the labeled candidate cube net that results from applying a Rubik-style move sequence.

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `one_move_result_label|two_move_result_label|inverse_sequence_result_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence targets: exactly one bbox for the selected candidate net option panel
6. Scene variants: `classic_net|paper_net|cool_net`
7. Trace contract: the start state, final state, move sequence, optional base sequence for inverse queries, candidate states, and answer state signature are recorded in metadata.

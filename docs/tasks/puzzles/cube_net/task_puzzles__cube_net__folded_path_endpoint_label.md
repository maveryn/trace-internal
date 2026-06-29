# `task_puzzles__cube_net__folded_path_endpoint_label`

## Summary
1. Domain: `puzzles`
2. Scene id: `cube_net`
3. Task id: `task_puzzles__cube_net__folded_path_endpoint_label`
4. Objective contract: choose the endpoint face after following folded-edge moves.

## Program Contract
`select_option(folded_cube_path.endpoint_face, path=edge_move_sequence); scene=cube_net; scope=folded_path_endpoint_label`

## Query Contract
1. `query_id=single`: fixed endpoint-selection program.
2. Move count, face labels, scene variant, and option order are generation/render axes, not query ids.

## Answer And Annotation
1. Answer type: `option_letter`
2. Annotation schema: `bbox_map`
3. Annotation keys: `start_face`, `move_instructions`, `selected_option`
4. Annotation boxes mark the start face, instruction panel, and selected endpoint option card.

## Implementation
1. Registered class: `trace.tasks.puzzles.cube_net.folded_path_endpoint_label.PuzzlesCubeFoldedPathEndpointLabelTask`
2. Prompt bundle: `prompts/puzzles/cube_net/puzzles_cube_net_v1.json`
3. Scene config: `configs/domains/puzzles/cube_net.yaml`

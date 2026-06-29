# `task_puzzles__cube_net__cube_rolling_result_label`

## Summary
1. Domain: `puzzles`
2. Scene id: `cube_net`
3. Task id: `task_puzzles__cube_net__cube_rolling_result_label`
4. Objective contract: choose the option matching the requested final cube face after rolling.

## Program Contract
`select_option(cube_roll.final_face, target_slot=top|front|right, path=visible_arrow_path); scene=cube_net; scope=cube_rolling_result_label`

## Query Contract
1. `query_id=final_top_face_label`: select the final top face.
2. `query_id=final_front_face_label`: select the final front face.
3. `query_id=final_right_face_label`: select the final right face.
4. Query ids are semantic target slots, not path length, grid size, style, or option layout.

## Answer And Annotation
1. Answer type: `option_letter`
2. Annotation schema: `bbox_map`
3. Annotation keys: `start_cube`, `roll_path`, `selected_option`
4. Annotation boxes mark the start-cube panel, roll-path panel, and selected option card.

## Implementation
1. Registered class: `trace.tasks.puzzles.cube_net.cube_rolling_result_label.PuzzlesCubeRollingResultLabelTask`
2. Prompt bundle: `prompts/puzzles/cube_net/puzzles_cube_net_v1.json`
3. Scene config: `configs/domains/puzzles/cube_net.yaml`

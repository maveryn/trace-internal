# `task_games__lane_runner__safe_path_label`

## Contract
1. Domain: `games`
2. Scene id: `lane_runner`
3. Public task id: `task_games__lane_runner__safe_path_label`
4. Supported `query_id` values: `single`
5. Annotation schema: `bbox`

## Program Contract
`select_unique(label(path) where no_hazard_collision(path, hazards)); scene=lane_runner; scope=safe_path_label`

1. The scene shows labeled candidate path cards.
2. Each card contains a two-lane track with hazard cells and one candidate path, using the same lane-grid scale as the shown-path lane-runner task.
3. Each path advances one row per step toward the finish.
4. The task asks which labeled path reaches the finish without entering any hazard cell.

## Answer And Annotation
1. `answer_gt.type`: `option_letter`.
2. `annotation_gt.type`: `bbox`.
3. Annotation is the bounding box around the selected path card.
4. The sampler uses only four-option or six-option sets and rejects instances unless exactly one displayed path avoids all hazards.

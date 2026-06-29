# `task_puzzles__cube_net__cube_net_face_relation_label`

## Summary
1. Domain: `puzzles`
2. Scene id: `cube_net`
3. Task id: `task_puzzles__cube_net__cube_net_face_relation_label`
4. Objective contract: choose the option matching a folded-cube face relation.

## Program Contract
`select_option(folded_cube_net.face_relation, relation=opposite|edge_neighbor, reference=marked_face); scene=cube_net; scope=cube_net_face_relation_label`

## Query Contract
1. `query_id=opposite_face_label`: choose the face opposite the marked face after folding.
2. `query_id=marked_edge_neighbor_face_label`: choose the face sharing the marked edge after folding.
3. Query ids are semantic relation operators, not style or layout variants.

## Answer And Annotation
1. Answer type: `option_letter`
2. Annotation schema: `bbox_map`
3. Annotation keys: `marked_face`, `selected_option`
4. Annotation boxes are image-pixel boxes for the marked reference face and selected option card.

## Implementation
1. Registered class: `trace.tasks.puzzles.cube_net.cube_net_face_relation_label.PuzzlesCubeNetFaceRelationLabelTask`
2. Prompt bundle: `prompts/puzzles/cube_net/puzzles_cube_net_v1.json`
3. Scene config: `configs/domains/puzzles/cube_net.yaml`

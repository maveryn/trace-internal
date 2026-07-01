# `task_games__rhythm__lane_note_score_value`

## Program Contract

Program: `sum(map(filter(notes, lane=target_lane), color_score(note.color_key))); scene=rhythm; scope=lane_note_score_value`

Candidate set: the visible game board, pieces, tokens, cards, tiles, marked state, legal-move cues, result panels, and labeled options inside the `lane_note_score_value` objective scope.
Operands: visible scene state and prompt-bound target operands named by the task contract.
Operation: evaluate `sum(map(filter(notes, lane=target_lane), color_score(note.color_key)))` over visible rhythm notes and the side score palette; generation enforces a unique final answer.
Output binding: `answer` uses the `integer` schema; generation binds a unique final answer.
Annotation witnesses: `annotation` uses the `bbox_set` schema for all scoring note objects in the target lane.
Query ids: `single`.

## Notes
- `target_lane` is prompt-bound by lane number.
- The side score palette maps note colors to integer score values.
- A long vertical note scores once.
- Annotation bboxes are all note objects in the specified lane that contribute to the score.
- Scalar annotation checked: true.

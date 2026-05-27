# `task_icons__named_field__reference_distance_rank_label`

Status: accepted after qwen25vl7b solve-rate calibration.

## Identity
- domain: `icons`
- scene_id: `named_field`
- task_group: `relation`
- task: `named_reference_distance_rank_label`
- module: `trace/tasks/icons/relation/named_reference_distance_rank_label.py`
- prompt bundle: `prompts/icons/relation/icons_relation_v0.json`

## Scene And Query
The task renders one panel labeled `Scene` with exactly one unique named
reference icon, six letter-labeled candidate icons (`A`..`F`), and `4..8`
unlabeled distractor icons. The reference is uniquely identified by its
prompt-named color and procedural shape, for example `red [#E63232] star`.

Supported query ids:
- `closest_to_named_reference_label`
- `second_closest_to_named_reference_label`
- `farthest_from_named_reference_label`

The six labeled candidates are the only answer options. Distractors are
unlabeled and are not included in the distance-rank candidate set.

## Answer Contract
- `answer_gt.type = option_letter`
- answer support is exactly `A|B|C|D|E|F`
- the answer is the label of the candidate at the requested center-to-center
  distance rank from the named reference icon

## Evidence Contract
- `evidence_gt.type = bbox_set`
- evidence contains one bbox for the named reference icon and one bbox for the
  selected labeled candidate icon
- candidate distance ranks are separated from adjacent ranks by the configured
  `distance_rank_margin_px`

## Trace Contract
- `scene_ir.entities` contains all reference, candidate, and distractor icons.
- Candidate entities include visible `label`, `distance_to_reference_px`, and
  `distance_rank`.
- `execution_trace.sorted_candidate_labels_by_distance` records the verifier
  order used to derive the answer.
- `projected_evidence.bbox_set` is derived from the same rendered reference and
  selected candidate bboxes.

## Prompt Contract
- `scene_key = named_reference_distance_relation`
- `task_key = relation_query`
- prompts ask which labeled icon is closest, second closest, or farthest from
  the unique named reference icon
- answer-only and answer+evidence modes both include contract-valid JSON
  examples

## Calibration
- sample distribution: 6 unique answers, max answer frequency `0.190`
- qwen25vl7b: hard `0.060`, easy `0.000`, mean `0.225`
- scene review workbook:
  `plans/task-reviews/icons/named_field/scene_review.xlsx`

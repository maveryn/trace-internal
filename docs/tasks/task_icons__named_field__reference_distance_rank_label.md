# `task_icons__named_field__reference_distance_rank_label`

Status: pending taxonomy-v0 review refresh.

## Identity
- domain: `icons`
- scene_id: `named_field`
- scene_id: `relation`
- task: `named_reference_distance_rank_label`
- module: `trace/tasks/icons/named_field/reference_distance_rank_label.py`
- prompt bundle: `prompts/icons/relation/icons_relation_v0.json`

## Scene And Query
The task renders one panel labeled `Scene` with exactly one unique named
reference icon, six option icons labeled `A`..`F`, and `4..8` other icons.
The reference is uniquely identified by its
prompt-named color and procedural shape, for example `red [#E63232] star`.

Supported query ids:
- `closest_to_named_reference_label`
- `second_closest_to_named_reference_label`
- `farthest_from_named_reference_label`

The six labeled option icons are the only answer options. Other icons are not
included in the distance-rank candidate set.

## Answer Contract
- `answer_gt.type = option_letter`
- answer support is exactly `A|B|C|D|E|F`
- the answer is the label of the candidate at the requested center-to-center
  distance rank from the named reference icon

## Annotation Contract
- `annotation_gt.type = keyed_bbox_map`
- annotation contains `reference_icon` for the named reference icon and
  `selected_candidate` for the selected labeled candidate icon
- candidate distance ranks are separated from adjacent ranks by the configured
  `distance_rank_margin_px`

## Trace Contract
- `scene_ir.entities` contains all reference, candidate, and other icons.
- Candidate entities include visible `label`, `distance_to_reference_px`, and
  `distance_rank`.
- `execution_trace.sorted_candidate_labels_by_distance` records the verifier
  order used to derive the answer.
- `projected_annotation.keyed_bbox_map` is derived from the same rendered
  reference and selected candidate bboxes.
- `render_spec.style.text_legibility` records validated panel-header and
  candidate-label text roles for the visible `A`..`F` option labels.

## Prompt Contract
- `scene_key = named_reference_distance_relation`
- `task_key = relation_query`
- prompts ask which labeled icon is closest, second closest, or farthest from
  the unique named reference icon
- answer-only and answer+annotation modes both include contract-valid JSON
  examples

## Current Review Status
Current v0 review and solve-rate artifacts are pending. Browser-review sidecars
belong under
`review/task-reviews/icons/named_field/task_icons__named_field__reference_distance_rank_label/`;
solve-rate status is tracked in `review/calibration_sweep_status.json`.

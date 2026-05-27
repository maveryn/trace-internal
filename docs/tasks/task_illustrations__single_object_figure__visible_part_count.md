# task_illustrations__single_object_figure__visible_part_count

Status: previously accepted after qwen25vl7b solve-rate calibration; expanded
with additional query variants and needs a fresh solve-rate sweep before being
treated as accepted for the full current distribution.

## Taxonomy
- domain: `illustrations`
- task_group: `counterfactual`
- scene_id: `single_object_figure`
- module: `trace/tasks/illustrations/counterfactual/visible_part_count.py`

## Contract
The task renders one large stylized object whose visible part count may differ
from the familiar canonical count. The prompt asks only for the visible count.
Object colors vary by seed as render-only visual variation. Traffic-light lens
colors stay fixed in signal order, while the casing/post color varies; clovers
vary only within green palettes.

Public variants:
- `bird_visible_leg_count`
- `quadruped_visible_leg_count`
- `airplane_visible_wing_count`
- `butterfly_visible_wing_count`
- `bicycle_visible_wheel_count`
- `traffic_light_visible_lens_count`
- `clover_visible_leaf_count`
- `star_visible_point_count`
- `glove_visible_finger_count`
- `fork_visible_tine_count`
- `snowflake_visible_arm_count`
- `chair_visible_leg_count`

## Answer And Evidence
- `answer_gt.type = integer`
- `evidence_gt.type = bbox_set`
- evidence contains one pixel-space bbox per counted visible part, ordered
  left-to-right by bbox position

## Trace
The trace stores the rendered object bbox, counted part bboxes, canonical bias
answer, counterfactual delta, and `counterfactual_edit_type =
visible_part_count_changed`. The render style also records the sampled RGB
colors under `colors_rgb`; traffic-light traces additionally record the fixed
lens color policy and the visible lens RGB sequence. The verifier source of
truth is the generated visible part records, not pixels or the canonical prior.

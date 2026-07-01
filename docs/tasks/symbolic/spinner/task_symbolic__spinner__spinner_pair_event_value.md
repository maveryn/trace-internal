# `task_symbolic__spinner__spinner_pair_event_value`

## Summary
- Domain: `symbolic`
- Scene: `spinner`
- Task id: `task_symbolic__spinner__spinner_pair_event_value`
- Goal: compute the reduced-fraction probability of a color event over one independent spin from each of two equal-sector spinners.

## Program Contract
Program: `probability.two_device_event(scene=spinner, scope=two_independent_equal_sector_spinners, event=both_target_color|at_least_one_target_color|same_color, sample_space=cartesian_product_of_visible_sectors, output=reduced_fraction)`

Candidate set: the cartesian product of visible sectors from spinner `A` and spinner `B`.
Operands: the sector colors on both spinners and the query event predicate.
Operation: count ordered two-spinner outcomes satisfying the event predicate and reduce `matching_outcomes / total_outcomes`.
Output binding: `answer` is the reduced fraction string.
Annotation witnesses: a `bbox_map` with `spinner_a` and `spinner_b` panel bboxes.
Query ids: `pair_both_target_color_probability`, `pair_at_least_one_target_color_probability`, `pair_same_color_probability`.

## Query Contract
- `pair_both_target_color_probability`: both spinners must land on the same resolved target color.
- `pair_at_least_one_target_color_probability`: at least one spinner must land on the resolved target color.
- `pair_same_color_probability`: the two selected sectors must have the same color.

## Answer And Annotation
- `answer_gt.type`: `string`
- `answer_gt.value`: reduced fraction such as `"5/24"`
- Annotation schema: `bbox_map`
- `annotation_gt.type`: `bbox_map`
- Annotation roles: `spinner_a`, `spinner_b`; each role maps to that spinner panel bounding box.

## Implementation Notes
- Source package: `trace.tasks.symbolic.spinner`
- Prompt bundle: `symbolic_spinner_v1`
- Scene variants: `spinner_clean|spinner_card|spinner_notebook`
- Generation is deterministic from seed, params, config, prompt bundle, and code versions.

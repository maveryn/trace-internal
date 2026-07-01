# `task_symbolic__spinner__multi_attribute_or_probability`

## Summary
- Domain: `symbolic`
- Scene: `spinner`
- Task id: `task_symbolic__spinner__multi_attribute_or_probability`
- Goal: compute the reduced-fraction probability that one equal-sector spinner lands on a sector matching either a resolved color or a resolved shape marker.

## Program Contract
Program: `probability.attribute_disjunction_event(scene=spinner, scope=one_equal_sector_spinner, attributes=color_or_shape, sample_space=visible_sectors, output=reduced_fraction)`

Candidate set: all equal-area visible sectors on the spinner.
Operands: each sector's color and shape marker, plus the resolved target color and resolved target shape.
Operation: count sectors matching either target attribute and reduce `matching_sectors / total_sectors`.
Output binding: `answer` is the reduced fraction string.
Annotation witnesses: the scalar bbox of the full spinner panel.
Query ids: `single`.

## Query Contract
- `single`: no public semantic query branch. The disjunction predicate is the fixed objective contract.

## Answer And Annotation
- `answer_gt.type`: `string`
- `answer_gt.value`: reduced fraction such as `"1/3"`
- Annotation schema: `bbox`
- `annotation_gt.type`: `bbox`
- Annotation target: full spinner panel bounding box.

## Implementation Notes
- Source package: `trace.tasks.symbolic.spinner`
- Prompt bundle: `symbolic_spinner_v1`
- Scene variants: `spinner_clean|spinner_card|spinner_notebook`
- Internal trace metadata records `event_key=single_color_or_shape_probability`.
- Generation is deterministic from seed, params, config, prompt bundle, and code versions.

# `task_symbolic__spinner__single_attribute_probability`

## Summary
- Domain: `symbolic`
- Scene: `spinner`
- Task id: `task_symbolic__spinner__single_attribute_probability`
- Goal: compute the reduced-fraction probability that one equal-sector spinner lands on a sector matching one visible attribute.

## Program Contract
Program: `probability.single_attribute_event(scene=spinner, scope=one_equal_sector_spinner, attribute=color|shape, sample_space=visible_sectors, output=reduced_fraction)`

Candidate set: all equal-area visible sectors on the spinner.
Operands: each sector's target attribute value and the resolved color or shape predicate.
Operation: count sectors matching the requested single attribute predicate and reduce `matching_sectors / total_sectors`.
Output binding: `answer` is the reduced fraction string.
Annotation witnesses: the scalar bbox of the full spinner panel.
Query ids: `single_color_probability`, `single_shape_probability`.

## Query Contract
- `single_color_probability`: target predicate is one resolved sector color.
- `single_shape_probability`: target predicate is one resolved sector shape marker.

## Answer And Annotation
- `answer_gt.type`: `string`
- `answer_gt.value`: reduced fraction such as `"3/8"`
- Annotation schema: `bbox`
- `annotation_gt.type`: `bbox`
- Annotation target: full spinner panel bounding box.

## Implementation Notes
- Source package: `trace.tasks.symbolic.spinner`
- Prompt bundle: `symbolic_spinner_v1`
- Scene variants: `spinner_clean|spinner_card|spinner_notebook`
- Generation is deterministic from seed, params, config, prompt bundle, and code versions.

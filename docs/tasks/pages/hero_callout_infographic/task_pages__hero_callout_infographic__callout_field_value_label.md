# `task_pages__hero_callout_infographic__callout_field_value_label`

## Identity
1. Domain: `pages`
2. Scene id: `hero_callout_infographic`
3. Source path: `trace/tasks/pages/hero_callout_infographic/callout_field_value_label.py`
4. Task id: `task_pages__hero_callout_infographic__callout_field_value_label`

## Program Contract
1. Program schema: `lookup.callout_field_value(callout=resolved_callout, field=resolved_field); scene=hero_callout_infographic; scope=one poster-style hero infographic`
2. Contract: find the named callout card, find the named field row in that card, and return the exact visible value cell.
3. Public query contract: one fixed query program with target callout and target field as query arguments.
4. answer schema: `string`
5. Annotation schema: `bbox_map` with `target_callout_card` and `target_field_row` boxes.
6. Supported `query_id`: `single`
7. Prompt query key: `callout_field_value_label`
8. scalar_annotation_checked=true

## Prompt + Trace
1. Prompt bundle: `pages_hero_callout_infographic_v1`
2. Scene key: `hero_callout_infographic`
3. Task key: `hero_callout_infographic_query`
4. Trace records callout titles, field labels, visible values, parsed numeric values, sampled visual assets, sampled style metadata, final card/field-row bboxes, and layout geometry.
5. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized render metadata.

## Rendering Notes
1. The scene draws a central decorative illustration, badge assets, and connector lines as native page content.
2. Decorative page visual assets are visual context only and are not annotation witnesses for this lookup task.

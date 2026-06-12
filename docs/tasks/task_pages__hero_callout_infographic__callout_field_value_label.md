# `task_pages__hero_callout_infographic__callout_field_value_label`

## Identity
1. Domain: `pages`
2. Scene id: `hero_callout_infographic`
3. Source scene: `infographic`
4. Task id: `task_pages__hero_callout_infographic__callout_field_value_label`

## Contract
1. Objective: read one visible value from a titled callout card in a poster-style infographic with a large central hero visual.
2. Branch metadata: `query_id`
3. `query_id`: `callout_field_value_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` with `callout_title`, `field_label`, and `value_cell` boxes.
6. Query knobs: target callout, target field label, callout count, per-callout field count, and scene layout variant.

## Prompt + Trace
1. Prompt bundle: `pages_infographic_v0`
2. Scene key: `hero_callout_infographic`
3. Task key: `hero_callout_infographic_query`
4. Internal prompt variant key: `callout_field_value_label`
5. Trace records callout titles, field labels, visible values, parsed numeric values, sampled visual assets, sampled style metadata, final bboxes, and layout geometry.
6. Generation is deterministic from `instance_seed`; answers and annotation come from the finalized render metadata.

## Rendering Notes
1. The scene disables the generic safe-margin pages context layer and draws the hero visual, decorative illustration, badge assets, and connector lines as native page content.
2. Decorative page visual assets are never supporting annotation for this lookup task.

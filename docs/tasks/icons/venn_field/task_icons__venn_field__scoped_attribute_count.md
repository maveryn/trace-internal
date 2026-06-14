# `task_icons__venn_field__scoped_attribute_count`

## Identity
- domain: `icons`
- scene_id: `venn_field`
- scene_id: `counting`
- task: `named_shape_venn_region_count`
- module: `trace/tasks/icons/counting/named_shape_venn_region_count.py`
- prompt bundle: `prompts/icons/counting/icons_counting_v0.json`

## Scene And Query
The task renders one panel labeled `Scene` containing procedurally generated
named shape icons plus two overlapping marked circles. The prompt names one
target icon condition and asks how many matching icons have centers in a Venn
region.

Supported query ids:
- `inside_both_circles_count`: count targets inside both marked circles.
- `inside_either_circle_count`: count targets inside at least one marked
  circle.
- `inside_exactly_one_circle_count`: count targets inside exactly one marked
  circle.
- `outside_both_circles_count`: count targets outside both marked circles.

Target modes:
- `shape_only`: prompt names one procedural shape, e.g. `"bell"` icons.
- `color_shape`: prompt names a shared semantic color plus shape, e.g.
  `red [#E63232] "bell" icons`.
- `fill_style_shape`: prompt names a fill style plus shape, e.g.
  `striped "bell" icons`.

The target shape support is the full procedural named-icon vocabulary in
`trace/tasks/icons/shared/procedural_named_icons.py`. The task avoids
three-attribute bindings; color and fill style are separate target modes.

## Answer Contract
- `answer_gt.type = integer`
- default answer support is `1..5`
- value is the number of target icons whose centers satisfy the active Venn
  predicate

## Annotation Contract
- `annotation_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for every counted target icon
- icons are placed with bbox clearance from circle boundaries so queried
  targets do not touch or cross the marked circles
- annotation boxes are sorted in reading order

## Trace Contract
- `scene_ir.entities` contains one entity for each rendered procedural icon,
  including `shape_id`, `shape_name`, `color_name`, `fill_style`,
  `venn_category`, and target/count flags.
- `scene_ir.relations.venn` records both circle geometries.
- `query_spec.params.target_attribute_mode` records whether the target is
  shape-only, color+shape, or fill-style+shape.
- `execution_trace.counted_venn_categories` records the categories counted by
  the active query.
- `render_map.counted_instance_ids`, `witness_symbolic.counted_instance_ids`,
  and `projected_annotation.bbox_set` are derived from the same rendered
  instances.
- `projected_annotation` follows the shared icon bbox annotation shape, including
  `bbox_set`, `pixel_bbox_set`, and `pixel_point_set`.

## Prompt Contract
- `scene_key = single_scene_counting`
- `task_key = counting_query`
- prompts ask for the count of target named icons in a visible overlapping
  circle region
- prompt text quotes the named target shape, e.g. `"bell"`
- answer-only and answer+annotation modes both include contract-valid JSON
  examples

# `task_icons__pattern_grid__attribute_pattern_violation_index`

## Identity
- domain: `icons`
- scene_id: `pattern_grid`
- module: `trace/tasks/icons/pattern_grid/attribute_pattern_violation_index.py`
- prompt bundle: `icons_pattern_v0`

## Program Contract
`selection.attribute_pattern_violation(scene=pattern_grid, scope=numbered_grid_cells, attribute=color|size, output=cell_index)`

scene=pattern_grid
scope=numbered_grid_cells

## Contract
Renders a numbered `3 x 3` icon grid where one numbered box violates a visible
attribute pattern. The public task asks for the number of the single violating
box.

Supported query ids:
- `grid_color_violation`: the violating cell breaks the color pattern.
- `grid_size_violation`: the violating cell breaks the size pattern.

Answer schema: integer numbered-box index.
Annotation schema: scalar `bbox` around the violating numbered box.

## Notes
Color and size are semantic query branches of the same objective contract:
identify the single visible attribute-pattern violation in a numbered grid. The
color branch internally samples row-uniform and column-uniform repetition rules,
recorded as `pattern_rule` and `color_group_axis` trace metadata. It does not
use hidden ordered color arithmetic. The sampled icon, palette, canvas style,
and exact violating index are recorded as trace metadata.

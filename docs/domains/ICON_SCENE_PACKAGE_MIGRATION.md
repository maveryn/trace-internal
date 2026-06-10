# Icons Scene-Package Migration Notes

Use this note with `docs/workflows/SCENE_PACKAGE_MIGRATION/README.md` when
migrating the `icons` domain.

## Current Inventory

The icons domain has 40 active public tasks across 18 public scenes:

- `icon_cutout`: 1 task
- `icon_field`: 1 task
- `mirror_grid`: 1 task
- `named_field`: 12 tasks
- `named_grid`: 3 tasks
- `named_path`: 1 task
- `named_ring`: 1 task
- `named_strip`: 1 task
- `overlap_grid`: 1 task
- `pair_grid`: 2 tasks
- `paired_canvas`: 4 tasks
- `pattern_grid`: 1 task
- `reference_canvas`: 3 tasks
- `sequence_strip`: 2 tasks
- `single_transform_options`: 1 task
- `two_anchor`: 1 task
- `venn_field`: 1 task
- `wallpaper_panels`: 3 tasks

## Migrated Scenes

The following icons scenes have moved to scene-package layout and are listed in
`MIGRATED_SCENE_PACKAGE_SCENES`:

```text
single_transform_options
pair_grid
paired_canvas
```

Migrated task modules:

```text
trace/tasks/icons/single_transform_options/geometric_transform_result_label.py
trace/tasks/icons/pair_grid/attribute_delta_pair_count.py
trace/tasks/icons/pair_grid/reference_transform_match_count.py
trace/tasks/icons/paired_canvas/original_attribute_label.py
trace/tasks/icons/paired_canvas/panel_attribute_change_count.py
trace/tasks/icons/paired_canvas/panel_movement_direction_count.py
trace/tasks/icons/paired_canvas/panel_set_relation_count.py
```

Migrated scene configs:

```text
configs/domains/icons/single_transform_options.yaml
configs/domains/icons/pair_grid.yaml
configs/domains/icons/paired_canvas.yaml
```

Migrated prompt bundles:

```text
prompts/icons/single_transform_options/icons_single_transform_options_v0.json
prompts/icons/pair_grid/icons_pair_grid_v0.json
prompts/icons/paired_canvas/icons_paired_canvas_v0.json
```

These scenes validate scene package layout, scene config loading, scene prompt
loading, and task-group-free generated records before migrating the whole icons
domain.

## Known Consolidation Work

These legacy modules currently bundle multiple public tasks and must be split
during the full migration:

- `named_shape_color_boolean_count.py`: split into five `named_field` task
  modules.
- `named_shape_counterfactual_count.py`: split into two `named_field` task
  modules.
- `reference_match_count.py`: split into two `reference_canvas` task modules.

These public task ids are currently mentioned by multiple legacy modules and
must collapse to one final module per task:

- `task_icons__icon_field__type_frequency_count`
- `task_icons__pattern_grid__attribute_pattern_violation_index`
- `task_icons__reference_canvas__reference_metric_relation_count`

Do not add `icons` to `MIGRATED_SCENE_PACKAGE_DOMAINS` until all active icons
tasks, configs, prompts, docs, tests, and review artifacts have moved to the
scene-package layout.

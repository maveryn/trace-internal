# `task_icons__wallpaper_panels__motif_violation_label`

## Program Contract

`relation.option_panel_outlier_label(scene=wallpaper_panels, scope=curated_icon_wallpaper_patterns, relation=one_candidate_has_distinct_wallpaper_group, output=option_letter)`

## Identity

- Domain: `icons`
- Scene id: `wallpaper_panels`
- Task id: `task_icons__wallpaper_panels__motif_violation_label`
- Objective contract: select the labeled wallpaper panel whose repeated motif pattern differs from the other five panels.
- Module: `trace/tasks/icons/wallpaper_panels/motif_violation_label.py`
- Prompt bundle: `prompts/icons/wallpaper_panels/icons_wallpaper_panels_v1.json`

## Contract

- Supported `query_id` values: `single`.
- Answer schema: `option_letter`.
- Annotation schema: `bbox`.
- The image contains six labeled panels `A..F`.
- Five panels share one wallpaper-group arrangement and exactly one panel uses a different wallpaper-group arrangement.
- Wallpaper groups are rendered with repeated curated-icon motifs on an invisible `4 x 4` lattice.
- Wallpaper group id, icon id, canvas treatment, palette, and the selected odd panel are generation metadata, not public query ids.

## Generation

- Option count is fixed at six.
- The shared wallpaper group and odd wallpaper group are distinct by construction.
- Each panel uses a distinct curated icon from `non_symmetry.txt`.
- Wallpaper panels use quiet canvas treatments only, with no visible internal grid or tile outline.
- Generation rejects unsupported option counts, unsupported wallpaper groups, unsafe canvas treatments, collapsed layouts, insufficient icon pools, and palette/style failures.

## Prompt

- Prompt bundle: `icons_wallpaper_panels_v1`
- `scene_key`: `wallpaper_panel_violation_scene`
- `task_key`: `motif_violation_label`
- Answer-only JSON shape: `{"answer":"C"}`
- Answer+annotation JSON shape: `{"annotation":[420,220,620,400],"answer":"C"}`

## Annotation

- `bbox` is used because the task always has exactly one selected panel witness.
- The box marks the selected wallpaper panel, not individual motif icons or the letter label.
- `scalar_annotation_checked=true`.

## Trace

- `scene_ir.entities` contains wallpaper panel entities plus motif-element and icon-instance entities.
- `execution_trace.wallpaper_group_ids_by_label` records the panel-to-wallpaper-group mapping.
- `render_map.answer_panel_bbox_px`, `witness_symbolic.answer_panel_bbox_xyxy`, and `projected_annotation.bbox` are derived from the same selected panel.

## Tests

- Behavior and trace tests: `tests/test_icons_pattern_wallpaper_motif_violation_tasks.py`
- Config tests: `tests/test_icons_scene_config.py`
- Prompt bundle tests: `tests/test_prompt_system.py`
- Scene-package migration gates: `tests/test_scene_package_migration_contracts.py`, `tests/test_scene_package_review_candidate_contracts.py`

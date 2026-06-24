# `task_icons__wallpaper_panels__same_pattern_as_reference_label`

## Program Contract

`relation.reference_panel_pattern_match_label(scene=wallpaper_panels, scope=curated_icon_wallpaper_patterns, relation=same_wallpaper_group_as_reference, output=option_letter)`

## Identity

- Domain: `icons`
- Scene id: `wallpaper_panels`
- Task id: `task_icons__wallpaper_panels__same_pattern_as_reference_label`
- Objective contract: select the labeled panel whose repeated motif pattern matches the Reference panel.
- Module: `trace/tasks/icons/wallpaper_panels/same_pattern_as_reference_label.py`
- Prompt bundle: `prompts/icons/wallpaper_panels/icons_wallpaper_panels_v1.json`

## Contract

- Supported `query_id` values: `single`.
- Answer schema: `option_letter`.
- Annotation schema: `bbox_map`.
- The image contains one `Reference` panel and four candidate panels `A..D`.
- The `Reference` panel is shown above the candidate grid and has the same size as each candidate panel.
- Exactly one candidate panel shares the Reference wallpaper group; every distractor uses a distinct non-reference wallpaper group.
- Wallpaper groups are rendered with exactly one visible curated-icon motif per cell on an invisible `4 x 4` lattice, for 16 motif icons per panel.
- Wallpaper group id, icon id, canvas treatment, palette, and selected answer label are generation metadata, not public query ids.

## Generation

- Option count is fixed at four.
- The reference-match canvas is `1104 x 960` pixels, below the 1,200,000-pixel cap.
- The Reference and correct candidate share one wallpaper group.
- Nonmatching candidate groups are distinct from the Reference group and from each other.
- Each panel, including Reference, uses a distinct curated icon from `non_symmetry.txt`.
- Wallpaper panels use quiet canvas treatments only, with no visible internal grid or tile outline.
- Generation rejects unsupported option counts, unsupported wallpaper groups, unsafe canvas treatments, too-small group supports, collapsed layouts, insufficient icon pools, and palette/style failures.

## Prompt

- Prompt bundle: `icons_wallpaper_panels_v1`
- `scene_key`: `wallpaper_reference_match_scene`
- `task_key`: `same_pattern_as_reference_label`
- Answer-only JSON shape: `{"answer":"C"}`
- Answer+annotation JSON shape: `{"annotation":{"reference_panel":[36,36,320,604],"selected_panel":[420,220,620,400]},"answer":"C"}`

## Annotation

- `bbox_map` is used because two role-bound panel witnesses are required.
- `reference_panel` marks the Reference panel.
- `selected_panel` marks the selected candidate panel.
- Boxes mark whole wallpaper panels, not individual motif icons or letter labels.
- `scalar_annotation_checked=true`; scalar `bbox` is not sufficient because role binding matters.

## Trace

- `scene_ir.entities` contains wallpaper panel entities plus motif-element and icon-instance entities.
- `execution_trace.wallpaper_group_ids_by_label` records the candidate panel-to-wallpaper-group mapping.
- `render_map.reference_panel_bbox_px`, `render_map.answer_panel_bbox_px`, and `projected_annotation.bbox_map` are derived from the same rendered panels.

## Tests

- Behavior and trace tests: `tests/test_icons_pattern_wallpaper_reference_match_tasks.py`
- Config tests: `tests/test_icons_scene_config.py`
- Prompt bundle tests: `tests/test_prompt_system.py`
- Scene-package migration gates: `tests/test_scene_package_migration_contracts.py`, `tests/test_scene_package_review_candidate_contracts.py`

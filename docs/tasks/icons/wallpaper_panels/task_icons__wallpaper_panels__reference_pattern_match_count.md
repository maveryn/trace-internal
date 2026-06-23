# `task_icons__wallpaper_panels__reference_pattern_match_count`

## Program Contract

`counting.reference_panel_pattern_match_count(scene=wallpaper_panels, scope=curated_icon_wallpaper_patterns, relation=same_wallpaper_group_as_reference, output=count)`

## Identity

- Domain: `icons`
- Scene id: `wallpaper_panels`
- Task id: `task_icons__wallpaper_panels__reference_pattern_match_count`
- Objective contract: count how many labeled candidate panels use the same repeated motif pattern as the Reference panel.
- Module: `trace/tasks/icons/wallpaper_panels/reference_pattern_match_count.py`
- Prompt bundle: `prompts/icons/wallpaper_panels/icons_wallpaper_panels_v1.json`

## Contract

- Supported `query_id` values: `single`.
- Answer schema: `integer`.
- Annotation schema: `bbox_set_map`.
- The image contains one `Reference` panel and six candidate panels `A..F`.
- Between one and five candidate panels share the Reference wallpaper group.
- Every nonmatching candidate uses a distinct non-reference wallpaper group.
- Wallpaper groups are rendered with repeated curated-icon motifs on an invisible `4 x 4` lattice.
- Match count, matching labels, wallpaper group id, icon id, canvas treatment, and palette are generation metadata, not public query ids.

## Generation

- Option count is fixed at six.
- Default answer support is `1..5`.
- Matching candidate labels are sampled without replacement and rendered in their visible panel locations.
- Each panel, including Reference, uses a distinct curated icon from `non_symmetry.txt`.
- Wallpaper panels use quiet canvas treatments only, with no visible internal grid or tile outline.
- Generation rejects unsupported option counts, unsupported match counts, unsupported wallpaper groups, unsafe canvas treatments, too-small group supports, collapsed layouts, insufficient icon pools, and palette/style failures.

## Prompt

- Prompt bundle: `icons_wallpaper_panels_v1`
- `scene_key`: `wallpaper_reference_match_scene`
- `task_key`: `reference_pattern_match_count`
- Answer-only JSON shape: `{"answer":2}`
- Answer+annotation JSON shape: `{"annotation":{"reference_panel":[[36,36,320,604]],"matching_candidate_panels":[[420,220,620,400],[650,220,850,400]]},"answer":2}`

## Annotation

- `bbox_set_map` is used because the Reference role and matching-candidate set are heterogeneous witness roles.
- `reference_panel` is a one-item list containing the Reference panel box.
- `matching_candidate_panels` contains the whole-panel boxes for matching candidate panels, sorted by visible label order.
- Boxes mark whole wallpaper panels, not individual motif icons or letter labels.
- `scalar_annotation_checked=true`; scalar `bbox` is not sufficient because the number of matching candidates varies and the Reference role must be explicit.

## Trace

- `scene_ir.entities` contains wallpaper panel entities plus motif-element and icon-instance entities.
- `execution_trace.matching_labels` records the matching candidate labels.
- `execution_trace.wallpaper_group_ids_by_label` records the candidate panel-to-wallpaper-group mapping.
- `render_map.matching_candidate_panel_bboxes_px`, `witness_symbolic.matching_candidate_panel_bboxes_xyxy`, and `projected_annotation.bbox_set_map` are derived from the same rendered panels.

## Tests

- Behavior and trace tests: `tests/test_icons_pattern_wallpaper_reference_match_count_tasks.py`
- Config tests: `tests/test_icons_scene_config.py`
- Prompt bundle tests: `tests/test_prompt_system.py`
- Scene-package migration gates: `tests/test_scene_package_migration_contracts.py`, `tests/test_scene_package_review_candidate_contracts.py`

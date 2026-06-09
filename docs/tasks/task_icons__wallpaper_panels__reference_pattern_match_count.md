# `task_icons__wallpaper_panels__reference_pattern_match_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `wallpaper_panels`
3. Task group: `pattern`
4. Task id: `task_icons__wallpaper_panels__reference_pattern_match_count`
5. Objective: count how many labeled wallpaper panels use the same global wallpaper arrangement as the Reference panel.

## 2) Scene + task contract
1. Entities/relations: one Reference wallpaper panel and six labeled candidate panels `A..F`; between one and five candidates share the Reference wallpaper group.
2. Supported `query_id` values:
   - `reference_pattern_match_count`
3. Answer type: `answer_gt.type = integer`.
4. Annotation type: `annotation_gt.type = keyed_bbox_set_map` with panel-box lists under keys `reference_panel` and `matching_candidate_panels`; `reference_panel` is a one-box list.
5. Pattern policy: every matching candidate and the Reference share one wallpaper group; every nonmatching candidate uses a distinct other wallpaper group.
6. Asset policy: generation samples only from `assets/icons/non_symmetry.txt`; each panel uses a different icon id while sharing tint and icon size, so the answer depends on global pattern layout rather than icon identity.
7. Render policy: no internal grid/cell/tile outlines are drawn inside wallpaper panels; the `4 x 4` motif lattice is metadata-only. Wallpaper panels use quiet canvas treatments only (`bare_canvas`, `plain_sheet`, `matte_sheet`, `thin_frame`, `soft_panel`) so ruled or worksheet-like chrome cannot appear inside motif areas.
8. Wallpaper group subset: `p1`, `p2`, `pm`, `pg`, `cm`, `pmm`, `p4`, `p3`.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_pattern_v0`
2. `scene_key`: `wallpaper_reference_match_scene`
3. `task_key`: `structured_violation_query`
4. Answer+annotation JSON shape: `{"annotation":{"reference_panel":[[36,36,320,604]],"matching_candidate_panels":[[420,220,620,400],[650,220,850,400]]},"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Prompt style: asks how many labeled panels use the same wallpaper arrangement as the Reference panel; curated icon ids are never shown.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`, deterministic support selection via `task_icons__wallpaper_panels__reference_pattern_match_count:wallpaper_spec`, deterministic matching-label choice via `task_icons__wallpaper_panels__reference_pattern_match_count:matching_labels`, deterministic distractor-group order via `task_icons__wallpaper_panels__reference_pattern_match_count:distractor_groups`, plus per-icon noise namespaces.
2. Unique-answer policy: the answer is the exact number of candidate panels whose wallpaper group matches the Reference wallpaper group.
3. Reject/resample conditions: unsupported option count, unsupported match count, too few wallpaper groups, unsupported wallpaper group id, icon pool smaller than seven panels, palette-separation failures, collapsed layout, or motif icon placement failure.
4. Semantic-unit rule: the public answer is an integer count; annotation marks the Reference panel and every matching visual candidate panel.
5. Trace metadata records option labels, Reference group id, matching labels, group id by candidate label, icon id by panel label, panel geometry, palette/style metadata, and per-icon noise edits.

## 5) Complexity + tests
1. Complexity definition/components: wallpaper-group rule inference, visual scan over the Reference and candidate panels, match-count ambiguity, and icon-scene clutter.
2. Behavior/trace/prompt tests: `tests/test_icons_pattern_wallpaper_reference_match_count_tasks.py`
3. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_icons_task_group_config.py`

# `task_icons__wallpaper_panels__same_pattern_as_reference_label`

## 1) Identity
1. Domain: `icons`
2. Scene id: `wallpaper_panels`
3. Scene: `pattern`
4. Task id: `task_icons__wallpaper_panels__same_pattern_as_reference_label`
5. Objective: select the labeled wallpaper panel whose global wallpaper pattern matches the Reference panel.

## 2) Scene + task contract
1. Entities/relations: one Reference wallpaper panel and six labeled candidate panels `A..F`; exactly one candidate has the same wallpaper group as the Reference panel.
2. Supported `query_id` values:
   - `same_pattern_as_reference_label`
3. Answer type: `answer_gt.type = option_letter`.
4. Annotation type: `annotation_gt.type = keyed_bbox_map` with keys `reference_panel` and `selected_panel`.
5. Pattern policy: the selected candidate and Reference share one wallpaper group; each distractor candidate uses a distinct other wallpaper group.
6. Asset policy: generation samples only from `assets/icons/non_symmetry.txt`; each panel uses a different icon id while sharing tint and icon size, so the answer depends on global pattern layout rather than icon identity.
7. Render policy: no internal grid/cell/tile outlines are drawn inside wallpaper panels; the `4 x 4` motif lattice is metadata-only. Wallpaper panels use quiet canvas treatments only (`bare_canvas`, `plain_sheet`, `matte_sheet`, `thin_frame`, `soft_panel`) so ruled or worksheet-like chrome cannot appear inside motif areas.
8. Wallpaper group subset: `p1`, `p2`, `pm`, `pg`, `cm`, `pmm`, `p4`, `p3`.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_pattern_v0`
2. `scene_key`: `wallpaper_reference_match_scene`
3. `task_key`: `structured_violation_query`
4. Answer+annotation JSON shape: `{"annotation":{"reference_panel":[36,36,320,604],"selected_panel":[420,220,620,400]},"answer":"C"}`
5. Answer-only JSON shape: `{"answer":"C"}`
6. Prompt style: asks which labeled panel has the same wallpaper pattern as the Reference panel; curated icon ids are never shown.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`, deterministic support selection via `task_icons__wallpaper_panels__same_pattern_as_reference_label:wallpaper_spec`, deterministic distractor-group order via `task_icons__wallpaper_panels__same_pattern_as_reference_label:distractor_groups`, plus per-icon noise namespaces.
2. Unique-answer policy: exactly one candidate panel shares the Reference wallpaper group and every distractor uses a distinct non-reference group.
3. Reject/resample conditions: unsupported option count, too few wallpaper groups, unsupported wallpaper group id, icon pool smaller than seven panels, palette-separation failures, collapsed layout, or motif icon placement failure.
4. Semantic-unit rule: the public answer is the candidate panel letter; annotation marks the Reference panel and selected visual option panel.
5. Trace metadata records option labels, Reference group id, group id by candidate label, icon id by panel label, panel geometry, palette/style metadata, and per-icon noise edits.

## 5) Complexity + tests
1. Complexity definition/components: wallpaper-group rule inference, visual scan over the Reference and candidate panels, answer ambiguity floor, and icon-scene clutter.
2. Behavior/trace/prompt tests: `tests/test_icons_pattern_wallpaper_reference_match_tasks.py`
3. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_icons_scene_config.py`

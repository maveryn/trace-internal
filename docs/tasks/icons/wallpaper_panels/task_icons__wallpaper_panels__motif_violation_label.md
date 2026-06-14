# `task_icons__wallpaper_panels__motif_violation_label`

## 1) Identity
1. Domain: `icons`
2. Scene id: `wallpaper_panels`
3. Scene: `pattern`
4. Task id: `task_icons__wallpaper_panels__motif_violation_label`
5. Objective: select the labeled wallpaper panel whose global wallpaper pattern differs from the others.

## 2) Scene + task contract
1. Entities/relations: six labeled option panels `A..F`; five panels share one continuous repeated icon-motif wallpaper pattern and one panel uses a different wallpaper-group pattern. Patterns are generated from an invisible `4 x 4` lattice.
2. Supported `query_id` values:
   - `wallpaper_motif_violation_label`
3. Answer type: `answer_gt.type = option_letter`.
4. Annotation type: `annotation_gt.type = bbox_set` with exactly one bbox around the selected odd wallpaper panel.
5. Motif policy: five panels use the same wallpaper group and one panel uses a different wallpaper group.
6. Asset policy: generation samples only from `assets/icons/non_symmetry.txt`; each panel uses a different icon id while sharing tint and icon size, so the answer depends on global pattern layout rather than icon identity.
7. Distractor policy: non-answer panels have the same wallpaper group as each other and the answer panel has a different wallpaper group.
8. Styling policy: all option panels share icon tint, icon size, and invisible lattice shape within an instance.
9. Render policy: no internal grid/cell/tile outlines are drawn inside panels; the lattice is metadata-only. Wallpaper panels use quiet canvas treatments only (`bare_canvas`, `plain_sheet`, `matte_sheet`, `thin_frame`, `soft_panel`) so ruled or worksheet-like chrome cannot appear inside motif areas.
10. Wallpaper group subset: `p1`, `p2`, `pm`, `pg`, `cm`, `pmm`, `p4`, `p3`.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_pattern_v0`
2. `scene_key`: `wallpaper_panel_violation_scene`
3. `task_key`: `structured_violation_query`
4. Answer+annotation JSON shape: `{"annotation":[[420,220,462,262]],"answer":"C"}`
5. Answer-only JSON shape: `{"answer":"C"}`
6. Prompt style: asks which labeled wallpaper panel uses a different wallpaper pattern from the others; curated icon ids are never shown.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`, deterministic support selection via `task_icons__wallpaper_panels__motif_violation_label:wallpaper_spec`, plus per-icon noise namespaces.
2. Unique-answer policy: five panels share one wallpaper group and exactly one labeled panel uses a different wallpaper group by construction.
3. Reject/resample conditions: unsupported option count, unsupported wallpaper group id, icon pool smaller than the option count, palette-separation failures, collapsed layout, or motif icon placement failure.
4. Semantic-unit rule: the public answer is the panel letter, while annotation marks the selected visual option panel because the difference is global to that panel.
5. Trace metadata records option count, option labels, shared wallpaper group id, odd wallpaper group id, group id by panel label, answer panel, icon id by panel label, palette/style metadata, and per-icon noise edits.

## 5) Complexity + tests
1. Complexity definition/components: wallpaper-group rule inference, visual scan over the six panels, answer ambiguity floor, and icon-scene clutter.
2. Behavior/trace/prompt tests: `tests/test_icons_pattern_wallpaper_motif_violation_tasks.py`
3. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_icons_scene_config.py`

# Puzzle Style-Pack Workflow

## Purpose

This note records the current puzzle-domain visual style-pack pass. The goal is
to make existing puzzle scenes visually broader without adding task ids,
changing task semantics, or changing verifier/evidence contracts.

Use this together with:

- `docs/workflows/PUZZLE_GAME_RENDERING_UPGRADE.md`
- `plans/SHARED_VISUAL_STYLE_REFACTOR_NOTE.md`
- `docs/domains/PUZZLE_TASK_SETUP.md`
- `docs/workflows/SHARED_UTILITIES.md`
- `trace/tasks/puzzles/shared/scene_style.py`

## Meaning Of Style Packs

`puzzle-specific style packs` means scene-local adapters over the shared panel
style system. They are visual-only wrappers for existing puzzle scenes:

- worksheet, puzzle-card, magazine, notebook, scan, lab-board, or light game-UI
  treatments
- palette, line-weight, grid-stroke, background, frame, margin, option-card, and
  mild noise variation
- optional scene chrome that is visibly non-semantic

They do not mean new tasks, new answer types, new hidden rules, or new public
taxonomy rows.

All puzzle scenes that use this layer must access the shared 20-treatment /
20-palette registry through `trace/tasks/puzzles/shared/scene_style.py`.
Do not duplicate treatment or palette code inside puzzle renderers.

## Hard Invariants

- Keep the public taxonomy unchanged: `domain -> scene_id -> task_id`.
- Keep answer distributions, solver logic, query semantics, prompts, and
  verifier payloads unchanged unless a stale visual description must be fixed.
- Preserve semantic colors and labels. If a treatment or palette makes puzzle
  state harder to read, constrain the scene's compatible styles.
- Project public evidence after final layout, canvas size, style, and unit-size
  jitter are resolved.
- Keep evidence bboxes/points inside the final canvas.
- Keep repeated units readable. Target about `2x` unit-size jitter when feasible,
  with minimum effective unit size around `28px` unless the scene has a
  documented exception.
- Record style metadata: treatment id, palette id, chrome mode, layout jitter,
  effective unit size, canvas size, and any scene-specific palette roles.
- Do not correlate visual style with query id, answer value, correct option, or
  difficulty.
- Do not run solve-rate calibration during this pass unless explicitly asked.

## Scene Priority

Do not try to style every puzzle scene in one bulk pass. Work scene by scene.

High-priority scenes:

- `arithmetic_constraint_puzzle`
- `word_search_grid`
- `maze_grid`
- `nonogram_grid_panel`
- `logic_grid`
- `raven_matrix`
- `music_staff_notation`
- `cell_board`

Medium-priority scenes:

- `tents_grid`
- `star_battle_grid`
- `polyomino_missing_region_board`
- `cube_voxel_puzzle`
- `sliding_block_board`
- `sokoban_grid_panel`
- `pipe_flow_grid`
- `counterfactual_board_grid`
- `agent_automaton_grid`
- `life_automaton_grid`
- `turing_tape_machine`

Lower-priority or fragile scenes:

- `paper_fold_panel`
- `paper_fold_cut_panel`
- `overlay_panel`
- `color_gradient_grid`
- `single_analog_clock`
- `clock_face_collection`
- `rubiks_cube_net_panel`
- `dice_probability_panel`
- `spinner_probability_panel`
- `matchstick_arrangement_panel`
- `cyclic_order_loop`
- `string_topology`
- `tangram_assembly_panel`

Lower priority does not mean "never"; it means style has a higher chance of
confusing geometry, fold/cut traces, topology, probability labels, or small
notation, so those scenes need tighter compatible treatment lists.

## Per-Scene Workflow

1. Pick one scene.
2. Identify all active task ids in that scene.
3. Inspect the renderer for fixed canvas size, fixed origin, narrow palette,
   hardcoded local treatment code, and evidence projection timing.
4. Add or route style sampling through
   `trace/tasks/puzzles/shared/scene_style.py`.
5. Map shared style roles to scene-owned concepts. Examples:
   - canvas/background -> worksheet, card, notebook, or board background
   - grid/stroke -> non-semantic grid/border lines
   - accent -> frame, panel title strip, or option-card accent
   - marker/cell palettes -> only where they do not overwrite semantic colors
6. Apply layout and unit-size jitter before evidence projection.
7. Add metadata for the sampled style and final layout.
8. Compile touched modules and run focused tests if the scene has tests.
9. Regenerate task review workbooks with `100` samples per task.
10. Rebuild the scene-level workbook.
11. Inspect the workbook images and metadata before moving to the next scene.

## Review Commands

Use inspection mode for visual-only style changes:

```bash
PYTHONPATH=. python scripts/run_task_review.py \
  --tasks <comma_separated_task_ids_for_scene> \
  --mode inspection \
  --random-count 100 \
  --max-total-samples-per-task 100 \
  --out-root plans/task-reviews
```

If the scene workbook does not refresh automatically or only the combined
workbook is needed:

```bash
PYTHONPATH=. python scripts/build_scene_task_review_workbooks.py \
  --out-root plans/task-reviews \
  --scene puzzles/<scene_id>
```

Do not use non-current review folders as current evidence. Current scene review
artifacts belong under:

```text
plans/task-reviews/puzzles/<scene_id>/scene_review.xlsx
plans/task-reviews/puzzles/<scene_id>/<task_id>/<task_id>.xlsx
```

## Inspection Checklist

For each regenerated `scene_review.xlsx`, check:

- visible style variety exists across the 100 samples per task
- style treatment and palette are recorded in metadata
- board/panel placement varies when there is slack
- unit size never drops below the scene's safe minimum
- semantic markings remain readable
- prompt text still matches what is actually visible
- evidence overlays align with final rendered positions
- no decorative chrome is used as evidence unless the task explicitly asks for
  it
- no new ambiguous answer cases are introduced

## Handoff Format

After each scene, summarize:

```text
Scene: puzzles/<scene_id>
Tasks refreshed: <task ids>
Renderer files touched: <paths>
Style source: shared panel style via trace/tasks/puzzles/shared/scene_style.py
Compatible treatments constrained: yes/no, reason if yes
Unit-size range: <range or unchanged>
Evidence projection checked: yes/no
Review workbook: plans/task-reviews/puzzles/<scene_id>/scene_review.xlsx
Solve rate run: no, unless explicitly requested
Open issues: <none or list>
```

## Common Mistakes To Avoid

- Adding a scene-local copy of the 20 treatments or 20 palettes.
- Applying a global post-render recolor that also changes semantic colors.
- Moving/cropping rendered pixels after evidence bboxes are computed.
- Letting decorative panels, titles, option cards, or noise hide required cells.
- Treating style pack work as a reason to add new task ids.
- Bulk-regenerating scene reviews before verifying that a renderer actually
  samples and records style metadata.
- Removing contiguous answer support or changing answer ranges during a visual
  style pass.

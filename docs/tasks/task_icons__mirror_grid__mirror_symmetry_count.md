# `task_icons__mirror_grid__mirror_symmetry_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `mirror_grid`
3. Task group: `relation`
4. Task id: `task_icons__mirror_grid__mirror_symmetry_count`
5. Objective: count how many labeled Scene cells have the same mirror symmetry as the Reference cell.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` cell on the left and a labeled `Scene` grid of icon-arrangement cells on the right.
2. Query id: `mirror_symmetry_count`.
3. Supported `mirror_signature` values: `mirror_vertical`, `mirror_horizontal`, `mirror_diagonal_main`, `mirror_diagonal_anti`, `mirror_both_axes`.
4. Answer type: `answer_gt.type = integer`.
5. Annotation type: `annotation_gt.type = bbox_set` (pixel-space boxes around the matching Scene cells, sorted top-to-bottom then left-to-right).
6. Count policy: Scene cell count is fixed at `6` (`2 x 3` grid); `target_count` is sampled independently from `0..4`, `distractor_count = 6 - target_count`, so there are always at least `2` non-matching Scene cells.
7. Label policy: Scene grid labels are fixed row-major as `A..F`; generation randomizes cell content, not label positions.
8. Asset policy: cells use the curated asymmetric icon subset from `assets/icons/non_symmetry.txt`; icon identity is not part of the query, only the mirror-symmetry type of each cell arrangement.
9. Symmetry policy: the Reference cell samples one exact `mirror_signature` from vertical, horizontal, main-diagonal, anti-diagonal, or both vertical+horizontal axes; matching Scene cells must satisfy that same exact symmetry signature, while distractors are a mix of exact-other-symmetry cells and cells with no supported mirror symmetry.
10. Exactness rule: matching cells must satisfy only the requested symmetry signature under rendered-image checks. In particular, single-axis or single-diagonal matches may not accidentally satisfy any other supported axis, `mirror_both_axes` must satisfy vertical+horizontal but not either diagonal, and distractor cells marked `none` must satisfy none of the supported axes.
11. Cell styling: the Reference cell and Scene cells use square cell boxes/content regions so diagonal symmetry is well-defined. Symmetric single-axis/diagonal cells use even icon counts from `2`, `4`, or `6`; both-axes cells use one `4`-icon orbit; non-symmetric cells also keep even icon counts (`2`, `4`, or `6`) so odd-count cues never give the answer away.
12. Noise policy: each seed icon may receive `0..2` subtle per-icon edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; the mirrored counterpart is derived from the edited seed sprite, so noise does not break the exact symmetry contract.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_relation_v0`
2. `scene_key`: `reference_grid_mirror_symmetry_relation`
3. `task_key`: `relation_query`
4. Answer+annotation JSON shape: `{"annotation":[[360,120,560,320],[590,120,790,320]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
7. Variant counts (scene/task/mode): exactly 5 templates per required key.
8. Prompt style: the scene stem establishes the Reference-vs-Scene labeled-grid layout; task wording asks only about matching mirror symmetry and names vertical, horizontal, either diagonal, and both-axes cases.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching Scene labels are sampled first, then the cell patches and matching-cell annotation boxes are generated from that exact match trace; `answer_gt` and `annotation_gt` both come from the same sampled match set.
3. Reject/resample conditions: unsupported count config, empty icon pool, palette-separation failures, or inability to render exact symmetric / exact non-symmetric cell patches under the configured gap and margin constraints.
4. No-auto-relaxation guarantee: generation fails on unmet symmetry/layout constraints instead of weakening the exact mirror-symmetry contract.
5. Semantic-unit rule: annotation is a pixel-space box around each matching Scene cell because the task asks about whole-cell mirror symmetry, not about one icon bbox inside a cell; the matching labels remain private trace metadata.
6. Trace style metadata records the sampled palette, cell-grid styling, validated text-legibility metadata, patch gap/margin settings, icon-count choices, and the per-seed noise ranges used during patch generation.
7. Balanced defaults: seeded sampling first balances the five `mirror_signature` values, then the task passes a decoupled index to the fixed-grid count resolver so each signature cycles through the full feasible `0..4` answer support.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + query branch.
2. Determinism/build tests: `tests/test_icons_relation_mirror_symmetry_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_relation_mirror_symmetry_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`

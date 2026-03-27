# `task_icons_relation_mirror_symmetry`

## 1) Identity
1. Domain: `icons`
2. Task group: `relation`
3. Task id: `task_icons_relation_mirror_symmetry`
4. Objective: count how many labeled Scene cells have the same mirror symmetry as the Reference cell.

## 2) Scene + task contract
1. Entities/relations: one two-panel image with a `Reference` cell on the left and a labeled `Scene` grid of icon-arrangement cells on the right.
2. Supported `task_variant` values: `mirror_vertical`, `mirror_horizontal`, `mirror_diagonal_main`, `mirror_diagonal_anti`, `mirror_both_axes`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = label_set` (sorted labels of the matching Scene cells).
5. Count policy: Scene cell count is fixed at `6` (`2 x 3` grid); `target_count` is sampled independently from `0..4`, `distractor_count = 6 - target_count`, so there are always at least `2` non-matching Scene cells.
6. Asset policy: cells use the curated asymmetric Prism subset from `assets/icons/non_symmetry.txt`; icon identity is not part of the query, only the mirror-symmetry type of each cell arrangement.
7. Symmetry policy: the Reference cell is sampled as one exact symmetry type from vertical, horizontal, main-diagonal, anti-diagonal, or both vertical+horizontal axes; matching Scene cells must satisfy that same exact symmetry signature, while distractors are a mix of exact-other-symmetry cells and cells with no supported mirror symmetry.
8. Exactness rule: matching cells must satisfy only the requested symmetry signature under rendered-image checks. In particular, single-axis or single-diagonal matches may not accidentally satisfy any other supported axis, `mirror_both_axes` must satisfy vertical+horizontal but not either diagonal, and distractor cells marked `none` must satisfy none of the supported axes.
9. Cell styling: the Reference cell and Scene cells use square cell boxes/content regions so diagonal symmetry is well-defined. Symmetric single-axis/diagonal cells use even icon counts from `2`, `4`, or `6`; both-axes cells use one `4`-icon orbit; non-symmetric cells also keep even icon counts (`2`, `4`, or `6`) so odd-count cues never give the answer away.
10. Noise policy: each seed icon may receive `0..2` subtle Prism-style edits (`blur`, `downsample`, `jpeg`, `noise`) before compositing; the mirrored counterpart is derived from the edited seed sprite, so noise does not break the exact symmetry contract.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_relation_v1`
2. `task_family_key`: `reference_grid_mirror_symmetry_relation`
3. `task_key`: `relation_query`
4. Answer+evidence JSON shape: `{"evidence":["B","E"],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: the family stem establishes the Reference-vs-Scene labeled-grid layout; task wording asks only about matching mirror symmetry and clarifies that the relevant symmetry types may be vertical, horizontal, diagonal, or both vertical and horizontal axes.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching Scene labels are sampled first, then the cell patches are generated from that exact match trace; `answer_gt` and `evidence_gt` both come from the same sampled label set.
3. Reject/resample conditions: unsupported count config, empty icon pool, palette-separation failures, or inability to render exact symmetric / exact non-symmetric cell patches under the configured gap and margin constraints.
4. No-auto-relaxation guarantee: generation fails on unmet symmetry/layout constraints instead of weakening the exact mirror-symmetry contract.
5. Semantic-unit rule: evidence stays at the cell-label level because the task asks about whole-cell mirror symmetry, not about one icon bbox inside a cell.
6. Trace style metadata records the sampled palette, cell-grid styling, patch gap/margin settings, icon-count choices, and the per-seed noise ranges used during patch generation.
7. Balanced defaults: the task uses one fixed-grid count resolver that keeps the `6` Scene-cell layout stable and cycles the feasible `0..4` answer support deterministically across `_sampling_index` sweeps while still remaining stable under task-review sampling without `_sampling_index`.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_icons_relation_mirror_symmetry_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_icons_relation_mirror_symmetry_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`

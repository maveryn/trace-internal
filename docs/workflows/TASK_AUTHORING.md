# TRACE Task Authoring Guide

Use this as the implementation checklist for new or modified tasks.

## 1) Before coding
1. Confirm taxonomy: `domain`, `task_group`, `task_id`.
2. Task-id format is required: `task_<domain>_<task_group>_<task_name>` (lowercase snake_case).
3. Task module filename is required: `<task_name>.py` in the documented domain layout. Default layout is `trace/tasks/<domain>/<task_group>/`; tile is the current exception and keeps concrete tasks flat under `trace/tasks/tile/<task_group>_<task_name>.py`.
4. Confirm family/variant fit using `docs/domains/TASK_FAMILY_VARIANTS.md` before introducing a new task group.
5. Define task contracts:
   - scene,
   - task variants,
   - answer type,
   - evidence type(s),
   - constraints/rejection policy.
6. Check shared helpers first:
   - `trace/core`
   - `trace/tasks/shared`
   - `trace/tasks/<domain>/shared`
   - existing task-group shared modules (for example `trace/tasks/<domain>/<task_group>/*_base.py`) or tile-domain shared modules under `trace/tasks/tile/shared/`
7. Keep helper placement at the narrowest reusable layer.

## 2) Required implementation behavior
1. Add the task module in the documented domain layout. Default is `trace/tasks/<domain>/<task_group>/<task_name>.py`; tile tasks live at `trace/tasks/tile/<task_group>_<task_name>.py`.
2. Register task with `@register_task`.
3. Import the task module in `trace/tasks/__init__.py` so registration executes at runtime.
4. Keep prompt text in external bundles only.
5. Emit `TaskOutput` with:
   - typed `answer_gt`,
   - typed `evidence_gt`,
   - `trace_payload`,
   - `task_versions`,
   - active `prompt`,
   - `prompt_variants` (both modes when supported).
6. Keep `trace_payload` complete with:
   - `scene_ir`,
   - `query_spec` (with prompt metadata),
   - `render_spec`,
   - `render_map`,
   - `execution_trace`,
   - `witness_symbolic`,
   - `projected_evidence`.
7. If the prompt-facing evidence is symbolic rather than geometric (for example `label_set`, `integer`, or `integer_list`), still emit pixel-space witness projections in `projected_evidence` when inspection overlays need to highlight the supporting objects.
8. Ensure answer/evidence/witness come from the same execution trace.
9. Enforce unique final answer by construction.
10. Use bounded resampling; never auto-relax semantic constraints.
11. Emit complexity (`complexity_score`, `complexity_components`).
12. Treat `complexity_score` as within-task normalized difficulty only; do not treat it as a cross-task or cross-domain scale.
13. Emit normalized `complexity_components` in `[0,1]`; if raw diagnostics are useful, keep them in trace/debug payloads rather than in the primary complexity map.
14. Keep raw-to-normalized transforms in task/domain code; domain/task-group policy should own criteria weighting and activation.
15. Domain-level complexity criteria must be applicable to every task in the domain; task-group criteria must be applicable to every task in the family where they are declared.
16. Task-level complexity criteria or weight overrides are allowed but should be rare; use them only when a task materially breaks the family pattern.
17. Use `skills/task-complexity/SKILL.md` whenever a patch introduces or revises a complexity policy.
18. When a domain already has a shared complexity helper/policy layer, keep active criteria and weights in domain/task-group config and emit normalized criterion values through that shared helper instead of embedding new task-local weight constants.
19. When sibling tasks in one family differ only by the queried icon attribute (for example type/color/orientation/size counting), keep them on the same family-level complexity weights and vary only the task-local normalized criterion measurements that reflect the distinguishing ambiguity knob.
20. For icon relation tasks that share one family-level complexity policy, keep the relation weights stable and express task differences through task-local normalized `spatial_reasoning`, `ambiguity`, and `clutter` measurements (for example strip span, occlusion overlap/color separation, or symmetry-variant load) instead of forking per-task scoring policies unless a task truly breaks the family pattern.
21. For icon transformation tasks that share one family-level complexity policy, keep the transformation weights stable and express task difficulty through task-local normalized `rule_inference`, `ambiguity`, and `clutter` measurements (for example transform-family difficulty, available transform support, distractor family similarity, and pair-cell readability) rather than cloning new task-local weight tables.
22. For icon sequence tasks that share one family-level complexity policy, keep the sequence weights stable and express task difficulty through task-local normalized `rule_inference`, `visual_scan`, `ambiguity`, and `clutter` measurements (for example row length, visible icon count, missing-position difficulty, and inverse step size) rather than falling back to count-only proxies.
23. For geometry comparison tasks that share one family-level complexity policy, keep the comparison weights stable and express task difficulty through task-local normalized `visual_scan`, `comparison_reasoning`, `ambiguity`, and `output_burden` measurements (for example object count, direct-vs-derived quantity load, winner-gap closeness, and graph-point evidence cardinality) rather than keeping ad hoc `object_count + gap` score formulas in each task.
24. For geometry counting tasks that share one family-level complexity policy, keep the counting weights stable and express task difficulty through task-local normalized `visual_scan`, `classification_reasoning`, `ambiguity`, and `output_burden` measurements (for example object count, class-subtlety by queried variant, target-density balance, and label-set evidence size) rather than keeping generic `object_count + target_count` proxies in sibling task modules.
25. For geometry measurement tasks that share one family-level complexity policy, keep the measurement weights stable and express task difficulty through task-local normalized `visual_scan`, `measurement_precision`, `ambiguity`, and `output_burden` measurements (for example source/shape variant load, canonical-value closeness, answer-format precision burden, and evidence point cardinality) rather than leaving each task on an unrelated score formula tied only to answer magnitude.
26. For geometry analytical tasks that share one family-level complexity policy, keep the analytical weights stable and express task difficulty through task-local normalized `visual_scan`, `analytical_reasoning`, `ambiguity`, and `output_burden` measurements (for example required-annotation count, solid/formula difficulty, variant confusability, and answer-format plus evidence-map burden) rather than keeping task-local score formulas tied mainly to variant constants or answer magnitude.
27. When one analytical task has multiple semantic variant axes (for example `shape_variant` plus `reasoning_mode`), fold those axes into the same family-level normalized `analytical_reasoning` and `ambiguity` measurements instead of inventing a parallel task-local weighting scheme for each axis.

## 3) Prompt rules
1. Bundle path: `prompts/<domain>/<task_group>/<bundle>.json`.
2. Required template layers:
   - task family,
   - task,
   - optional task variant,
   - output mode (`answer_only`, `answer_and_evidence`).
3. Deterministic variant selection only.
4. Record prompt metadata in trace payload.
5. Keep exactly 5 high-quality variants per required template list.
6. Both output modes must include explicit JSON response-format instructions via slots:
   - `answer_only`: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - `answer_and_evidence`: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Every JSON example shown in prompts (both `answer_only` and `answer_and_evidence`) must itself be a valid answer for that task/variant contract (key order, value type, and evidence cardinality/semantics).
8. For point-based evidence examples, use simple canonical non-degenerate layouts so the example still represents a valid shape/measurement cue.
9. If evidence cardinality/shape differs by variant (for example triangle vs quadrilateral), provide variant-specific `json_example_*` slots and select them deterministically from variant context.
10. If the answer meaning changes across variants even with similar evidence shape (for example area vs perimeter over the same polygon points), prefer variant-specific `json_example_*` slots over generic placeholder examples.
11. If a variant changes the semantic transform over the same displayed scene (for example `minutes_after` or `minutes_before` on one shown clock), generate prompt JSON examples that match the active transformed answer instead of reusing the direct-readout example answer.
12. If graph-paper evidence does not require label identity for verification, prefer coordinate-only evidence (`graph_point` for one point, `graph_point_set` for multiple points) and keep any labeled correspondence in projected trace metadata rather than the primary evidence payload; name pixel-space trace projections with a `pixel_` prefix (for example `pixel_point_set`) so they are not confused with prompt-facing evidence types.
13. If scene/layout capacity changes which answers are feasible, choose the target answer from the feasible support before placement so layout does not silently bias the answer distribution.
14. If that feasibility probe is reusable across sibling variants (for example polygon-side variants sharing one target-conditioned sampler), implement it in a domain-shared helper instead of task-local resampling code.
15. If one variant still collapses to a tiny feasible answer set under a generic sampler, switch that variant to a constructive sampler that directly realizes broader valid targets while preserving the task contract.
16. If a prompt slot value is static for a task (for example a fixed question stem), store it in prompt config/template data rather than task-module constants.
17. Favor natural, image-led wording in template stems; do not pad bundles with low-quality paraphrases just to increase variant count.
18. Keep `question_text` semantic-only when task templates already carry formatting or rounding instructions; avoid repeating the same instruction across prompt layers.
19. When a task prompt refers to a specific color, pass the color to templates as a combined label `<color_name> [#RRGGBB]` so color-name ambiguity is reduced consistently across the repo.
20. For multi-object counting tasks, label whole objects and use sorted `label_set` evidence unless geometry coordinates are truly necessary for verification.
21. For mixed-shape classification/counting tasks, enforce visible separation between visually adjacent classes (for example circles vs ellipses) in the sampler itself instead of leaving borderline cases to human interpretation.
22. For polygon classification/counting tasks, keep the convex/concave predicate in one shared geometry helper and reject `degenerate` near-flat or self-intersecting polygons instead of encoding one-off visual heuristics inside each task.
23. For reference-panel icon tasks, keep prompt wording anchored on the reference-vs-scene relationship and use scene-only `bbox_set` evidence in final image coordinates; store the reference box in trace metadata instead of the user-facing evidence payload.
24. For curated-icon tasks with Prism-style color variation, sample per-instance palettes through the shared icon-style helper, keep palette colors separated from panel/background anchor colors, and record the sampled palette or final tint assignments in trace metadata instead of leaving color randomness implicit.
25. For reference-scene icon color-matching tasks, construct the positive/negative sets from explicit tint assignments rather than hoping random palette draws realize the requested count, and keep any stricter color-separation threshold as a task-level config override.
26. For reference-scene icon counting tasks that mimic Prism, sample `target_count` and `distractor_count` from their explicit supports, derive `object_count` from the pair, and place the scene icons with an explicit overlap cap; keep any subtle icon noise per-instance before compositing and record those edits in trace metadata rather than applying an untracked final-image corruption pass.
27. For icon transformation tasks that compare pairwise rules, show the transformation explicitly in a Reference pair and use labeled Scene cells plus `label_set` evidence so the model grounds the matching rule on visible cells rather than hidden transform ids or bboxes.
28. For tasks whose evidence is an ordered sequence (for example chart readout values), define the evidence order from one explicit source such as prompt query order and record that ordering key in trace metadata; do not alphabetize or otherwise normalize sequence evidence whose positions have meaning.
29. For anchored icon relation tasks, keep the Anchor visibly marked in the Scene panel, exclude it from the counted candidate set, evaluate the directional predicate strictly from rendered bboxes, mix distractors across same-type wrong-side plus different-type queried-side cases so the task cannot be solved by icon identity or side occupancy alone, and enforce a Prism-style relaxed margin rule for same-type wrong-side distractors so they lie mostly outside the queried region instead of becoming near-miss positives.
29. If one-sided relation scenes still look visually biased when positives are numerous, make the distractor support depend on the sampled target count (for example `distractor_count >= target_count + 1`) through the shared counting sampler rather than relying on ad hoc resampling inside one task.
30. For icon attribute-binding tasks, build most distractors from explicit partial matches (for example `2-of-3` or `1-of-3` queried attributes) instead of mostly all-wrong negatives, so the task really tests attribute binding rather than independent marginal filters.
31. For icon occlusion-order tasks, keep the Reference and Scene cells on one shared icon pair, vary only pair-level styling such as tint/overlap/noise, and use `label_set` evidence over matching Scene cells because the task asks about pair-level front/back order rather than about boxing one icon.
32. For icon tasks where size itself is the queried predicate, sample and record explicit nominal sizes per icon through the shared scene renderer, and enforce one minimum size-gap threshold for both targets and distractors so the prompt never relies on “about the same size” judgments.
33. For icon sequence tasks with one missing box, keep the missing box visibly marked (for example `?`), sample the hidden count from the supported answer range before choosing the arithmetic rule, and use a one-box `bbox_set` for the missing cell when that cell itself is the grounding target.
34. For icon two-anchor strip tasks, use a single Scene panel with two visibly marked anchors, keep the anchors exactly aligned on the non-varying axis, exclude anchor icon types from the candidate pool, and evaluate strip membership from icon centers with one explicit boundary margin instead of drawing the strip itself.
35. For icon mirror-symmetry tasks, define one explicit rendered-image symmetry signature per variant (for example vertical-only, horizontal-only, main-diagonal-only, anti-diagonal-only, or vertical+horizontal only), keep the Reference and Scene cell boxes square so diagonal checks are well-defined, use even icon counts across both matching and non-matching cells, and reject any accidental extra-axis symmetries instead of treating them as acceptable matches.
36. For icon tasks whose queried predicate depends on orientation, mirror symmetry, or transform identity, use `assets/icons/non_symmetry.txt` via the shared manifest loader instead of the full curated pool; tasks where symmetry is irrelevant (for example type/color/size/spatial-only tasks) may continue using `all_icons.txt`.
37. For 2D icon pattern-violation tasks, prefer a numbered single-panel grid over an option strip, keep the answer on the violating cell index, keep user-facing evidence on the violating cell bbox, and reject any instance where another supported rule hypothesis would make a different violating cell plausible.
38. For 2D icon size-pattern tasks, define the clean rule over symbolic size levels first and only map those levels to pixel sizes after sampled cell geometry is known; this keeps uniqueness checks stable instead of making them depend on whichever raw pixel ladder happened to fit the cell.
39. For scene-internal icon frequency tasks, define frequency over `icon_id` only and let color/rotation vary independently; otherwise the task silently turns into appearance matching instead of type-frequency reasoning.

## 4) Config/defaults rules
1. Precedence: `domain -> task_group -> task/params`.
2. Use shared defaults helpers; avoid local parsing duplicates.
3. In task-group files, separate shared keys (`shared`) from task-specific keys (`task_overrides.<task_id>`) for `generation`/`rendering`/`prompt`/`sampling`; default to `shared` and use `task_overrides` only for task-specific deltas (legacy flat section keys are unsupported).
4. Keep broadly shared domain visual policy in `configs/domains/<domain>/base.yaml`; use task-group visual only for group-specific overrides.
5. Task-variant weights are resolved inside each task from config/params; builder-level sampling weights apply only across tasks.
6. Visual defaults/noise should route through shared visual modules.
7. Geometry `measurement` tasks should keep graph-paper/anchor alignment policy consistent; geometry `analytical_2d` tasks should use non-graph-paper backgrounds unless a task explicitly requires visible grid cues.
8. Tile-domain tasks should use non-grid backgrounds unless the task contract explicitly depends on an external grid distinct from the board itself.
9. For sibling variants of one objective family (for example area/perimeter), keep shared generation/prompt/trace flow in one task-group shared base helper and keep task modules thin.
10. Required prompt/config slots should be enforced with fail-fast shared helpers (no hardcoded fallback prompt literals in task code).
11. If the same fallback constants are used by multiple sibling tasks, move them to a task-group shared defaults module.
12. For cross-domain shared utilities, keep global fallback constants in the shared utility module and treat domain/task-group config keys as optional overrides.
13. For analytical scenes with free-form numeric annotations, reserve explicit border margin and use collision-aware local placement so labels/value text do not sit directly on geometry or hug the canvas edge.
14. For analytical composite/shaded objectives, keep region-fill semantics in the shared analytical scene helper so sibling tasks can reuse shaded-target and cutout rendering without task-local draw-order hacks.
15. If a board/scene family needs non-square image sizes, extend the shared visual/background path to accept rectangular canvases instead of creating task-local background renderers.
16. If a non-measurement geometry task-group needs its own background policy (for example counting on solid backgrounds), load geometry background/noise defaults for that task group explicitly instead of importing measurement-scoped constants.
17. For counting/classification tasks with overlapping textbook definitions (for example isosceles vs equilateral), encode the intended exclusivity directly in the prompt/config wording instead of assuming one convention.
18. For counting tasks where the answer is the matched-object count itself, prefer global target-count support sampling (for example `resolve_counting_cardinality_pair(...)`) over choosing object count first when the latter would skew answers toward smaller counts.
19. For polygon class-counting tasks with bulkier objects, use the roomier counting slot layout helper and a strict shared convexity classifier so object labels stay readable and class membership does not depend on ambiguous borderline outlines.
20. For curated-asset icon tasks, resolve manifest ids through one shared asset loader instead of assuming manifest ids and SVG filenames match exactly; record the chosen manifest in query trace metadata.
21. When adding a new chart `scene_variant`, update every active chart task group that shares the labeled-chart scene contract in the same patch: renderer support, `scene_variant_weights`, `object_description_<scene_variant>` prompt defaults, behavior tests, and regenerated task reviews should all land together.
22. When sibling tasks inside one task group use disjoint `task_variant` vocabularies, keep `task_variant_weights` under `task_overrides.<task_id>` instead of `generation.shared` so merged defaults do not leak inactive variants across tasks.

## 5) Sampling rules
1. Global sampling unit is `task`.
2. Task-variant sampling occurs inside each task.
3. Default `P(task_variant|task)` is uniform unless overridden.
4. If one task has both a semantic variant axis and a visual-representation axis, keep `task_variant` for the semantic/query axis and record the visual axis separately as `scene_variant` in trace/query metadata instead of exploding the task into a cross-product of near-duplicate tasks.
5. Keep answer sampling as broad as constraints allow and validate with the standard answer-distribution checks.
6. For geometry placement with lattice offsets, compute anchor bounds from the selected candidate (not global worst-case margins).
7. Avoid tiny fixed structure banks; randomize both structural and visual factors whenever constraints allow.
8. For tasks with both source categories and answer targets, sample both distributions explicitly and verify realized distributions.
9. For deterministic balance over generated prefixes, use builder `_sampling_index` (not hashed `instance_seed`) when cycling categories/answers; if `_sampling_index` is absent, fall back to a namespaced deterministic index so target-answer choice does not couple to unrelated seed-driven decisions such as task-variant selection.
10. For fixed-cardinality tasks with a very small answer support (for example six cells with answers `0..4`), make the answer-balancing path explicit in task code and verify it under task-review sampling too; review runs do not inject builder `_sampling_index`, so tiny supports can skew if they rely only on generic hash-based balancing.
11. If a target answer is chosen from a feasibility probe before layout, also propagate the probe's minimum required scene capacity (for example graph-cell count/span) into layout sampling; otherwise a globally feasible answer can still fail after the scene size is sampled.
12. When changing answer/evidence/variant contracts, remove deprecated helper paths and stale trace fields in the same patch.
13. When adding non-semantic visual diversity axes (for example named accent colors or bezel styles), keep those axes out of prompt wording and answer semantics unless the task explicitly queries them; record the resolved visual choices in trace/render metadata so review artifacts stay interpretable.
13. For derived analytical geometry tasks, do not force integer targets if that collapses scene variety; prefer integer givens plus a numeric answer rounded to one decimal place when the natural formula yields irrational lengths.

## 6) Minimal test checklist
1. Determinism for fixed seed.
2. Answer/evidence consistency with execution trace.
3. Prompt metadata and placeholder validity.
4. Build integration smoke.
5. Constraint-specific tests (for example non-overlap, uniqueness).
6. Feasibility sanity at max candidate count under default render ranges (for geometry/layout-heavy tasks).
7. Prefer extending shared family contract tests instead of duplicating full contract checks in every task file.
8. Keep tests behavior-focused and compact: merge overlapping checks rather than adding parallel literal-default tests for the same contract.

Run:
```bash
PYTHONPATH=. pytest -q
```

## 7) Required docs updates (same change)
1. `docs/tasks/<task_id>.md`
2. `docs/tasks/README.md` (task links must match active task set)
3. `docs/project/STATUS.md` (if behavior changed)
4. `docs/core/PROMPT_SYSTEM.md` (if active prompt bundles or task-to-bundle mappings changed)
5. `docs/core/SYSTEM_ARCHITECTURE.md` (if active domain/task module inventory or module boundaries changed)
6. `docs/workflows/SHARED_UTILITIES.md` (if shared helpers moved/added)
7. `docs/workflows/BUILD_VALIDATION.md` or `docs/workflows/VALIDATION_ERROR_CODES.md` (if validation behavior changed)
8. `docs/workflows/CODE_REVIEW_GUIDELINES.md` for reusable findings.

## 8) Reuse anti-patterns
Use `docs/workflows/CODE_REVIEW_GUIDELINES.md` Section 2 as the canonical anti-pattern list.

## 9) Task review workflow
For new tasks or distribution-changing changes, run the standardized review workflow:
```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full
```

The review scripts default to all visible CPUs; pass `--workers <n>` when you want to limit parallelism explicitly.

This writes review artifacts under `task-reviews/<domain>/<task_id>/`:
- `random_review_100.json` (100 random samples, includes variant/sampling-axis distributions)
- `distribution_review.json` (100 answers per variant when variants exist; otherwise single 100-sample check)
- `<task_id>.xlsx` (25 manual-inspection samples per variant, one sheet per task variant)

Prompt wording rule:
- when the task-family stem already establishes the image/diagram context, keep the task-layer line focused on the question itself instead of repeating phrases like `from the image` or `from the diagram`.
- when graph-paper geometry must stay strictly inside the plotted grid, compute scene-capacity bounds against the visible interior cells (not just the raw sampled `graph_cells` target) before locking target answers or placements.
- when an icon task's rule is fully visible inside one scene panel, prefer a single-panel layout over a decorative reference+scene layout so scene capacity stays focused on the actual reasoning target.
- when an icon sequence task asks for a violating or missing position, prefer visible in-scene cell labels plus one-box `bbox_set` evidence over a separate option strip; the row itself should ground both the answer and the evidence target.
- for labeled node-link graph tasks, keep node labels as the prompt-facing identity/evidence contract and treat layout as a non-semantic scene variation; answers should come from adjacency/topology rather than whichever node happened to render in a certain position.
- for graph tasks with added visual diversity, vary whole-image style axes such as label format, node glyph, named node color, or global layout transform only when they remain non-semantic for the task; if a future task queries one of those axes, promote it from style noise to an explicit task contract.
- if a graph task supports both undirected and directed variants, make directionality explicit in both prompt wording and trace metadata (`degree` vs `in-degree` vs `out-degree`) and render directed edges with arrowheads; do not rely on the image alone to disambiguate the semantic contract.
- if a directed graph task asks about reachability from one queried node, say explicitly whether the queried node itself is included in the answer/evidence set and verify the witness from successor adjacency after all extra-edge decoration; do not rely on convention alone for “reachable from itself.”
- if a graph task includes the queried node itself in the answer/evidence set (for example same-component queries), say that explicitly in the prompt and evidence hint rather than leaving “including the queried node” implicit.
- if a graph task exposes one “largest” or otherwise globally maximal witness component via a single `label_set`, enforce that winner’s uniqueness by construction; ties should be rejected rather than broken implicitly by label order or layout.
- if a graph task assumes exactly one cycle, construct a unicyclic graph by design and verify the finalized adjacency still has one cycle before exposing answer/evidence; do not infer uniqueness from a partial construction recipe alone.
- for graph tasks, treat `label_set` evidence as unordered semantically and canonicalize it internally only for determinism; only path-like tasks should require an explicitly ordered label sequence.
- for graph edge-witness tasks, use a graph-native `edge_set` contract where each witness is a two-label endpoint pair; treat both the endpoint pair and the outer witness set as unordered semantically, and keep `pixel_edge_set` only in projected trace metadata for review overlays.
- for weighted graph tasks, render edge-weight labels from the same canonical edge-to-weight map used in trace/verifier logic; do not let the renderer invent a separate edge ordering or duplicate weight assignment path.
- for graph path tasks, use an ordered graph-native contract such as `label_path` only when node order is truly semantic, and say explicitly whether the path includes both queried endpoints.
- for graph ordered-but-nonpath tasks, use an ordered graph-native contract such as `label_sequence` rather than overloading `label_path`; the JSON shape may stay the same ordered label list, but verifier semantics must come from the task-specific ordering rule instead of edge adjacency between consecutive labels.
- for temporal compare tasks that answer with one visible clock label, make sure the visible label support itself is broad enough for answer-distribution review; if only two to four labels can ever be correct, widen the scene or rethink the answer contract instead of relying on cross-variant mixing.
- when a task renders text inside compact glyphs or cells, fit the font against the available box instead of assuming one fixed font size will work for every label variant; multi-character labels and alternate glyph shapes should stay readable without overflowing the witness object.

Use `--mode inspection` when only visual/prompt inspection is needed and distribution checks should be skipped.

Required answer-distribution checks:
- `unique_answers >= 5`
- `max_answer_frequency < 25%`
- apply checks per `task_variant`; task-level pass requires every variant to pass.
- zero collected samples for a review slice is a hard fail (`no_samples_collected`).

Numeric answer-distribution summaries:
- task-review reports still include `five_bin_numeric` and `max_five_bin_frequency` for inspection,
- treat those as informational by default rather than hard pass/fail gates unless a task family adopts an explicit tighter rule.

For quick distribution-only runs:
```bash
PYTHONPATH=. python scripts/check_task_answer_distribution.py --tasks <task_id>
```

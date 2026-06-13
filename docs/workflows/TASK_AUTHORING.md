# TRACE Task Authoring Guide

Use this as the implementation checklist for new or modified tasks.

## 1) Before coding
1. Confirm public taxonomy: `domain`, `scene_id`, `task_id`.
2. Public task ids must use taxonomy-v0 form `task_<domain>__<scene_id>__<task_slug>` (lowercase snake_case inside each segment).
3. Task module filename is required: `<objective_contract>.py` in the documented domain layout. Review-candidate scenes use `trace/tasks/<domain>/<scene_id>/<objective_contract>.py`.
4. Confirm scene/task/query fit using `docs/core/TAXONOMY.md`,
   `docs/core/TASK_UNIT_POLICY.md`, and the matching domain contract doc in
   `docs/domains/`. Public tasks split by scene-contract stability plus
   task-contract fields: `answer_schema`, `annotation_schema`, and concrete
   `program_schema`.
   Query ids cover only task-local operators or parameters inside the same
   stable contract.
5. Define task contracts:
   - `scene_contract` (`domain`, `scene_id`, renderer grammar, and stable
     `view_contract` when relevant),
   - `task_slug`,
   - `task_contract.answer_schema`,
   - `task_contract.annotation_schema`,
   - `task_contract.program_schema`,
   - `parameter_axes` and constraints/rejection policy.
   The program schema must name the actual candidate set, operand roles,
   derived computation, final operator, output binding, and annotation role
   template. Do not ship a task whose taxonomy contract is only a generic
   placeholder such as `select_by_rank(items, metric, rank)`.
   Taxonomy audit artifacts additionally derive `program_arguments_json` from
   those fields to show allowed in-task argument values. Keep query ids and
   metadata descriptive enough that this argument metadata can be inferred or
   manually overridden during taxonomy review.
   Use **query id** as the human-facing name for task-internal branches and
   `query_id` as the canonical field for internal replay selectors.
   `task_id` is the only public task selector: do not use caller
   `params["query_id"]` to choose between public objectives.
6. Check shared helpers first:
   - `trace/core`
   - `trace/tasks/shared`
   - `trace/tasks/<domain>/shared`
   - existing scene-local shared modules under `trace/tasks/<domain>/<scene_id>/shared/`
7. Keep helper placement at the narrowest reusable layer.

## 2) Required implementation behavior
1. Add the task module in the documented domain layout. Review-candidate scenes use `trace/tasks/<domain>/<scene_id>/<objective_contract>.py`.
2. Register task with `@register_task`.
3. Import the task module in `trace/tasks/__init__.py` so registration executes at runtime.
4. Keep prompt text in external bundles only.
5. Emit `TaskOutput` with:
   - typed `answer_gt`,
   - typed `annotation_gt`,
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
   - `projected_annotation`.
7. Public annotation must be image-level: use active homogeneous types such as
   `bbox_set`, `bbox_sequence`, `point_set`, `point_sequence`, or
   `point_pair_set`, plus `keyed_point_map`, `keyed_point_set_map`,
   `keyed_bbox_map`, or `keyed_bbox_set_map` when witness role identity is
   part of the annotation contract. Semantic labels, ids, and
   graph/grid coordinates may be used internally during generation, but must
   not be the persisted public annotation contract.
8. Prompt-facing annotation should localize the semantic visual object or
   primitive used as input annotation, not the answer option and not standalone
   numeric annotations. Treat labels, measurements, and readout text as
   attributes of the nearest visual object/primitive unless the task is
   explicitly a text/readout task. Keep the annotation bboxes in `render_map`
   or trace metadata when useful, but do not expose them as public annotation by
   default.
9. If witness roles matter or an unordered set would make the requested
   annotation ambiguous, use only the active global homogeneous keyed
   annotation names `keyed_point_map`, `keyed_point_set_map`,
   `keyed_bbox_map`, or `keyed_bbox_set_map`; do not invent
   domain-specific names. Prefer keyed annotation whenever the verifier should
   check that the model bound each visual witness to a specific semantic role,
   such as `outer_shape` versus `shaded_region`, `source_panel` versus
   `target_panel`, `reference_item` versus `candidate_item`, or
   `input_force` versus `output_force`. The model-facing annotation value is
   just the inner object, for example
   `{"A": [123, 245], "B": [310, 240]}` or
   `{"A": [[123, 245], [140, 245]], "B": [[310, 240]]}` for keyed set maps.
   Avoid mixed point/box annotation; consider changing the task contract first.
10. Use unordered set annotation (`bbox_set`, `point_set`, `point_pair_set`) only
   when witness identity or order does not matter for reward. This is usually
   right for counting tasks where annotation cardinality is the answer, or for
   homogeneous witness sets where any permutation is semantically equivalent.
   Do not use an unordered set merely because it is easier to emit when the
   task actually depends on binding named roles to the correct regions.
11. Selected option bboxes are allowed only for visual option-image tasks where
   the chosen option is a complete candidate image/panel and the scene includes
   a source/reference/original image or region that the option matches,
   completes, transforms from, or belongs to. Do not use option bboxes for
   ordinary MCQ choices, numeric/text answer labels, or lettered candidate
   objects.
12. Annotation hints should name the witness category clearly without leaking the
   answer. In particular, for counting tasks do not state a fixed annotation
   cardinality when that cardinality is the answer; say to return boxes for
   the matching/countable objects instead. Annotation-format prompt text must be
   positive-only: specify what annotation to return, not what to omit. Keep
   exclusions and non-witness policy in task docs, verifier metadata, or audit
   notes rather than model-facing annotation instructions.
13. Do not emit `reward_contract` from task code; builder derives it from the public `answer_gt.type` / `annotation_gt.type` contract.
14. If a task changes its public answer or annotation type, update `task-reviews/RLVR_ANNOTATION_REWARD_MAPPING.md` in the same patch.
15. Ensure answer/annotation/witness come from the same execution trace.
16. Enforce unique final answer by construction.
17. Use bounded resampling; never auto-relax semantic constraints.
18. Non-semantic visual variation must not create answer shortcuts. If color,
   style, size jitter, marker style, or layout variation is not itself queried,
   do not assign it from answer-defining slots, verifier ranks, relation
   status, or fixed construction order. Semantic visual attributes are allowed
   only when the task explicitly queries them and the verifier records the same
   predicate metadata.
19. Do not emit scalar difficulty fields from new or migrated tasks.
20. If raw diagnostics are useful for debugging a task, keep them in
    task-specific trace/debug payloads and do not expose them as a training ABI
    field, sampler input, or review acceptance gate.
21. Enforce the query-id boundary:
    - every review-candidate task must declare `supported_query_ids`; tasks
      with no internal branch use `("default",)`;
    - caller-provided `query_id` is accepted only when it is in that task's
      `supported_query_ids`; unsupported values fail fast;
    - input-only legacy `query_variant`, when still accepted, follows the same
      validation rule and must not be emitted in generated metadata;
    - resolve/validate `query_id` only in the public task file, then pass
      semantic arguments into shared helpers;
    - generated outputs record the selected `query_id` as metadata, but
      `query_id` must not choose between public objectives.

## 3) Prompt rules
1. Bundle path: `prompts/<domain>/<scene_id>/<bundle>.json` for migrated
   scene packages.
2. Required template layers:
   - scene,
   - task,
   - optional query layer keyed by `prompt_query_key`; this may differ from
     runtime `query_id` for fixed-objective tasks that emit `query_id="default"`,
   - output mode (`answer_only`, `answer_and_annotation`).
3. Deterministic template selection only.
4. Record prompt metadata in trace payload.
5. Keep exactly 5 high-quality templates per required template list.
6. Both output modes must include task-specific JSON response-format guidance via slots:
   - `answer_only`: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - `answer_and_annotation`: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
   - the shared `json_output_contract*` slots are retained for bundle compatibility, but the generic schema sentence is stripped from rendered user prompts because the RLVR system prompt now carries that contract
   - rendered output-mode instructions should keep task-specific annotation/answer hints and examples, not tell the model to answer with only that object or forbid intermediate reasoning; the RLVR system prompt asks the model to end with a final JSON object
   - example JSON values must represent the actual answer contract. If a label answer can be a multi-character visible label, the example must use a multi-character label rather than a one-letter placeholder. One-character examples are only appropriate when the rendered answer support is intentionally one-character, such as option letters or panel IDs.
   - optional metadata-generated rationale targets must follow `TEMPLATED_RATIONALE_TARGETS.md`; they should not change prompt wording, verifier semantics, final JSON schema, or reward behavior unless explicitly approved
   - rationale-template grouping must not override the task contract; if a
     branch changes answer schema, annotation schema, program schema, or
     query-facing view contract, split the public task instead of only adding
     a new `query_id`
7. Every JSON example shown in prompts (both `answer_only` and `answer_and_annotation`) must itself be a valid answer for that task/query contract (key order, value type, and annotation cardinality/semantics).
8. For point-based annotation examples, use simple canonical non-degenerate layouts so the example still represents a valid shape/measurement cue; do not reuse one placeholder coordinate for multiple keyed roles that should be visually distinct.
9. If annotation cardinality/shape differs by query branch (for example triangle vs quadrilateral), provide branch-specific `json_example_*` slots and select them deterministically from query context.
10. If the answer meaning changes across query branches even with similar annotation shape (for example area vs perimeter over the same polygon points), prefer branch-specific `json_example_*` slots over generic placeholder examples.
11. If a branch changes the semantic transform over the same displayed scene (for example `minutes_after` or `minutes_before` on one shown clock), generate prompt JSON examples that match the active transformed answer instead of reusing the direct-readout example answer.
12. If graph-paper annotation does not require label identity for verification, prefer pixel-space point annotation (`point_set` or `point_sequence`) and keep graph-coordinate correspondence in private trace metadata rather than the primary annotation payload.
13. If scene/layout capacity changes which answers are feasible, choose the target answer from the feasible support before placement so layout does not silently bias the answer distribution.
14. If a task exposes explicit answer-support lists in config, intersect those lists with the constructively feasible subset for the active scene/query family before balanced sampling and reject explicit infeasible answers immediately; do not leave impossible support values in the live sampling path and hope review-time resampling avoids them.
15. Numeric answer supports should be contiguous ranges unless task semantics make an interior value impossible. Do not delete a middle answer value during calibration only because that bucket is weak; tune construction, rendering, or prompting, move a range endpoint, or document the semantic infeasibility.
16. Calibration and dataset generation must use the same seeded sampler. Do not add review-only balancing paths or hidden prefix-cycling parameters to make a small review sample pass distribution checks.
17. If that feasibility probe is reusable across sibling query branches (for example polygon-side branches sharing one target-conditioned sampler), implement it in a domain-shared helper instead of task-local resampling code.
18. If one branch still collapses to a tiny feasible answer set under a generic sampler, switch that branch to a constructive sampler that directly realizes broader valid targets while preserving the task contract.
19. If a prompt slot value is static for a task (for example a fixed question stem), store it in prompt config/template data rather than task-module constants.
20. Favor natural, image-led wording in template stems; do not pad bundles with low-quality paraphrases just to increase query-id count.
21. Avoid task-generated `question_text` for final model-facing wording. Use prompt-bundle query templates plus structured slot values instead; if an older helper still carries `question_text` for migration metadata, keep it semantic-only and do not repeat formatting or rounding instructions across prompt layers.
22. Keep task/query wording off the answer-only-response pattern (`Answer with ...`, `Respond with ...`, `Return only ...`) when output-mode templates already specify the structured answer format.
23. Keep prompt layers concise and non-overlapping: scene templates should describe the visual scaffold, task templates should add only a needed operation hint, query templates should ask the actual question, and output-mode templates should only state field hints/examples.
24. Scene templates should use ordinary visual framing such as `The image shows ...`, `The chart shows ...`, `The table shows ...`, `The diagram shows ...`, or `The board shows ...`.
25. Avoid telegraphic or imperative scene stems such as `Shown is`, `Displayed is`, `Use this`, `Read this`, `Look at`, `The image contains`, or `The chart is`.
26. Prompt-facing scene/task/query wording should describe visible, task-relevant content only. Do not mention absent properties or implementation-negative facts such as `unlettered`, `unlabeled`, `without labels`, `no option panel`, or `not shown` unless the task explicitly asks the model to contrast present versus absent visual elements.
27. If a query template already contains the full question, use empty task templates with `allow_empty_task_templates: true` rather than adding a redundant task-layer sentence.
28. Before and after broad prompt edits, run `PYTHONPATH=. python scripts/audit_prompt_concision.py --tasks <task_ids>` to inspect rendered prompt length and repeated scaffolding terms. For all-task coverage, add `--variant-coverage --samples-per-query-id 1 --include-all-prompts --output samples/prompt_concision_audit_all.md`.
29. When a task prompt refers to a specific color, pass the color to templates as a combined label `<color_name> [#RRGGBB]` so color-name ambiguity is reduced consistently across the repo.
30. For multi-object counting tasks, label whole objects for readability but ground annotation with whole-object `bbox_set` or object-center `point_set` annotation.
29. Required/read-off text must be rendered with the shared text-legibility policy: sample nonsemantic text ink from the approved readable pool, check contrast against the actual text surface, and record role/color/contrast metadata under `render_spec.text_legibility` or a nested render/style block copied into `render_spec`. All text draw calls should route through `draw_text_traced(...)`, `draw_traced_text(...)`, a readable-text helper, or a domain wrapper that uses them; the task registry also attaches automatically collected drawn-text records under `render_spec.drawn_text.text_legibility`. If a renderer draws multiple text roles on different surfaces, resolve each role separately; do not reuse panel/title text colors for labels drawn inside colored nodes, cells, markers, or objects. Core validation rejects any recorded required text role whose contrast metadata fails. During review, run `scripts/audit_text_legibility.py --strict-renderer-migration` and the runtime coverage mode for the touched domain. Do not use glyph text color itself as an answer, category, class, or filter; encode semantic colors with separate marks, swatches, object fills, outlines, or panels instead.
30. Semantic markers that identify answer-bearing objects, query targets, references, paths, selected cells, highlighted regions, or option cues must use the shared marker-legibility helpers in `trace/tasks/shared/marker_legibility.py` or a thin domain wrapper such as `trace/tasks/games/shared/marking.py` / `trace/tasks/puzzles/shared/marking.py`. Resolve marker colors against the actual drawn surface colors, draw a contrast-safe halo/accent marker, and let the task registry record the collected metadata under `render_spec.drawn_markers.marker_legibility`. Core validation rejects recorded required markers that fail the contrast or Lab-distance thresholds. Do not draw fixed RGB outlines or highlights over variable board, cell, panel, chart, or object fills unless the scene has a documented marker-specific contrast guard.
29. For mixed-shape classification/counting tasks, enforce visible separation between visually adjacent classes (for example circles vs ellipses) in the sampler itself instead of leaving borderline cases to human interpretation.
30. For polygon classification/counting tasks, keep the convex/concave predicate in one shared geometry helper and reject `degenerate` near-flat or self-intersecting polygons instead of encoding one-off visual heuristics inside each task.
31. For reference-panel icon tasks, keep prompt wording anchored on the reference-vs-scene relationship and use scene-only `bbox_set` annotation in final image coordinates; store the reference box in trace metadata instead of the user-facing annotation payload.
32. For curated-icon tasks with per-instance color variation, sample palettes through the shared icon-style helper, keep palette colors separated from panel/background anchor colors, and record the sampled palette or final tint assignments in trace metadata instead of leaving color randomness implicit.
33. For reference-scene icon color-matching tasks, construct the positive/negative sets from explicit tint assignments rather than hoping random palette draws realize the requested count, and keep any stricter color-separation threshold as a task-level config override.
34. For reference-scene icon counting tasks built from the shared curated-icon pipeline, sample `target_count` and `distractor_count` from their explicit supports, derive `object_count` from the pair, and place the scene icons with an explicit overlap cap; keep any subtle icon noise per-instance before compositing and record those edits in trace metadata rather than applying an untracked final-image corruption pass.
35. For icon transformation tasks that compare pairwise rules, show the transformation explicitly in a Reference pair and use Scene-cell `bbox_set` annotation so the model grounds the matching rule on visible cells rather than hidden transform ids.
36. For tasks whose annotation is an ordered sequence (for example chart readout values), define the annotation order from one explicit source such as prompt query order and record that ordering key in trace metadata; do not alphabetize or otherwise normalize sequence annotation whose positions have meaning.
37. For anchored icon relation tasks, keep the Anchor visibly marked in the Scene panel, exclude it from the counted candidate set, evaluate the directional predicate strictly from rendered bboxes, mix distractors across same-type wrong-side plus different-type queried-side cases so the task cannot be solved by icon identity or side occupancy alone, and enforce the relaxed same-type wrong-side margin rule so those distractors lie mostly outside the queried region instead of becoming near-miss positives.
38. If one-sided relation scenes still look visually biased when positives are numerous, make the distractor support depend on the sampled target count (for example `distractor_count >= target_count + 1`) through the shared counting sampler rather than relying on ad hoc resampling inside one task.
39. For icon attribute-binding tasks, build most distractors from explicit partial matches (for example `2-of-3` or `1-of-3` queried attributes) instead of mostly all-wrong negatives, so the task really tests attribute binding rather than independent marginal filters.
40. For icon occlusion-order tasks, keep the Reference and Scene cells on one shared icon pair, vary only pair-level styling such as tint/overlap/noise, and use Scene-cell `bbox_set` annotation over matching Scene cells because the task asks about pair-level front/back order rather than about boxing one icon.
41. For icon tasks where size itself is the queried predicate, sample and record explicit nominal sizes per icon through the shared scene renderer, and enforce one minimum size-gap threshold for both targets and distractors so the prompt never relies on “about the same size” judgments.
42. For icon sequence tasks with one missing box, keep the missing box visibly marked (for example `?`), sample the hidden count from the supported answer range before choosing the arithmetic rule, and use a one-box `bbox_set` for the missing cell when that cell itself is the grounding target.
43. For icon two-anchor strip tasks, use a single Scene panel with two visibly marked anchors, keep the anchors exactly aligned on the non-varying axis, exclude anchor icon types from the candidate pool, and evaluate strip membership from icon centers with one explicit boundary margin instead of drawing the strip itself.
44. For icon mirror-symmetry tasks, define one explicit rendered-image symmetry signature per query branch (for example vertical-only, horizontal-only, main-diagonal-only, anti-diagonal-only, or vertical+horizontal only), keep the Reference and Scene cell boxes square so diagonal checks are well-defined, use even icon counts across both matching and non-matching cells, and reject any accidental extra-axis symmetries instead of treating them as acceptable matches.
45. For icon tasks whose queried predicate depends on orientation, mirror symmetry, or transform identity, use `assets/icons/non_symmetry.txt` via the shared manifest loader instead of the full curated pool; tasks where symmetry is irrelevant (for example type/color/size/spatial-only tasks) may continue using `all_icons.txt`.
46. For 2D icon pattern-violation tasks, prefer a numbered single-panel grid over an option strip, keep the answer on the violating cell index, keep user-facing annotation on the violating cell bbox, and reject any instance where another supported rule hypothesis would make a different violating cell plausible.
47. For 2D icon size-pattern tasks, define the clean rule over symbolic size levels first and only map those levels to pixel sizes after sampled cell geometry is known; this keeps uniqueness checks stable instead of making them depend on whichever raw pixel ladder happened to fit the cell.
48. For scene-internal icon frequency tasks, define frequency over `icon_id` only and let color/rotation vary independently; otherwise the task silently turns into appearance matching instead of type-frequency reasoning.
49. For map-region tasks whose query depends on category rank, make the legend order explicit in the prompt or ask directly about a named legend category; do not require solvers to infer an unstated darker-is-higher convention from the palette alone.
50. For map-region count tasks, keep prompt-facing annotation as the ordered set of counted region bboxes in map reading order; do not switch annotation ordering to legend order just because the query references a legend category.
51. For section-local document checkbox-count tasks, keep prompt-facing annotation on the counted checkbox squares in reading order and allow an empty `bbox_set` when the visible count is zero; do not widen zero-count annotation to the full section or page.

## 4) Config/defaults rules
1. Precedence: domain defaults, then scene defaults, then task/params.
2. Use shared defaults helpers; avoid local parsing duplicates.
3. In scene config files, separate shared keys (`shared`) from task-specific keys (`task_overrides.<task_id>`) for `generation`/`rendering`/`prompt`/`sampling`; default to `shared` and use `task_overrides` only for task-specific deltas (flat section keys are unsupported).
4. Keep broadly shared domain visual policy in `configs/domains/<domain>/base.yaml`; use scene config only for scene-specific overrides.
5. Query-branch weights are resolved inside each task from config/params; builder-level sampling weights apply only across tasks.
6. Visual defaults/noise should route through shared visual modules.
7. Post-render noise may use only non-geometric edits that preserve image coordinates. Shared supported edits live in `trace/core/visual/noise.py` and include blur/downsample/compression, achromatic pixel/sensor noise, luminance-only screen/paper artifacts, mild exposure/contrast shifts, and other coordinate-preserving safe noise types. Do not use crop, translation, rotation, perspective, reflection, or padding changes as noise because those invalidate bbox/point annotation.
8. Keep icon noise per-icon before compositing and recorded per instance; do not add global post-image corruption to icon tasks unless that family is explicitly re-reviewed.
9. Geometry `measurement` tasks should keep graph-paper/anchor alignment policy consistent; full graph-paper/coordinate scenes should resolve the bounded graph-paper panel before projecting objects or annotation. Geometry `analytical` tasks should use non-graph-paper backgrounds unless a task explicitly requires visible grid cues.
10. Cell-board puzzle tasks should use non-grid backgrounds unless the task contract explicitly depends on an external grid distinct from the board itself.
11. For sibling query branches of one objective, keep shared generation/prompt/trace flow in scene-local shared helpers and keep task modules focused on objective ownership.
12. Required prompt/config slots should be enforced with fail-fast shared helpers (no hardcoded fallback prompt literals in task code).
13. If the same fallback constants are used by multiple sibling tasks, move them to a scene-local shared defaults module.
14. For cross-domain shared utilities, keep global fallback constants in the shared utility module and treat domain/scene config keys as optional overrides.
15. For analytical scenes with plotted labels or annotations, reserve explicit border margin and use collision-aware placement so labels/value text do not sit directly on geometry or hug the canvas edge.
16. For analytical panel-selection objectives, keep panel layout, graph-to-pixel projection, and collision-aware label placement in shared helpers rather than task-local drawing forks.
17. If a board/scene grammar needs non-square image sizes, extend the shared visual/background path to accept rectangular canvases instead of creating task-local background renderers.
18. If a non-measurement geometry scene needs its own background policy, load geometry background/noise defaults for that scene explicitly instead of importing measurement-scoped constants.
19. For counting/classification tasks with overlapping textbook definitions (for example isosceles vs equilateral), encode the intended exclusivity directly in the prompt/config wording instead of assuming one convention.
20. For counting tasks where the answer is the matched-object count itself, prefer global target-count support sampling (for example `resolve_counting_cardinality_pair(...)`) over choosing object count first when the latter would skew answers toward smaller counts.
21. For polygon class-counting tasks with bulkier objects, use the roomier counting slot layout helper and a strict shared convexity classifier so object labels stay readable and class membership does not depend on ambiguous borderline outlines.
22. For curated-asset icon tasks, resolve manifest ids through one shared asset loader instead of assuming manifest ids and SVG filenames match exactly; record the chosen manifest in query trace metadata.
23. When adding a new chart `scene_variant`, update every active chart scene that shares the labeled-chart scene contract in the same patch: renderer support, `scene_variant_weights`, `object_description_<scene_variant>` prompt defaults, behavior tests, and regenerated task reviews should all land together.
24. When sibling tasks inside one scene use disjoint query vocabularies, keep query defaults under `task_overrides.<task_id>` instead of `generation.shared` so merged defaults do not leak inactive queries across tasks.
25. For repeated-unit renderers such as cell grids, board tiles, slots, hex cells, stickers, polyomino squares, maze cells, automaton cells, word-search cells, and voxels, add non-semantic unit-size jitter. Try for at least a `2x` span between the minimum and maximum rendered unit size first, but use a narrower documented range when readability, scene fit, or verifier contracts require it. Record the sampled unit size or scale in render metadata and compute public annotation after the final layout.

## 5) Sampling rules
1. Global sampling unit is `task`.
2. Query sampling occurs inside each task.
3. Default `P(query_id|task)` is uniform. Do not add config-level query
   weights for migrated tasks.
4. If one task has both a semantic query axis and a visual-representation axis, keep `query_id` for the semantic axis and record the visual axis separately as `scene_variant` in trace/query metadata instead of exploding the task into a cross-product of near-duplicate tasks.
5. Do not rebuild old consolidated-wrapper behavior by accepting source
   `query_id` params as aliases for public task selection. Retired public task
   ids should be deleted, not preserved as query routers.
6. Keep answer sampling as broad as constraints allow and validate with the standard answer-distribution checks.
7. For geometry placement with lattice offsets, compute anchor bounds from the selected candidate (not global worst-case margins).
8. Avoid tiny fixed structure banks; randomize both structural and visual factors whenever constraints allow.
9. For tasks with both source categories and answer targets, sample both distributions explicitly and verify realized distributions.
10. Sample task axes from the real intended dataset distribution using explicit seeded RNG streams or constructive samplers. If answer values are intended to be uniform, sample them uniformly in the normal generator rather than adding a separate calibration-only cycle.
11. For fixed-cardinality tasks with a very small answer support (for example six cells with answers `0..4`), make the answer-support distribution explicit in the normal task sampler and verify that generated samples follow it.
12. If a target answer is chosen from a feasibility probe before layout, also propagate the probe's minimum required scene capacity (for example graph-cell count/span) into layout sampling; otherwise a globally feasible answer can still fail after the scene size is sampled.
13. When changing answer/annotation/query contracts, remove obsolete helper paths and stale trace fields in the same patch.
14. When adding non-semantic visual diversity axes (for example named accent colors or bezel styles), keep those axes out of prompt wording and answer semantics unless the task explicitly queries them; record the resolved visual choices in trace/render metadata so review artifacts stay interpretable.
15. For derived analytical geometry tasks, do not force integer targets if that collapses scene variety; prefer integer givens plus a numeric answer rounded to one decimal place when the natural formula yields irrational lengths.

## 6) Minimal test checklist
1. Determinism for fixed seed.
2. Answer/annotation consistency with execution trace.
3. Prompt metadata and placeholder validity.
4. Build integration smoke.
5. Constraint-specific tests (for example non-overlap, uniqueness).
6. Feasibility sanity at max candidate count under default render ranges (for geometry/layout-heavy tasks).
7. Prefer extending shared scene/task contract tests instead of duplicating full contract checks in every task file.
8. Keep tests behavior-focused and compact: merge overlapping checks rather than adding parallel literal-default tests for the same contract.

Run:
```bash
PYTHONPATH=. pytest -q
```

## 7) Required docs updates (same change)
1. `docs/tasks/<task_id>.md`
2. `docs/tasks/README.md` (task links must match active task set)
3. `docs/ACTIVE_TASK_INVENTORY.md` (regenerate after active task, scene, or taxonomy changes)
4. `docs/core/PROMPT_SYSTEM.md` (if active prompt bundles or task-to-bundle mappings changed)
5. `docs/core/SYSTEM_ARCHITECTURE.md` (if architecture/module boundaries changed; do not add task inventory lists there)
6. `docs/workflows/SHARED_UTILITIES.md` (if shared helpers moved/added)
7. `docs/workflows/BUILD_VALIDATION.md` or `docs/workflows/VALIDATION_ERROR_CODES.md` (if validation behavior changed)
8. `docs/workflows/CODE_REVIEW_GUIDELINES.md` for reusable findings.
9. Treat existing-domain task additions/removals the same as first-domain activation for doc hygiene: update the active task docs, generated active inventory, and prompt-bundle maps together in one change.

## 8) Reuse anti-patterns
Use `docs/workflows/CODE_REVIEW_GUIDELINES.md` Section 2 as the canonical anti-pattern list.

## 9) Task review workflow
For new tasks or distribution-changing changes, run the standardized review workflow:
```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews
```

The review scripts default to all visible CPUs; pass `--workers <n>` when you want to limit parallelism explicitly.

This writes review artifacts under `review/task-reviews/<domain>/<scene_id>/<task_id>/`:
- `random_review_100.json` (100 random samples, includes query/sampling-axis distributions)
- `distribution_review.json` (100 answers per query when query ids exist; otherwise single 100-sample check)
- `images/` and `data/` sidecars for browser inspection
- `manifest.json` with source dataset, taxonomy, and baseline metadata
- optional `<task_id>.xlsx` static workbook export when the reviewer needs an offline snapshot

Use `--balanced-inspection-by-query` only when you intentionally need a
balanced visual inspection sample per query id; calibration reviews should use
the default 100 total samples per public task so they match solve-rate sampling.

Manual inspection should happen in the browser review app by default:

```bash
PYTHONPATH=. python scripts/run_review_app.py --host 127.0.0.1 --port 7860
```

The launcher defaults browser-facing links to `/proxy/{port}`. Pass
`--base-url ''` only when intentionally debugging root-relative localhost
links.

The app reads the sidecars, shows image/annotation/prompt/answer details by
domain, scene, task, and query id, and persists sample-level issues. Excel
workbooks are optional archival/fallback artifacts and should not be the normal
handoff for new reviews.

For scene-package migration scenes, do not generate task-review artifacts until
the scene has a passing `manual_code_audit_status.json` under
`review/task-reviews/<domain>/<scene_id>/`. That file records the manual source
audit for role boundaries: public task ownership, identity-free scene shared
helpers, correct helper placement, and no wrapper/dispatcher shortcuts. The
review generator rejects migration-review artifacts when that status is missing
or not passing.

After regenerating anything under `review/task-reviews`, reload the app index
with **Reload Index** or `POST /api/reload` before inspection or handoff. If
review-app code, templates, CSS/JS, server routes, indexer logic, resource
indexing, feedback storage, or schema code changed, restart the app instead of
reloading. After reload or restart, open the affected
domain/scene/task/sample page and verify that the image, prompt, annotation,
distribution status, solve-rate status, manual-audit status, and issue
controls reflect the updated local files. Save sample-specific issues in the
app rather than Excel notes. If acting on a reviewer issue, add a brief agent
repair note under the relevant issue item after making and validating the change;
include whether artifacts were regenerated/reloaded. Do not mark the issue
resolved unless the user explicitly asks for that verification step. Resolved
issues leave the open work queue but remain visible in their threads. The
reviewer-facing term is **issue**; the internal route/database name remains
`feedback`. Browser-facing issue pages use `/issues`. A task is complete only
when the app shows prompt, image, annotation, distribution, code review, and
solve-rate gates passing; do not treat a fresh workbook export as completion
by itself.

Current acceptance calibration uses artifact baseline `v0`. Review manifests
and solve-rate stats used for acceptance must include `calibration_baseline:
"v0"`; older files without that metadata are historical and should be deleted
or regenerated before they appear in the web app as current scene-review
artifacts.

Prompt wording rule:
- when the scene stem already establishes the image/diagram context, keep the task-layer line focused on the question itself instead of repeating phrases like `from the image` or `from the diagram`.
- when graph-paper geometry must stay strictly inside the plotted grid, compute scene-capacity bounds against the visible interior cells and final `graph_panel_bbox_px` (not just the raw sampled `graph_cells` target) before locking target answers or placements.
- when an icon task's rule is fully visible inside one scene panel, prefer a single-panel layout over a decorative reference+scene layout so scene capacity stays focused on the actual reasoning target.
- when an icon sequence task asks for a violating or missing position, prefer visible in-scene cell labels plus one-box `bbox_set` annotation over a separate option strip; the row itself should ground both the answer and the annotation target.
- for labeled node-link graph tasks, keep node labels as prompt-facing identities only; public annotation should ground node witnesses with `point_set`, ordered node witnesses with `point_sequence`, and edge witnesses with `point_pair_set`.
- for graph tasks with added visual diversity, vary whole-image style axes such as label format, node glyph, edge routing, named node color, or global layout transform only when they remain non-semantic for the task; if a future task queries one of those axes, promote it from style noise to an explicit task contract. Prompt references to short person-name node labels should quote the label text.
- if a graph task supports both undirected and directed branches, make directionality explicit in both prompt wording and trace metadata (`degree` vs `in-degree` vs `out-degree`) and render directed edges with arrowheads; do not rely on the image alone to disambiguate the semantic contract.
- if a directed graph task asks about reachability from one queried node, say explicitly whether the queried node itself is included in the answer/annotation set and verify the witness from successor adjacency after all extra-edge decoration; do not rely on convention alone for “reachable from itself.”
- if a graph task includes the queried node itself in the answer/annotation set (for example same-component queries), say that explicitly in the prompt and annotation hint rather than leaving “including the queried node” implicit.
- if a graph task exposes one “largest” or otherwise globally maximal witness component, enforce that winner’s uniqueness by construction; ties should be rejected rather than broken implicitly by label order or layout.
- if a graph task assumes exactly one cycle, construct a unicyclic graph by design and verify the finalized adjacency still has one cycle before exposing answer/annotation; do not infer uniqueness from a partial construction recipe alone.
- for graph tasks, treat `point_set` node annotation as unordered semantically and canonicalize it internally only for determinism; only path-like tasks should require an explicitly ordered `point_sequence`.
- for graph edge-witness tasks, use `point_pair_set` where each witness is the two pixel endpoints of one visible edge; treat both the endpoint pair and the outer witness set as unordered semantically.
- for weighted graph tasks, render edge-weight labels from the same canonical edge-to-weight map used in trace/verifier logic; do not let the renderer invent a separate edge ordering or duplicate weight assignment path.
- for graph path tasks, use ordered `point_sequence` annotation only when node order is truly semantic, and say explicitly whether the path includes both queried endpoints.
- for graph ordered-but-nonpath tasks, use ordered `point_sequence` annotation and make the ordering rule task-specific; consecutive points do not need to share an edge unless the task is a path query.
- for clock-compare puzzle tasks that answer with one visible clock label, make sure the visible label support itself is broad enough for answer-distribution review; if only two to four labels can ever be correct, widen the scene or rethink the answer contract instead of relying on cross-query mixing.
- for page schedule tasks, prefer event-block `bbox_set` annotation when the query can be grounded on visible events; do not jump to empty-gap annotation if the same reasoning contract can stay on concrete schedule blocks.
- for page timeline tasks, prefer event-card `bbox_set` annotation over whole-axis or connector-line annotation; keep the witness anchored to the milestone cards even when the reasoning depends on their left-to-right order.
- for month-view calendar tasks, keep the visual scaffold fixed to one month grid and vary the question through `query_id`; date-cell `bbox_set` annotation should stay local to the relevant day cells rather than widening to week rows, headers, or the month title.
- when a task renders text inside compact glyphs or cells, fit the font against the available box instead of assuming one fixed font size will work for every label variant; multi-character labels and alternate glyph shapes should stay readable without overflowing the witness object.
- when a second page task reuses the same grouped page grammar, promote the shared section templates and typed scene-value builders into a neutral shared helper instead of leaving them under one objective-specific module.

Use `--mode inspection` when only visual/prompt inspection is needed and distribution checks should be skipped.

Required answer-distribution checks:
- `unique_answers >= 4`
- `max_answer_frequency < 1/3`
- apply checks per `query_id`; task-level pass requires every query branch to pass.
- zero collected samples for a review slice is a hard fail (`no_samples_collected`).

Numeric answer-distribution summaries:
- task-review reports still include `five_bin_numeric` and `max_five_bin_frequency` for inspection,
- treat those as informational by default rather than hard pass/fail gates unless a scene adopts an explicit tighter rule.

For quick distribution-only runs:
```bash
PYTHONPATH=. python scripts/check_task_answer_distribution.py --tasks <task_id>
```

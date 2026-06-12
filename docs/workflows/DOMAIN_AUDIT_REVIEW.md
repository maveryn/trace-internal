# TRACE Domain Audit Review

Use this workflow for repo-wide sanitation passes that review one active domain at a time.

## 1) Purpose
1. Catch contract drift, visual clarity problems, stale docs/configs/tests, and lingering review inconsistencies after a domain has grown over multiple patches.
2. Keep audits domain-scoped so fixes stay tractable and validation remains targeted.
3. Turn recurring findings into reusable guidance by updating `docs/workflows/CODE_REVIEW_GUIDELINES.md` when needed.

## 2) Audit inputs per domain
For the domain being reviewed, inspect:
1. Domain setup doc in `docs/domains/`.
2. Active task inventory in `docs/ACTIVE_TASK_INVENTORY.md` and `docs/tasks/README.md`.
3. Repo-local domain skill in `skills/domain-<domain>/`.
4. Task modules, domain/scene configs, prompt bundles, task docs, and tests.
5. Existing task-review artifacts under `review/task-reviews/<domain>/<scene_id>/<task_id>/`,
   inspected through the browser review app unless an offline workbook export
   is explicitly needed.
   Current acceptance artifacts must carry `calibration_baseline: "v0"`;
   otherwise treat them as stale and regenerate them for the audited scope.

For taxonomy design or task-boundary audit passes, use the core taxonomy and
task-unit docs as policy sources. Domain setup docs, code, configs, prompts,
tests, review artifacts, and skills may be inspected as factual inputs, but
repo-local skills are not authority for merge/split decisions.
`docs/core/TASK_UNIT_POLICY.md` is the canonical source for concrete
program-contract design.

## 3) Required audit checklist
### A. Inventory and registration
1. Active task ids in code, docs, configs, and review folders agree.
2. Task ids, filenames, and module layout match the documented taxonomy.
3. Retired tasks are not still listed as active examples, prompts, or review rows.

### B. Contract and prompt audit
1. Prompt wording matches the real scene contract and annotation contract.
2. Prompt-facing annotation is local, non-vacuous, and visually discoverable.
3. Zero-answer cases use the documented empty annotation contract rather than widened fallback annotation.
4. Prompt examples remain valid for the active task/query surface.
5. For task-boundary review, record the scene contract and the three task
   contract fields: `answer_schema`, `annotation_schema`, and
   concrete `program_schema`. Do not use query ids, descriptive review tags,
   broad objectives, or target task-count goals as merge/split authority.
   Generic inferred schemas are draft-only and must be refined before approval.

### C. Visual audit
1. The queried object, marker, or reference is easy to locate.
2. Labels do not overlap figures, points, cells, or critical geometry when avoidable.
3. Non-semantic style variation does not create semantic ambiguity.
4. Layout size, gutters, and text scale still support the task at the configured max scene density.
5. Backgrounds, palettes, panels, strokes, sizes, marker styles, board/object styles, and other non-semantic visual axes include safe variety where the domain supports it. Prefer shared style registries, but each scene must still map those shared primitives to its own annotation-bearing geometry safely.
6. Answer-bearing path, marker, option, and highlight colors must be checked against known background/panel/board colors with shared Lab-distance helpers such as `resolve_contrasting_palette(...)` or a documented equivalent; hand-picked palettes are not enough when the background is independently sampled.
7. Text-bearing elements use the shared role-aware font dispatcher. Required/read-off text must use `role="readout"` and the 100-family readout pool; non-answer context/chrome may use `role="context"`, and purely non-semantic visual dressing may use `role="decorative"`. Record the sampled family, role, pool id, pool size, and asset version in render metadata.
8. Keep font choice consistent inside one meaningful visual unit, such as a single chart, game board, table, form, panel, or option set, unless mixed typography is itself part of the scene grammar.
9. Required/read-off text must use the shared text-legibility resolver or a documented equivalent that records role, text/surface colors, contrast thresholds, and pass/fail metadata in render metadata copied into `render_spec`. Resolve separate text roles for separate surfaces, for example chart ticks versus legend labels or graph titles versus node labels. During a scene audit, run `python scripts/audit_text_legibility.py --root . --scan-root trace/tasks/<domain> --strict-renderer-migration --strict-role-metadata --strict-font-routing` and `python scripts/audit_text_legibility.py --root . --runtime-coverage --runtime-domain <domain>`. The runtime audit checks generated trace metadata, including automatically collected drawn-text records under `render_spec.drawn_text.text_legibility`; add `--require-required-roles` or `--fail-unvalidated-required-draws` when ratcheting one scene from compatibility routing to full role-level contrast metadata. Non-answer distractor/context text may use weaker styling, but it must stay outside answer/annotation contracts.
10. Glyph text color must be non-semantic. Do not make the answer, category, class, or filter depend on the color of the text itself; use marks, swatches, fills, outlines, icons, or panels for semantic color channels.
11. Rendered content is not unnecessarily fixed at the same centered location; any layout jitter must be sampled before annotation projection, and public annotation must use the final jittered coordinates.
12. Board, panel, chart, graph, page, and object styles have scene-appropriate variation beyond canvas background alone, such as board skins, piece/token styles, grid/axis strokes, marker glyphs, card/table chrome, or page/control skins where safe. For game scenes, aim for at least five scene-local board/object styles in addition to shared background/panel/font variation unless a documented canonical/readability exception applies.
13. Charts, graphs, pages, and UI-like scenes use context or distractor text appropriately: distractor text should create realistic visual clutter without being confusable with answer-bearing text or overriding the prompt contract. Post-render context layers must avoid legends, colorbars, annotations, option panels, and other support/readout regions by using recorded protected bboxes rather than visual guesswork.
14. Scenes with named objects use the broadest suitable reusable object/name pools available for that scene.
15. Semantic markers that the prompt relies on, such as highlighted cells, marked references, selected moves, routes, and target outlines, are contrast-checked against their actual rendered surfaces and have marker-legibility metadata under `render_spec.drawn_markers.marker_legibility` or a nested render block.

### D. Sampling and answer-support audit
1. Scene construction still supports the configured answer range by construction or explicit feasibility checks.
2. No query id has collapsed to a tiny answer support unintentionally.
3. Reference/context objects are not accidentally counted when the prompt only asks about the candidate pool.
4. Candidate answer and input supports are continuous across the intended range unless task semantics require structured discontinuities.
5. Overall answer-distribution checks are supplemented with breakdowns by `query_id`, scene/style variant, option count, object count, and other task-specific knobs.
6. MCQ tasks render at least four options in the image rather than relying on prompt-only choices, and answer-support checks should confirm at least four unique final answers for the task surface.
7. Decimal-answer tasks state the exact formatting contract, such as one digit after the decimal point, and avoid approximation shortcuts unless the displayed approximation is itself the object being read.
8. If a visible `?` or blank marker appears, treat it as a target locator by default, not prompt-facing annotation. Include it only when localizing the unknown slot is part of the grounding contract; otherwise annotation should point to the source givens/witnesses used to derive the answer, and optional locator boxes should stay in trace metadata.

### E. Annotation and trace audit
1. Answer and annotation come from the same execution trace.
2. Annotation is computed after final layout, scaling, style chrome, and image composition.
3. Prompt-facing annotation remains local, visible, and inside the final canvas.
4. Annotation identifies the visual witnesses used to derive the answer rather than unrelated context or overly broad fallback regions.
5. Annotation should usually localize object/primitive witnesses rather than
   standalone numeric labels or selected answer options. Numeric annotations
   should be trace/render metadata or attributes of nearby objects unless the
   task is explicitly a text/readout task.
6. Role-aware annotation must use the active global homogeneous names
   `keyed_point_map`, `keyed_point_set_map`, `keyed_bbox_map`, or
   `keyed_bbox_set_map`; flag any
   domain-specific keyed annotation type names or mixed point/box annotation unless
   the global contract has been deliberately expanded.
7. Prefer keyed annotation when witness-role binding matters or when an
   unordered annotation set would be ambiguous. If the verifier
   should distinguish roles such as outer versus shaded region, source versus
   target panel, reference versus candidate item, or input versus output
   measurement, the task should normally use `keyed_bbox_map`,
   `keyed_bbox_set_map`, `keyed_point_map`, or `keyed_point_set_map` rather
   than an unordered set.
   Unordered sets remain appropriate for counting tasks where annotation
   cardinality is the answer, or for homogeneous witness sets where role and
   order are semantically irrelevant.
8. Line-like witnesses such as segments, rays, paths, route legs, displacement
   cues, and graph edges should usually be grounded by endpoints or ordered
   points (`point_pair_set`, `point_sequence`, or keyed point maps) rather than
   by broad rectangular bboxes. Use bboxes for line-like annotation only when the
   visible witness is intentionally a thick/extended region or a complete
   visual option panel.
9. Selected option bboxes are used only for visual option-image tasks where the
   option is a complete candidate image/panel and there is a
   source/reference/original image or region that the option matches,
   completes, transforms from, or belongs to. Ordinary MCQ choices,
   numeric/text labels, and lettered candidate objects should ground the
   source/candidate objects or primitives instead of the option bbox.
10. Annotation instructions should be clear about witness categories without
   leaking answers. For counting tasks, do not tell the model a fixed annotation
   count when that count is the answer.
11. Annotation-format prompt text is positive-only. It should say what witness
   category/shape to return and should not list non-witness objects, exclusions,
   or rejected annotation forms.
12. Trace metadata records explicit random choices that affect prompt, rendering, query branch, answer construction, and annotation.
13. Analytical geometry and other construction-heavy tasks should use the minimal visible givens as annotation. If the only plausible annotation is a `?` marker or broad whole-diagram box, flag the task for annotation-contract cleanup.

### F. Shared-infra audit
1. Helpers still live at the narrowest reusable layer that fits.
2. No task-local wrapper has silently become shared infrastructure.
3. Config defaults live in domain/scene config instead of repeated task-local literals.
4. Reusable font, object, icon, palette, background, and style resources have inspection sheets or review artifacts under a shared review location.
5. Asset pools have documented provenance and compatible licenses before becoming generation inputs.
6. Runtime renderer audits include marker legibility for touched domains when semantic markers are migrated or newly introduced.

### G. Docs and tests audit
1. Domain setup docs and task docs still describe the live contract.
2. Tests cover the actual contract surface and do not only assert stale defaults.
3. Review status and review summary reflect the active task surface.
4. Tests cover MCQ option count, decimal formatting, annotation projection, prompt/image agreement, and deterministic generation where applicable.

## 4) Audit conventions
1. Work domain by domain; do not mix fixes from unrelated domains in the same audit patch unless they are truly shared infrastructure.
2. Start by reading the domain setup doc and existing review artifacts before changing code.
3. Fix safe, clearly correct issues immediately rather than building a long deferred list.
4. If an issue repeats across tasks, add one reusable rule to `docs/workflows/CODE_REVIEW_GUIDELINES.md` in the same patch.
5. Keep a short issue taxonomy in notes and handoff:
   - `contract`
   - `visual`
   - `distribution`
   - `shared`
   - `docs`

## 5) Validation expectations
1. For audit-only reading with no code changes, inspection of the existing review artifacts is enough.
2. If code, prompts, configs, or docs change:
   - run focused pytest for the touched area first,
   - run `python -m py_compile` when shared/task modules changed,
   - run `git diff --check`,
   - run full task review for every touched task:
     - `PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews`
   - after regenerating review artifacts, use **Reload Index** in the browser
     review app or call `POST /api/reload` before inspection; restart the app
     when templates, CSS/JS, server routes, indexer logic, resource indexing,
     feedback storage, or schema code changed; inspect regenerated task/sample
     pages there and add sample-level issues in the app when a visible issue
     remains; verify the affected page shows the updated local files before
     handoff
   - mark manual audit checkboxes only after prompt, image, annotation,
     distribution, code review, and solve-rate review are acceptable in the app
   - when fixing reviewer issues, add a brief agent repair note to the
     relevant task-level or sample-level issue item; leave resolution for
     human verification unless explicitly instructed otherwise. The app UI says
     "issue" and browser issue pages use `/issues`; internal APIs/storage still
     use `feedback`.
   - if solve-rate calibration is required but no GPU/endpoint is available,
     record the scene as pending solve rate and stop there; do not mark the
     scene accepted or move to the next scene until solve-rate calibration has
     run.
   - treat a task as complete only when prompt, image, annotation,
     distribution, code review, and solve-rate gates pass in the app.
3. If the audit changes shared infrastructure, expand pytest coverage to the affected sibling tasks.

## 6) Recommended audit order inside one domain
1. Domain inventory and task list.
2. Shared helpers and configs.
3. Prompt bundles and docs.
4. Task modules.
5. Tests.
6. Review artifacts and targeted image sampling.
7. Fixes + validation.

## 7) Handoff format
Summarize each domain audit under:
1. `Fixed` — issues corrected in this pass.
2. `Deferred` — issues intentionally left for later, with reason.
3. `Rules added` — any new distilled reusable review rules.
4. `Validation` — focused tests and task reviews that were rerun.

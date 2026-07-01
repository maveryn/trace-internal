# Domain Finalization Checklist

Use this checklist only after a domain has completed scene-package migration
and the current active tasks are intended to be the domain's training/release
surface for the current repo version.

The finalization review answers one question:

```text
Is this domain coherent, non-duplicative, review-ready, and safe to use as a
final training/release surface?
```

It does not replace:

- scene-package migration gates in `docs/SCENE_PACKAGE_MIGRATION/`;
- task authoring rules in `docs/workflows/TASK_AUTHORING.md`;
- task review in the browser app;
- calibration and solve-rate acceptance.

## Output Location

Write domain-specific finalization outputs under:

```text
docs/domain-finalization-review/<domain>/
```

Recommended files:

```text
docs/domain-finalization-review/<domain>/<domain>_finalization_review.md
docs/domain-finalization-review/<domain>/issues.md
docs/domain-finalization-review/<domain>/scene_inventory_snapshot.json
docs/domain-finalization-review/<domain>/task_signature_matrix.csv
docs/domain-finalization-review/<domain>/duplicate_candidate_scan.md
```

Do not copy generated task-review samples, images, workbooks, or review-app
state into this folder. Those remain under `review/task-reviews/` and
`review/feedback/`.

## Review Mode

Default mode is audit-only.

During a finalization pass:

- do not edit task source, configs, prompt bundles, task docs, review
  artifacts, review-app state, or solve-rate artifacts;
- record findings as issues with severity and concrete file/task references;
- apply fixes only in a separate implementation pass after approval;
- rerun affected scene review artifacts only after the implementation pass.

If the user explicitly asks to fix issues during the same turn, keep fixes
separate from the audit report and document which issues were fixed.

## Severity

Use these severities consistently:

- `blocker`: cannot train or release with this issue present.
- `fix_before_calibration`: generation, prompt, annotation, distribution, or
  review-artifact issue that must be fixed before solve-rate calibration.
- `release_cleanup`: code/doc/config consistency issue that should be fixed
  before declaring the domain final, but does not invalidate generated samples
  by itself.
- `follow_up`: useful improvement that can be deferred after release.
- `accepted`: reviewed design choice; no change needed.

Every non-accepted issue should include:

- domain;
- scene id;
- task id or `scene-level` / `domain-level`;
- affected query ids, if any;
- severity;
- observed problem;
- expected behavior;
- recommended fix;
- validation needed after fix.

## Required Inputs

Collect these before reviewing:

- active task and scene counts from the live registry;
- `docs/ACTIVE_TASK_INVENTORY.md`;
- domain contract doc in `docs/domains/<domain>.md`;
- task docs in `docs/tasks/<domain>/`;
- configs in `configs/domains/<domain>/`;
- prompt bundles in `prompts/<domain>/`;
- task source in `trace/tasks/<domain>/`;
- scene-package migration status from `trace/core/scene_package_migration.py`;
- review artifacts under `review/task-reviews/<domain>/`;
- browser-app review status for prompt, image, annotation, distribution,
  taxonomy, and code review;
- solve-rate status if final solve-rate acceptance is in scope.

## Automated Inventory Checks

Run or inspect equivalent outputs:

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python scripts/check_active_inventory_integrity.py
PYTHONPATH=. python scripts/audit_active_domain_surfaces.py
```

Check:

- every active task id follows
  `task_<domain>__<scene_id>__<objective_contract>`;
- active registry, generated inventory, taxonomy, configs, prompts, and task
  docs agree;
- every active task has a task doc;
- no active task is missing a taxonomy mapping;
- no retired scene/task/config/prompt/doc reference remains;
- no compatibility alias, task-group route, disabled legacy task, or stale
  wrapper remains in the domain.

## Scene Inventory Lock

Create a scene inventory table with:

- scene id;
- active task count;
- task ids;
- source package path;
- config path;
- prompt bundle path;
- review artifact path;
- migration status;
- taxonomy review status;
- manual review status;
- solve-rate status, if in scope.

Flag:

- scenes present in source but absent from active inventory;
- configs or prompts for absent scenes;
- review artifacts for absent scenes;
- active scenes missing source/config/prompt/task docs/review artifacts;
- task docs for inactive tasks;
- mismatched task counts between registry and docs.

## Scene Uniqueness Review

For every pair of scenes in the domain, decide whether they are genuinely
different visible grammars.

Scenes should stay separate when they require different visual parsing, such
as:

- Cartesian series vs radar vs radial progress;
- Sankey flow vs map region chart;
- table/grid vs 3D surface;
- distribution plot vs composition chart;
- single chart vs multi-panel grammar, when the panel grammar changes the
  reasoning surface.

Flag a scene merge candidate when two scenes differ only by:

- style, theme, palette, font, or decorative context;
- minor layout treatment;
- renderer implementation history;
- source data route rather than visible grammar;
- one scene being a strict cosmetic variant of another.

For each scene, record one sentence explaining why the scene remains distinct.

## Intra-Scene Task Uniqueness Review

For each scene, build a task signature table:

- task id;
- answer schema;
- annotation schema;
- candidate set;
- queried primitive;
- program contract;
- query ids;
- annotation witness;
- closest neighboring task in the same scene;
- decision: `keep`, `merge_candidate`, `split_candidate`, or `delete_candidate`.

Tasks should stay separate when they differ in at least one meaningful task
contract axis:

- answer schema;
- annotation schema;
- candidate type;
- output binding;
- core program skeleton;
- required visual witness type;
- reasoning operation, such as count vs aggregate vs rank vs arithmetic;
- single-object reasoning vs cross-panel/global reasoning.

Flag a duplicate task when the difference is only:

- wording;
- sampled label/category/object name;
- threshold value;
- target color or style used as a prompt slot;
- layout or renderer variant;
- mirror direction that should be a query id;
- arithmetic sign/direction that fits one stable program with a direction
  argument.

Flag a split candidate when one task/query family mixes:

- one-bound threshold and two-bound interval logic;
- count and numeric aggregation;
- label selection and numeric value computation;
- scalar annotation and set/map annotation;
- option-image selection and direct chart readout;
- single-panel and cross-panel reasoning;
- different candidate sets or output bindings.

## Query-ID Review

Query ids are internal replay/review metadata, not public task units. They are
valid only when they are prompt-facing branches of one stable task program.

Valid query-id examples:

- largest vs smallest;
- above vs below;
- earliest vs latest;
- source vs target;
- first vs last endpoint, when prompt-facing;
- left vs right / inner vs outer, when prompt-facing;
- rank direction or comparison direction under one stable candidate set.

Invalid query ids:

- font, palette, layout, style, context mode, or renderer preset;
- sampled label, category, object, region, threshold, or numeric value;
- hidden generation mode that does not affect prompt meaning;
- branches that change answer schema, annotation schema, candidate type,
  witness role structure, or program skeleton.

Check:

- single-query tasks use `query_id="single"`;
- all query ids appear in review samples;
- no query id has a separate task-level objective hidden inside it;
- prompts and program contracts explain the query branch when it is semantic.

## Program Contract Review

Every task doc should have a concrete program contract. It must name enough of
the operation to distinguish the task from nearby tasks.

Check that each program contract includes:

- candidate set;
- filters or predicates;
- operand roles;
- aggregation, comparison, rank, selection, arithmetic, or transformation
  operation;
- output binding;
- annotation witness role.

Flag vague contracts such as:

- `count(objects)`;
- `select_by_rank(items)`;
- `compare(values)`;
- `lookup(label)`;
- generic placeholders that do not distinguish the task from another task in
  the same scene.

Program contract names should be consistent across scenes and domains when the
operation is genuinely the same, but scene-specific operands can remain named
in the contract.

## Prompt Review

For every task/query prompt:

- prompt asks exactly for the generated answer;
- visible labels used in the question are quoted;
- answer format examples match the active answer schema and support;
- option-letter tasks show options in the image, not as prompt-only MCQ lists;
- prompt does not expose hidden task ids, query ids, trace fields, or
  generation internals;
- prompt does not leak answer ranges unless the range is task-relevant;
- prompt does not include decorative renderer trivia;
- prompt uses `annotation`, not historical terminology;
- opening scene sentence is short and semantic;
- if unanswerable is supported, prompt defines the unanswerable condition
  before asking for the answer.

For chart-like domains specifically:

- named chart labels should be in quotes;
- examples should use multi-character labels when real labels can be
  multi-character;
- axis, panel, legend, region, or table scope should be explicit when needed;
- prompts should not ask for exact values when the image does not provide a
  readable scale or readout.

## Annotation Review

Annotation must mark minimal visual witnesses for the answer. Use
`docs/contracts/ANNOTATION_AND_REWARD_CONTRACTS.md` as the normative contract,
`docs/review/ANNOTATION_REVIEW.md` as the review procedure, and the domain
contract doc only as a domain-specific refinement.

Finalization review should also flag annotation designs that are technically
valid but clunky, overly verbose, or harder than necessary for reviewers and
models. These are not always contract bugs, but they should be recorded as
`fix_before_calibration` when they make prompts/reward targets confusing, or
`release_cleanup` when a simpler equivalent contract would make the task easier
to maintain.

Check:

- annotation type in prompt, task doc, source, review artifact, and reward
  contract agree;
- scalar witnesses use scalar `point`, `bbox`, or `segment`;
- one-item arrays are not used for scalar annotation;
- unordered sets are used only for homogeneous counted/selected witnesses;
- keyed maps are used when roles need binding;
- answer labels/options/numeric text are not annotated unless the text itself
  is the queried visual object;
- annotation and answer come from the same execution trace;
- bboxes are large enough to inspect and do not target tiny text when the full
  visual object is the witness;
- point targets are stable and described as center/top-center/etc. when the
  reward expects a specific point;
- segment targets use `[[x0, y0], [x1, y1]]` and reversed endpoints are
  acceptable only when the reward contract allows it;
- the annotation schema is no more complex than the answer-verification witness
  requires;
- single-witness tasks do not use maps, sets, or keyed objects only to name an
  obvious role;
- homogeneous witnesses do not use keyed maps when an unordered set is enough;
- annotation does not include reference/scope/proof context that can live in
  trace metadata instead;
- prompt annotation instructions remain short and easy to follow for the task;
- repeated patterns of clunky annotation within a scene are filed as
  scene-level simplification issues, not only task-level comments.

## Renderer And Visual Quality Review

Review samples scene-by-scene in the browser app.

Check:

- image canvas is under the current size cap;
- semantic marks, labels, legends, axes, options, and annotations are visible;
- no label, legend, readout, paragraph, or panel overlaps answer-bearing
  content;
- text is legible across sampled fonts;
- dark and light themes have sufficient contrast;
- semantic colors are distinguishable;
- option markers and MCQ panels have consistent sizing;
- clean mode is truly clean;
- minimal/paragraph context modes follow the domain policy;
- distractor text is non-answer context and does not hide chart annotation
  targets;
- generated styles are varied but do not change the semantic task;
- review samples cover expected renderer variants.

For final release, record any scene that still needs manual visual inspection
even if automated checks pass.

## Distribution Review

For every task:

- `distribution_review.json` exists;
- distribution review status is passing or accepted;
- every query id appears in samples;
- answer support is not pathologically narrow unless the task contract
  requires it;
- generated answers are unique by construction;
- MCQ tasks meet the current minimum option policy;
- unanswerable support, if present, has a controlled answer rate and clear
  prompt condition;
- generation retries do not hide constraint failures or rejection spikes.

Flag:

- answer support with suspicious gaps;
- tasks whose valid answer range is too small for training;
- tasks whose answer is almost always the same;
- tasks with generation failures in review logs;
- tasks where hard/easy split is outside current calibration policy.

## Review Artifact And App Status

For every active task:

- review artifacts exist under
  `review/task-reviews/<domain>/<scene_id>/<task_id>/`;
- artifacts were generated after the latest source/config/prompt/task-doc
  change for that task;
- browser app index sees the current local files;
- prompt, image, annotation, distribution, taxonomy, and code-review gates are
  manually checked where required;
- open reviewer issues are either fixed and awaiting human verification or
  recorded as blockers/follow-ups;
- solve-rate artifact is current or explicitly marked pending.

Do not silently reuse stale artifacts from failed or retired configs.

## Code Organization Review

After migration, check that implementation still matches the intended source
shape:

- one public task id maps to one public task file;
- public task file owns objective/query logic, answer binding, annotation
  binding, prompt slots, and final output construction;
- scene `shared/` contains identity-free primitives only;
- domain `shared/` contains code reused across multiple scenes;
- no task-group routing remains;
- no wrapper-only task files remain;
- no public task file delegates the full task to a shared runtime/generator;
- no large duplicated helper blocks remain across tasks/scenes;
- no stale review/migration compatibility aliases remain.

Flag source cleanup only when it affects maintainability or future task
authoring. Do not turn finalization into open-ended refactoring.

## Documentation Review

Check:

- domain contract doc matches current scenes and task policies;
- task docs exist for every active task and no inactive task;
- task docs match source answer/annotation/program/query contracts;
- prompt bundle docs and examples are current;
- active inventory is generated and current;
- docs do not mention retired task ids or old scene names;
- skills do not duplicate stale task lists or old terminology;
- docs point to current review and calibration workflows.

## Release Decision

End the finalization report with one of:

- `accepted_for_training`: no blocker or fix-before-calibration issues remain;
- `accepted_with_followups`: only cleanup/follow-up issues remain;
- `not_accepted`: at least one blocker or fix-before-calibration issue remains.

The final report should include:

- active task count;
- active scene count;
- reviewed scene list;
- count of accepted scenes/tasks;
- count of issues by severity;
- explicit merge/split/delete candidates, if any;
- remaining validation commands;
- whether solve-rate acceptance is in scope and current.

# Trace Task Authoring Guide

Use this as the procedural checklist for adding or modifying tasks. Keep policy
definitions in `docs/contracts/`; this file should tell an implementer what to
do and where to verify it.

## Read First
1. `docs/contracts/TAXONOMY.md`
2. `docs/contracts/TASK_UNIT_POLICY.md`
3. `docs/contracts/PROGRAM_SCHEMA_CATALOG.md`
4. `docs/contracts/PROMPT_SYSTEM.md`
5. `docs/contracts/ANNOTATION_AND_REWARD_CONTRACTS.md`
6. The matching domain contract in `docs/domains/`
7. `docs/contracts/SOURCE_LAYOUT.md`

## Before Coding
1. Confirm `domain`, `scene_id`, and public `task_id`.
2. Confirm the task is one stable scene contract plus one objective contract:
   answer schema, annotation schema, and concrete program schema.
3. Decide which branches are valid internal `query_id` values. Split the public
   task if a branch changes the answer type, annotation type, witness roles,
   program skeleton, or visible task scaffold.
   Use `query_id="single"` for tasks with no semantic query branch; never use
   the task id, objective name, or `default` as a single-query placeholder.
4. Check `docs/ACTIVE_TASK_INVENTORY.md` and nearby
   `docs/tasks/<domain>/<scene_id>/<task_id>.md` files before adding a new one.
5. Search for reusable helpers before writing new logic:
   `trace/core/`, `trace/tasks/shared/`, `trace/tasks/<domain>/shared/`, and
   `trace/tasks/<domain>/<scene_id>/shared/`.
6. Pick the narrowest helper layer that fits. Promote helpers only after real
   reuse or an approved domain shared boundary.

## Implementation Checklist
1. Put the public task module in the documented layout:
   `trace/tasks/<domain>/<scene_id>/<objective_contract>.py`.
2. Register the task with `@register_task` and make sure the module is imported
   through the active task registration path.
3. Declare the reviewed reasoning families as a literal class-level
   `reasoning_operations` tuple, using the canonical vocabulary and order in
   `docs/contracts/PROGRAM_SCHEMA_CATALOG.md`.
4. Keep user-facing prompt text in external prompt bundles, not task modules.
5. Resolve and validate `query_id` in the public task file. Pass semantic
   arguments to shared helpers; do not route shared code by task id, query id,
   or objective name.
6. Treat literal operands as parameters, not query ids. Split public tasks when
   changing the visual reasoning channel or predicate arity changes how the
   model must scan the image, for example color pattern vs size pattern,
   type-match vs color-match, or shape-only lookup vs color+shape lookup.
7. Build the final output from one execution trace:
   typed `answer_gt`, typed `annotation_gt`, prompt slots, render/projection
   data, witness records, and `TaskOutput`.
8. Keep randomness explicit, deterministic from seed/spec/version inputs, and
   recorded when it affects prompts, layout, rendering, answer, or annotation.
9. For semantic random axes, define an explicit support or bounded range plus
   optional weights, then sample with a seeded RNG draw. Uniform sampling means
   every support item has weight `1`. Do not implement sampling by `seed % n`,
   hash-index modulo, cursor cycling, or other deterministic enumeration inside
   a task. Use `trace.core.sampling.uniform_choice`,
   `uniform_choice_with_probabilities`, `weighted_support_choice`, or
   `integer_range_choice`; put exact stratification in the review/dataset
   sampler if exact strata are required.
10. Enforce unique final answers by construction. Use bounded resampling and do
   not silently relax semantic constraints.
11. Do not emit scalar difficulty fields or hand-authored reward contracts from
   task code.
12. Remove retired task ids, wrapper aliases, disabled registry entries, stale
   configs, stale prompt branches, and stale review paths in the same change.

## Prompt Checklist
1. Use prompt bundles under `prompts/<domain>/<scene_id>/`.
2. Use the standard layers: scene, task, optional query, and output mode.
3. Record prompt bundle id, selected keys, variant indices, output mode, and
   required slot values in trace metadata.
4. Provide task-specific JSON examples for both answer-only and
   answer-and-annotation modes.
5. Make examples contract-valid for the active answer and annotation schema.
   If label answers can be multi-character, example labels should be
   multi-character too; one-letter examples are for option/panel-letter tasks.
6. Keep scene wording visual, query wording operational, and output-mode wording
   limited to field hints and examples.
7. Do not put internal taxonomy/source/scaffold adjectives in user-facing
   prompts unless they are necessary visible operands or rules. Avoid wording
   like "special", "synthetic", "procedural", "unlettered", or internal scene
   family names when the concrete visible object, label, mark, or shape name is
   enough.
8. Use `annotation` terminology in prompt-facing text.
9. Do not include method hints or shortcut cues that tell the model how to
   solve the task when the visual/task contract already implies the needed
   reasoning. Include explicit rules only when the rule is part of the problem
   statement, such as game movement rules or a domain convention that would
   otherwise be unavailable from the image. Avoid phrases such as "using the
   slope," "using the Sun-focus distance," or "look for the only non-center
   point on the major axis" unless that method is itself the requested task.

## Annotation Checklist
1. Annotation marks minimal visual answer-verification witnesses for the task
   family, not the full reasoning proof. Direct visible-answer tasks usually
   annotate selected/countable answer objects; derived value tasks annotate the
   minimal visible operands needed to verify the computation; diagram tasks
   annotate canonical visual primitives. Put full derivation context, reference
   objects, intermediate operands, and debug witnesses in trace metadata unless
   they are part of the task's answer-verification witness.
2. Use the global annotation types in
   `docs/contracts/ANNOTATION_AND_REWARD_CONTRACTS.md`.
3. Choose annotation geometry by visual primitive: area-like targets such as
   cells, tiles, cards, GUI controls, text boxes, bars, and page regions default
   to `bbox`; localized features or compact object centers default to `point`;
   line-like witnesses such as edges, paths, spans, sides, and vectors default
   to `segment`.
4. Similar scenes inside a domain should use the same annotation geometry for
   the same visual primitive unless the task doc explains a task-specific
   exception.
5. Prefer map annotation when role binding matters or an unordered set would
   be ambiguous.
6. Use unordered sets only for homogeneous witness collections where order and
   identity do not matter.
7. Avoid mixed point/box annotation; revise the task contract before adding a
   new public annotation type.
8. For scoped selection tasks, annotate the selected answer object/card/tile,
   not the enclosing scope region, unless the scope region is needed to verify
   the answer contract.
9. For MCQ or visual-option tasks, annotate the selected visual option when
   that option is the answer-verification witness.

## Config And Sampling Checklist
1. Use precedence: domain defaults, scene defaults, task/params.
2. Keep scene configs scoped to generation/rendering/prompt knobs. Do not put
   public objective dispatch, task coverage, query weights, or retired
   difficulty gates in config.
3. Query sampling happens inside the selected task and is uniform by default.
4. Uniform means an RNG draw from an explicit support or bounded range with
   weight `1` for every item, not seed modulo or deterministic cycling. A fixed
   seed should reproduce the random draw; it should not be the sampling
   algorithm.
5. Keep visual-representation axes such as style, chart type, board skin, font,
   and layout jitter in metadata such as `scene_variant`, not public task ids,
   unless the visible scaffold changes the objective contract.
6. Answer supports should be constructively feasible and contiguous unless task
   semantics make interior values impossible.
7. Use the same seeded sampler for normal review, calibration, and dataset
   generation. When a harness passes `_sample_cursor` for fixed review/export
   coverage, shared samplers may use it as explicit stratification metadata;
   task-local generators must still not implement their own seed or cursor
   modulo sampling.

## Visual And Resource Checklist
1. Use shared font, label, context-text, marker-legibility, and text-legibility
   resources where applicable:
   - `docs/resources/SHARED_FONT_ASSETS.md`
   - `docs/resources/SHARED_LABEL_ASSETS.md`
   - `docs/resources/SHARED_CONTEXT_TEXT_ASSETS.md`
   For text centered inside circular markers, badges, option chips, or node
   labels, use the shared bbox-aware centered text helper instead of manually
   offsetting by measured width and height.
2. Sample non-semantic visual variety before projection so annotation
   coordinates remain valid.
3. When assigning visual attributes such as colors, styles, shapes, fonts,
   icons, symbols, or option appearances from a larger pool, first sample or
   shuffle the candidate set with seeded RNG from an explicit support, using
   `sample_without_replacement` or `shuffled_support` when that shape fits.
   Then assign the selected candidates deterministically by object/order.
4. Do not use seed/hash/cursor modulo as the random visual candidate selector.
   Use modulo cycling only when repeated assignment is intentional, such as
   cycling through an already-selected palette because there are more rendered
   objects than available distinct colors.
5. Use only coordinate-preserving post-image noise.
6. Record meaningful style, font, palette, marker, and layout choices in render
   metadata.
7. Semantic visual attributes must not accidentally correlate with answer value,
   query id, correct option, or construction order.

## Docs And Review Checklist
1. Update the affected task doc under
   `docs/tasks/<domain>/<scene_id>/<task_id>.md`.
2. Run `PYTHONPATH=. python scripts/audit_task_reasoning_operations.py` and
   require the task doc's `## Reasoning Operations` block to match the public
   task class. Use `--sync-docs` only after the code declaration is reviewed.
3. Regenerate `docs/ACTIVE_TASK_INVENTORY.md` when active tasks, scenes, or
   taxonomy mappings change.
4. Update the matching domain doc only for domain-specific policy changes.
5. Update workflow or contract docs only when the reusable process or ABI
   changes.
6. Generate review artifacts only under `review/task-reviews/`.
7. Use the browser review app as the default inspection surface. Reload its
   index after artifact changes and restart it after app/indexer/schema changes.

## Standard Checks
Run focused tests first, then the relevant docs and surface checks:

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python scripts/audit_active_domain_surfaces.py
PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache
PYTHONPATH=. python scripts/audit_task_reasoning_operations.py
PYTHONPATH=. python scripts/check_skill_consistency.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_docs_consistency.py
git diff --check -- docs skills scripts tests trace configs prompts review assets AGENTS.md README.md
```

For broad prompt edits, also run:

```bash
PYTHONPATH=. python scripts/audit_prompt_concision.py --variant-coverage --samples-per-query-id 1 --include-all-prompts --output samples/prompt_concision_audit_all.md
```

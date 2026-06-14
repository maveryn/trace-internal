# TRACE Task Authoring Guide

Use this as the procedural checklist for adding or modifying tasks. Keep policy
definitions in `docs/contracts/`; this file should tell an implementer what to
do and where to verify it.

## Read First
1. `docs/contracts/TAXONOMY.md`
2. `docs/contracts/TASK_UNIT_POLICY.md`
3. `docs/contracts/PROGRAM_SCHEMA_CATALOG.md`
4. `docs/contracts/PROMPT_SYSTEM.md`
5. `docs/contracts/RLVR_REWARD_CONTRACTS.md`
6. The matching domain contract in `docs/domains/`
7. `docs/SCENE_PACKAGE_MIGRATION/README.md` for scene-package migrations

## Before Coding
1. Confirm `domain`, `scene_id`, and public `task_id`.
2. Confirm the task is one stable scene contract plus one objective contract:
   answer schema, annotation schema, and concrete program schema.
3. Decide which branches are valid internal `query_id` values. Split the public
   task if a branch changes the answer type, annotation type, witness roles,
   program skeleton, or visible task scaffold.
4. Check `docs/ACTIVE_TASK_INVENTORY.md` and nearby
   `docs/tasks/<domain>/<scene_id>/<task_id>.md` files before adding a new one.
5. Search for reusable helpers before writing new logic:
   `trace/core/`, `trace/tasks/shared/`, `trace/tasks/<domain>/shared/`, and
   `trace/tasks/<domain>/<scene_id>/shared/`.
6. Pick the narrowest helper layer that fits. Promote helpers only after real
   reuse or an approved domain shared boundary.

## Implementation Checklist
1. Put the public task module in the documented layout. Review-candidate
   scene-package tasks use
   `trace/tasks/<domain>/<scene_id>/<objective_contract>.py`.
2. Register the task with `@register_task` and make sure the module is imported
   through the active task registration path.
3. Keep user-facing prompt text in external prompt bundles, not task modules.
4. Resolve and validate `query_id` in the public task file. Pass semantic
   arguments to shared helpers; do not route shared code by task id, query id,
   or objective name.
5. Build the final output from one execution trace:
   typed `answer_gt`, typed `annotation_gt`, prompt slots, render/projection
   data, witness records, and `TaskOutput`.
6. Keep randomness explicit, deterministic from seed/spec/version inputs, and
   recorded when it affects prompts, layout, rendering, answer, or annotation.
7. Enforce unique final answers by construction. Use bounded resampling and do
   not silently relax semantic constraints.
8. Do not emit scalar difficulty fields or hand-authored reward contracts from
   task code.
9. Remove retired task ids, wrapper aliases, disabled registry entries, stale
   configs, stale prompt branches, and stale review paths in the same change.

## Prompt Checklist
1. Use prompt bundles under `prompts/<domain>/<scene_id>/` for migrated scenes.
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
7. Use `annotation` terminology in prompt-facing text.

## Annotation Checklist
1. Annotation marks minimal visual witnesses, not answer labels, unless the
   task is a true visual option-image task.
2. Use the global annotation types in
   `docs/contracts/RLVR_REWARD_CONTRACTS.md`.
3. Prefer keyed annotation when role binding matters or an unordered set would
   be ambiguous.
4. Use unordered sets only for homogeneous witness collections where order and
   identity do not matter.
5. Avoid mixed point/box annotation; revise the task contract before adding a
   new public annotation type.

## Config And Sampling Checklist
1. Use precedence: domain defaults, scene defaults, task/params.
2. Keep scene configs scoped to generation/rendering/prompt knobs. Do not put
   public objective dispatch, task coverage, query weights, or retired
   difficulty gates in config.
3. Query sampling happens inside the selected task and is uniform by default.
4. Keep visual-representation axes such as style, chart type, board skin, font,
   and layout jitter in metadata such as `scene_variant`, not public task ids,
   unless the visible scaffold changes the objective contract.
5. Answer supports should be constructively feasible and contiguous unless task
   semantics make interior values impossible.
6. Use the same seeded sampler for review, calibration, and dataset generation.

## Visual And Resource Checklist
1. Use shared font, label, context-text, marker-legibility, and text-legibility
   resources where applicable:
   - `docs/resources/SHARED_FONT_ASSETS.md`
   - `docs/resources/SHARED_LABEL_ASSETS.md`
   - `docs/resources/SHARED_CONTEXT_TEXT_ASSETS.md`
2. Sample non-semantic visual variety before projection so annotation
   coordinates remain valid.
3. Use only coordinate-preserving post-image noise.
4. Record meaningful style, font, palette, marker, and layout choices in render
   metadata.
5. Semantic visual attributes must not accidentally correlate with answer value,
   query id, correct option, or construction order.

## Docs And Review Checklist
1. Update the affected task doc under
   `docs/tasks/<domain>/<scene_id>/<task_id>.md`.
2. Regenerate `docs/ACTIVE_TASK_INVENTORY.md` when active tasks, scenes, or
   taxonomy mappings change.
3. Update the matching domain doc only for domain-specific policy changes.
4. Update workflow or contract docs only when the reusable process or ABI
   changes.
5. Generate review artifacts only under `review/task-reviews/`.
6. Use the browser review app as the default inspection surface. Reload its
   index after artifact changes and restart it after app/indexer/schema changes.

## Standard Checks
Run focused tests first, then the relevant docs and surface checks:

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python scripts/audit_active_domain_surfaces.py
PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache
PYTHONPATH=. python scripts/check_skill_consistency.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_docs_consistency.py
git diff --check -- docs skills scripts tests trace configs prompts review assets AGENTS.md README.md
```

For broad prompt edits, also run:

```bash
PYTHONPATH=. python scripts/audit_prompt_concision.py --variant-coverage --samples-per-query-id 1 --include-all-prompts --output samples/prompt_concision_audit_all.md
```

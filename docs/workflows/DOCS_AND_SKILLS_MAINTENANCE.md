# Docs And Skills Maintenance

Use this checklist whenever code, taxonomy, prompt, config, task-review, or
skill surfaces change. The goal is to keep one current repo status instead of
letting historical inventories or old task names become hidden policy.

## Source-Of-Truth Order
Documentation placement rules live in `docs/workflows/DOC_STRUCTURE.md`.

1. Runtime behavior lives in code, configs, prompts, and assets.
2. Active task/domain inventory is generated in `docs/ACTIVE_TASK_INVENTORY.md`.
3. Domain setup docs in `docs/domains/` define domain contracts, boundaries,
   annotation policy, and scene-specific rules. They should not be the only
   exhaustive task inventory unless a generated check covers the list.
4. Task docs in `docs/tasks/` define public task contracts.
5. Repo-local skills under `skills/` are operational overlays. They point to
   source-of-truth docs and may add short review checklists, but they must not
   redefine taxonomy, active task lists, calibration gates, or domain policy.

## Code Documentation Rules
1. Add docstrings for new modules, classes, and non-trivial functions.
2. Document ownership, key inputs/outputs, determinism assumptions, and
   non-obvious rejection/failure behavior.
3. Prefer comments that explain why a constraint or boundary exists, not
   line-by-line restatements of code.
4. Use repo-relative paths in docs and comments; do not write local absolute
   filesystem paths into source-of-truth docs.

## Required Updates
Update docs and skills in the same patch when changing any of these surfaces:

1. Active domain, scene, task id, task registration, or taxonomy mapping.
2. Task answer schema, annotation schema, verifier contract, query ids, or prompt
   output-mode examples.
3. Prompt bundle path, bundle id, template layer behavior, or prompt wording
   policy.
4. Domain/scene config defaults for generation, rendering, visual style,
   difficulty knobs, or prompt slots.
5. Shared helper ownership, module boundaries, or reusable rendering/style
   infrastructure.
6. Calibration gates, vLLM serving instructions, task-review workflow, or saved
   artifact layout.
7. Domain boundary changes, including moving a scene/task between domains.

## Update Triggers
1. ABI/contract changes -> `docs/contracts/BLUEPRINT.md`.
2. Architecture/module flow changes -> `docs/contracts/SYSTEM_ARCHITECTURE.md`.
3. Prompt-system changes -> `docs/contracts/PROMPT_SYSTEM.md`.
4. Public answer/annotation reward-contract changes ->
   `docs/contracts/ANNOTATION_AND_REWARD_CONTRACTS.md`.
5. Shared-helper placement/API changes -> `docs/contracts/SOURCE_LAYOUT.md`,
   `docs/contracts/SYSTEM_ARCHITECTURE.md`, or the relevant domain contract
   in `docs/domains/`.
6. Validation/build behavior changes -> `docs/workflows/BUILD_VALIDATION.md`
   and `docs/contracts/VALIDATION_ERROR_CODES.md`.
7. Task behavior changes -> the affected
   `docs/tasks/<domain>/<scene_id>/<task_id>.md`,
   `docs/ACTIVE_TASK_INVENTORY.md`, and `docs/tasks/README.md` only when the
   task-doc process itself changes.
8. Docs/skills navigation or source-of-truth ownership changes ->
   `docs/workflows/DOC_STRUCTURE.md`, this file, `docs/README.md`,
   `docs/workflows/README.md`, and `skills/README.md`.

## What To Update
For active task or taxonomy changes:

1. Regenerate `docs/ACTIVE_TASK_INVENTORY.md`.
2. Update the affected `docs/tasks/<domain>/<scene_id>/<task_id>.md` files.
3. Update the relevant domain setup doc under `docs/domains/`.
4. Update prompt docs only when the prompt-system contract changes; do not copy
   exhaustive prompt-bundle maps by hand.
5. Update a workflow skill only when its routing, stop conditions, or handoff
   expectations changed. Do not add domain-skill mirrors.

## Anti-Drift Rules
1. Do not add historical migration prose to active docs.
2. Do not keep old task ids, old domain names, retired task inventories, or
   disabled-task notes in source-of-truth docs.
3. Do not duplicate exhaustive active task inventories outside
   `docs/ACTIVE_TASK_INVENTORY.md` and generated or checked task docs.
4. Do not make a skill the only place where a behavior rule is written.
5. Do not leave prompt examples, annotation hints, or task-review paths using a
   task id that is not active.
6. Do not describe a task with inactive public domain names. Use the active
   public domain and scene names from `docs/ACTIVE_TASK_INVENTORY.md`.

## Validation
Run the relevant focused tests for the changed domain, then run the docs and
surface checks below before handing work back:

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python scripts/audit_active_domain_surfaces.py
PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache
PYTHONPATH=. python scripts/check_skill_consistency.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_docs_consistency.py
git diff --check -- docs skills scripts tests trace configs prompts review assets AGENTS.md README.md
```

If a broad prompt edit lands, also run:

```bash
PYTHONPATH=. python scripts/audit_prompt_concision.py --variant-coverage --samples-per-query-id 1 --include-all-prompts --output samples/prompt_concision_audit_all.md
```

Remove local cache artifacts such as `__pycache__/`, `.pytest_cache/`, and
`.ipynb_checkpoints/` after running checks.

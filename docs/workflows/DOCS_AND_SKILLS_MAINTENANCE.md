# Docs And Skills Maintenance

Use this checklist whenever code, taxonomy, prompt, config, task-review, or
skill surfaces change. The goal is to keep one current repo status instead of
letting historical inventories or old task names become hidden policy.

## Source-Of-Truth Order
1. Runtime behavior lives in code, configs, prompts, and assets.
2. Active task/domain inventory is generated in `docs/ACTIVE_TASK_INVENTORY.md`.
3. Domain setup docs in `docs/domains/` define domain contracts, boundaries,
   evidence policy, and scene-specific rules. They should not be the only
   exhaustive task inventory unless a generated check covers the list.
4. Task docs in `docs/tasks/` define public task contracts.
5. Project status lives in `docs/project/STATUS.md` and should stay compact.
6. Repo-local skills under `skills/` are operational overlays. They point to
   source-of-truth docs and may add short review checklists, but they must not
   redefine taxonomy, active task lists, calibration gates, or domain policy.

## Required Updates
Update docs and skills in the same patch when changing any of these surfaces:

1. Active domain, scene, task id, task registration, or taxonomy mapping.
2. Task answer schema, evidence schema, verifier contract, query ids, or prompt
   output-mode examples.
3. Prompt bundle path, bundle id, template layer behavior, or prompt wording
   policy.
4. Domain/task-group config defaults for generation, rendering, visual style,
   complexity, or prompt slots.
5. Shared helper ownership, module boundaries, or reusable rendering/style
   infrastructure.
6. Calibration gates, vLLM serving instructions, task-review workflow, or saved
   artifact layout.
7. Domain boundary changes, including moving a scene/task between domains.

## What To Update
For active task or taxonomy changes:

1. Regenerate `docs/ACTIVE_TASK_INVENTORY.md`.
2. Update `docs/tasks/README.md` and the affected `docs/tasks/<task_id>.md`
   files.
3. Update the relevant domain setup doc under `docs/domains/`.
4. Update `docs/project/STATUS.md` if counts, contracts, or validation guidance
   changed.
5. Update prompt docs only when the prompt-system contract changes; do not copy
   exhaustive prompt-bundle maps by hand.
6. Update the matching `skills/domain-<domain>/SKILL.md` only if its short
   operational checklist or linked docs changed.
7. Update `skills/task-complexity/references/<domain>.md` only if complexity
   criteria or weighting intent changed.

## Anti-Drift Rules
1. Do not add historical migration prose to active docs.
2. Do not keep old task ids, old domain names, retired task inventories, or
   disabled-task notes in source-of-truth docs.
3. Do not duplicate exhaustive active task inventories outside
   `docs/ACTIVE_TASK_INVENTORY.md`, `docs/tasks/README.md`, and generated or
   checked task docs.
4. Do not make a skill the only place where a behavior rule is written.
5. Do not leave prompt examples, evidence hints, or task-review paths using a
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

# Domain Refactor Agent Brief

Date: 2026-05-27

Use this brief when assigning another agent to work on one TRACE domain during
the task-unit refactor, audit, and calibration cleanup. This is a working
handoff document, not a replacement for the source-of-truth docs.

## Read First

Before touching code, read these files in order:

1. `AGENTS.md`
2. `docs/README.md`
3. `docs/core/TASK_UNIT_POLICY.md`
4. `docs/workflows/TASK_UNIT_AUDIT.md`
5. `plans/MERGE_SPLIT_REFACTOR_REFERENCE.md`
6. `plans/CALIBRATION_PLAN.md`
7. The active domain setup doc under `docs/domains/`
8. `docs/workflows/SHARED_UTILITIES.md`
9. `docs/workflows/CODE_REVIEW_GUIDELINES.md`

If these disagree, stop and report the conflict. Do not invent a local policy.

## Assignment Scope

Work one domain at a time. Do not touch other domains unless the reviewer
explicitly asks for a cross-domain shared-helper change.

The reviewer decides:

- which domain is active,
- which merge/split candidates to apply,
- which task/config changes to make,
- whether to add a new task or scene,
- when to run solve-rate calibration.

Agents may inspect, summarize, propose, and implement reviewer-approved changes.
Do not auto-tune configs, auto-delete tasks, or add Vero-derived tasks without
explicit approval.

## Current Public Taxonomy

The public taxonomy is:

`domain -> scene_id -> task_id`

Task ids use:

`task_<domain>__<scene_id>__<objective_contract>`

Rules:

- `task_group` is implementation/config organization, not public taxonomy.
- `query_id` is the task-internal branch identity.
- A public task must keep one stable answer schema and one stable evidence
  schema across all query branches.
- Prompt text must come from external prompt bundles, not task modules.

## Task Boundary Rule

Use `docs/core/TASK_UNIT_POLICY.md` as the hard boundary. A task is one stable
combination of:

1. scene grammar,
2. primary witness kind,
3. visual search pattern,
4. algorithmic/objective family.

Merge only when all four match and the difference is a query-local operator,
predicate, mirror direction, ordering choice, or local arithmetic transform.

Split when one task mixes genuinely different objective families or materially
different visual search contracts.

When unsure, do not refactor. Record the uncertainty and ask the reviewer.

## Domain Workflow

### 1. Sync Inventory

For the assigned domain:

1. List active task ids by scene from the registry/taxonomy.
2. Compare against `plans/MERGE_SPLIT_REFACTOR_REFERENCE.md`.
3. Check current docs, configs, prompt bundles, tests, and task-review folders
   for stale task ids or stale domain names.
4. Report the current domain task count, scene count, and proposed delta before
   editing.

### 2. Apply Approved Refactors

For each reviewer-approved merge or split:

1. Update registrations and taxonomy entries.
2. Keep task-internal branches as explicit `query_id`s.
3. Delete retired public task ids rather than leaving disabled compatibility
   tasks.
4. Update configs, prompt bundles, task docs, domain docs, tests, and review
   artifact paths.
5. Remove stale imports and stale task-review folders for deleted ids.
6. Preserve deterministic generation for fixed seeds.

For merged or split tasks, do not copy old solve-rate results as current
acceptance. Regenerate review artifacts and leave solve-rate cells blank unless
fresh current-baseline calibration is run.

### 3. Prompt And Contract Audit

Before calibration work, audit prompts and contracts for the domain:

- no repeated scene description,
- no duplicated answer-format rule,
- no stale task-family or task-variant wording,
- MCQ options rendered in the image, not only in prompt text,
- MCQ tasks have at least five visible options,
- decimal-answer prompts require exactly one decimal place when applicable,
- visible `?` markers are target locators by default, not evidence, unless
  the task explicitly localizes a missing slot,
- answer, evidence, prompt, rendered image, and verifier trace agree exactly.

### 4. Visual And Sampling Audit

Scene by scene, inspect:

- shared font usage for meaningful text blocks,
- safe style/background/palette variation,
- safe layout jitter without evidence drift,
- text/label/tick/option overlap at max density,
- distractor/context text placement for charts, graphs, and pages,
- broad enough object/name/icon pools for the scene,
- continuous input and answer supports unless the task semantics require a
  structured support,
- answer distribution by `query_id`, scene variant, option count, object count,
  chart/map/board type, and any other meaningful knob.

### 5. Task Review Artifacts

Generate fresh current-baseline review artifacts only from current code/config.

Current baseline is `v0`.

Task and scene review workbooks belong under:

`plans/task-reviews/<domain>/<scene_id>/<task_id>/`

Scene review workbook:

`plans/task-reviews/<domain>/<scene_id>/scene_review.xlsx`

Scene review workbooks should include `model_stats` first when model stats
exist, then one sheet per task. For visual/prompt inspection, use the current
calibration sample policy from `plans/CALIBRATION_PLAN.md`.

Delete stale active artifacts for removed ids and stale non-`v0` artifacts for
the scope being regenerated.

### 6. Calibration

Do not run solve-rate calibration unless the reviewer asks.

When asked, use only the current calibration plan:

- model: `qwen25vl7b`
- endpoint: `http://127.0.0.1:8002/v1`
- lock: `logs/vllm/locks/qwen25vl7b_8002.lock`
- prompt budget: `2048`
- samples: `100`
- rollouts per sample: `24`
- current baseline: `v0`

If the endpoint is busy, wait on the lock. Do not start another local vLLM
server.

Acceptance gates are defined only in `plans/CALIBRATION_PLAN.md`.

### 7. New Task Or Scene Proposals

Vero-derived or coverage-extension ideas are proposals until the reviewer
approves them.

For each proposal, report:

- target domain and scene,
- whether it is a new task in an existing scene or a new scene,
- why it is distinct under the task boundary rule,
- answer schema and evidence schema,
- expected query ids,
- rendering/visual variation plan,
- why it is not a duplicate of an existing task.

Do not implement until explicitly approved.

### 8. Complexity Pass

Only run the complexity update after the reviewer says the domain task set is
accepted.

Use the current domain-level complexity requirements from
`plans/CALIBRATION_PLAN.md`:

- at most six axes per task,
- remove axes with weight `< 0.05`,
- target at least `0.40` Spearman correlation with model difficulty
  (`1 - solve_rate`) per task.

## Required Handoff

At the end of a domain work chunk, report:

- domain worked,
- task count before and after,
- scenes touched,
- task ids added, deleted, merged, or split,
- docs/configs/prompts/tests/review artifacts updated,
- checks run and results,
- current blockers or reviewer decisions needed.

Do not claim a domain is done unless it satisfies the domain definition of done
in `plans/CALIBRATION_PLAN.md`.

## Minimum Checks

Run targeted checks for touched files and the relevant domain. At minimum:

```bash
git diff --check -- <touched paths>
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 pytest -q tests/test_docs_consistency.py
```

Also run the domain-specific registry/taxonomy/tests named by the touched code
or docs. If a test is unavailable or too expensive, say so in the handoff.

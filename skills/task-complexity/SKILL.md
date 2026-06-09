---
name: task-complexity
description: Use when defining or revising TRACE task complexity policy, especially for within-task normalized difficulty, domain-level complexity criteria, task-group weight overrides, and migration away from ad hoc scalar `complexity_score` formulas.
---

# Task Complexity

Use this whenever a change touches `complexity_score`, `complexity_components`, curriculum buckets, or domain/scene difficulty policy.

## Read first
1. `docs/workflows/TASK_AUTHORING.md`
2. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
3. `docs/project/STATUS.md`
4. `docs/TODO.md`
5. `skills/README.md`

## Core policy
- Treat `complexity_score` as **within-task normalized difficulty only**.
- Make tasks emit normalized criterion values in `[0,1]`; do not compare raw scores across tasks or domains.
- Keep raw-to-normalized transforms in task/domain code, not in config.
- Let config own **weights and active criteria**, with precedence `domain -> task_group -> task`.
- Keep **domain-level criteria** broad enough that every task in the domain can score them meaningfully.
- Keep **task-group criteria** broad enough that every task in that family can score them meaningfully.
- Use task-level criteria or weight overrides only when a task materially breaks the family pattern; this should be rare.
- Treat existing one-off scalar formulas as source. Do not copy them forward when touching a task.

## Workflow
1. Open the domain reference from `references/` and choose the base criteria vocabulary for that domain.
2. Verify each domain-level criterion is genuinely applicable to every task in the domain.
3. Add task-group criteria only when they apply to every task in that family.
4. Decide the default domain weights and any task-group override weights.
5. In the task code, measure each active criterion and normalize it into `[0,1]`.
6. Keep any raw diagnostics in trace/debug payloads, not in `complexity_components`.
7. Compute the final score from the resolved weights over the normalized criterion values.
8. Check monotonicity against the task's obvious difficulty knobs before finalizing.

## Read as needed
- General policy and config shape: `references/policy.md`
- Domain-specific guidance: every active domain must have `references/<domain>.md`.
- For migrated scene types, use the domain where the task now lives. For example, clock scenes use the misc reference, while calendar, schedule, and timeline scenes use the pages reference.

## Update discipline
- When adding a new domain, add the corresponding domain reference in this skill in the same change and run `PYTHONPATH=. python scripts/check_skill_consistency.py`.
- When adding a new scene, update the relevant domain reference only if the scene introduces reusable complexity policy.
- When introducing a new criterion name, update the domain reference before using it in task code.
- When moving a criterion upward (task -> task_group or task_group -> domain), verify the broader scope can score it for every task before promoting it.
- When migrating a source task, preserve the task's relative easy/medium/hard ordering as closely as possible while moving to named normalized criteria.

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-implementation/SKILL.md`
- relevant domain skills under `skills/domain-*/SKILL.md`

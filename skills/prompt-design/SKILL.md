---
name: prompt-design
description: Use when adding or updating Trace prompt bundles, prompt slots, JSON examples, or prompt metadata and output-mode wiring.
---

# Prompt Design

Use this when creating or changing prompt bundles or prompt-facing contract wording.

## Read first
1. `docs/contracts/PROMPT_SYSTEM.md`
2. `docs/workflows/TASK_AUTHORING.md`
3. `docs/contracts/ANNOTATION_AND_REWARD_CONTRACTS.md` when output-mode examples include annotation

## Prompt workflow
1. Keep bundle structure aligned to Trace's composition layers:
   - scene,
   - task,
   - optional query,
   - output mode.
2. Keep exactly 5 strong variants per required template list.
3. Use static prompt slots from bundle/config data, not task-module constants.
4. Make every JSON example contract-valid for the active task and annotation type.
5. Record prompt metadata in trace payload.

## Prompt checks
- No hardcoded user-facing prompt text in task modules.
- `answer_only` and `answer_and_annotation` must both have explicit JSON response instructions.
- If a task mentions a color, pass it as `name [#RRGGBB]` through the shared formatter.
- If query branches change annotation structure or semantics, examples must be query-aware too.
- Keep task-layer wording semantic; do not duplicate formatting instructions already carried by scene or mode templates.

## Stop conditions
- If prompt wording changes the task boundary or answer/annotation schema,
  switch to `skills/task-unit-audit/SKILL.md` before editing templates.
- If prompt changes affect generated samples, use
  `skills/verification-review/SKILL.md` after implementation.

## Handoff
After prompt wiring is stable, run `skills/verification-review/SKILL.md`.

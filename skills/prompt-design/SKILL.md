---
name: prompt-design
description: Use when adding or updating TRACE prompt bundles, prompt slots, JSON examples, or prompt metadata and output-mode wiring.
---

# Prompt Design

Use this when creating or changing prompt bundles or prompt-facing contract wording.

## Read first
1. `docs/core/PROMPT_SYSTEM.md`
2. `docs/workflows/TASK_AUTHORING.md`

## Prompt workflow
1. Keep bundle structure aligned to TRACE's composition layers:
   - scene,
   - task,
   - optional query,
   - output mode.
2. Keep exactly 5 strong variants per required template list.
3. Use static prompt slots from bundle/config data, not task-module constants.
4. Make every JSON example contract-valid for the active task and evidence type.
5. Record prompt metadata in trace payload.

## Prompt checks
- No hardcoded user-facing prompt text in task modules.
- `answer_only` and `answer_and_evidence` must both have explicit JSON response instructions.
- If a task mentions a color, pass it as `name [#RRGGBB]` through the shared formatter.
- If query branches change evidence structure or semantics, examples must be query-aware too.
- Keep task-layer wording semantic; do not duplicate formatting instructions already carried by scene or mode templates.

## Handoff
After prompt wiring is stable, run `skills/verification-review/SKILL.md`.

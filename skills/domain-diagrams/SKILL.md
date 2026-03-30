---
name: domain-diagrams
description: Use when designing, implementing, or reviewing TRACE diagrams-domain tasks, especially flowcharts, swimlanes, hierarchies, cycles, set diagrams, and annotated schematics with clean local evidence contracts.
---

# Diagrams Domain

Use this whenever the task lives under `domain=diagrams`.

## Read first
1. `docs/project/STATUS.md`
2. `docs/project/TODO.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`
5. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
6. `docs/domains/DIAGRAM_TASK_SETUP.md`

## Diagrams-domain rules
- Treat `diagrams` as schematic visual reasoning over boxes, arrows, lanes, cycles, or set regions, not as generic graph or document tasks with a new skin.
- Prefer broad families such as `flow`, `hierarchy`, `cycle`, `set_diagram`, and `schematic` over one-off templates.
- Reuse one shared scene contract whenever multiple tasks use the same diagram grammar.
- Keep prompts explicit when branch labels or containment rules matter.

## Boundary rules
- If the task is mostly generic graph topology with free node placement, it likely belongs in `graph`.
- If the task is mostly page-like field reading, it likely belongs in `documents`.
- If the reasoning depends on arrows, lanes, parent-child connectors, stage ordering, or explicit set overlap regions, it is a good fit for `diagrams`.

## Early-family guidance
- `flow`: labeled process nodes plus arrows; good early tasks are next-step and terminal-outcome questions.
- `swimlane` is a visual scene variant within `flow`, not a separate task group.
- `hierarchy`: labeled parent/child containment over tree connectors; good early tasks are parent lookup and lowest-common-ancestor lookup with one-box target evidence.
- Active `cycle`: ordered `k`-step before/after reasoning over circular process layouts with short visible labels and one-box target-stage evidence.
- Active `set_diagram`: numeric `3`-set overlap reasoning over one digit per region, with sum queries grounded on the contributing digit boxes.
- Active `schematic`: annotated part-and-callout reasoning where prompts should stay explicit about whether the query names a part or relies on a highlighted part.

## Evidence rules
- Flow next-step tasks should ground prompt-facing evidence on the single target step box.
- Schematic callout-target tasks should ground prompt-facing evidence on the single queried part, not on the answer callout badge.
- Keep edge-label bboxes and lane bboxes in trace for review/debugging, but do not widen prompt-facing evidence to whole paths when the answer is one visible target node.

## First-family lessons
- The first reusable flow scene should support both plain flowchart and swimlane variants while preserving the same step/arrow semantics.
- Short visible node labels are preferable to long prose inside boxes.
- Branch questions should make the active branch label explicit in the prompt so the solver does not infer hidden branch semantics.

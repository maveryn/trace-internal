---
name: domain-diagrams
description: Use when designing, implementing, or reviewing TRACE diagrams-domain tasks, especially flowcharts, swimlanes, hierarchies, cycles, set diagrams, and annotated schematics with clean local evidence contracts.
---

# Diagrams Domain

Use this whenever the task lives under `domain=diagrams`.

## Read first
1. `docs/domains/DIAGRAM_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- Treat `diagrams` as schematic visual reasoning over boxes, arrows, lanes, cycles, or set regions, not as generic graph or document tasks with a new skin.
- Prefer broad families such as `flow`, `hierarchy`, `cycle`, `set_diagram`, and `schematic` over one-off templates.
- Reuse one shared scene contract whenever multiple tasks use the same diagram grammar.
- Keep prompts explicit when branch labels or containment rules matter.
- `docs/domains/DIAGRAM_TASK_SETUP.md` owns the active diagrams contract.

## Boundary reminders
- If the task is mostly generic graph topology with free node placement, it likely belongs in `graph`.
- If the task is mostly page-like field reading, it likely belongs in `documents`.
- If the reasoning depends on arrows, lanes, parent-child connectors, stage ordering, or explicit set overlap regions, it is a good fit for `diagrams`.

## Practical review checklist
- Keep prompt-facing evidence local to the decisive diagram element rather than widening to whole paths or full subtrees.
- Reuse the same renderer/scene grammar before adding a second diagram scaffold for the same family.
- Keep short visible labels; avoid turning diagram tasks into mini documents with long prose inside boxes.
- Make branch labels, containment semantics, and set-overlap semantics explicit in the prompt whenever they matter.

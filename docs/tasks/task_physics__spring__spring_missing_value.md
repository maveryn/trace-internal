# `task_physics__spring__spring_missing_value`

## Summary
- Domain: `physics`
- Scene id: `spring`
- Task group: `mechanics`
- Query id: `missing_value`
- Answer type: `integer`
- Evidence type: `keyed_bbox_map`

## Contract
The image shows two identical springs with rulers and weight blocks. The task asks for a missing weight or missing extension using the proportional relation represented by the reference spring.

Evidence contains the reference weight and extension markers plus the queried value and its paired measurement. The prompt-facing keys are `reference_weight`, `reference_extension`, `query_weight`, and `query_extension`; whichever query value is marked red `?` remains under its semantic key. `solve_for=weight|extension` is an inverse parameter inside this task.

Evidence is projected after the final whole-diagram layout offset, so each bbox uses rendered pixel coordinates.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; family key: `paired_spring_diagram`; task key: `spring_extension_query`; query id key: `missing_value`.

Outputs `query_id="missing_value"`. The trace records the scale factor, solve target, measurements, answer support, keyed evidence boxes, technical diagram style, font family, whole-diagram layout placement, and post-render noise metadata.

## Rendering
The renderer uses shared `technical_diagram_style` for the outer sheet, card/ruler palette, frame, and post-render noise. It samples one readout font family per diagram and applies whole-diagram layout placement before computing evidence.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized spring layout.

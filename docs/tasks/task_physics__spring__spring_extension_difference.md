# `task_physics__spring__spring_extension_difference`

## Summary
- Domain: `physics`
- Scene id: `spring`
- Task group: `mechanics`
- Query id: `extension_difference`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Contract
The image shows two identical springs with visible, value-labeled extension markers. The task asks for the absolute difference between the two shown extensions. The calibrated public mix uses extension-difference answers `{2,4,8,10,12}` and scale factor `2` so this query is not dominated by visually trivial small-difference cases.

Evidence is the pair of shown extension-marker bounding boxes. Scene variants affect card layout and texture only; they do not change the difference contract.

Evidence is projected after the final whole-diagram layout offset, so each bbox uses rendered pixel coordinates.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; family key: `paired_spring_diagram`; task key: `spring_extension_query`; query id key: `extension_difference`.

Outputs `query_id="extension_difference"`. The trace records both measurements, the query-specific scale-factor support, answer support, evidence entity ids, technical diagram style, font family, whole-diagram layout placement, and post-render noise metadata.

## Rendering
The renderer uses shared `technical_diagram_style` for the outer sheet, card/ruler palette, frame, and post-render noise. It samples one readout font family per diagram and applies whole-diagram layout placement before computing evidence.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized spring layout.

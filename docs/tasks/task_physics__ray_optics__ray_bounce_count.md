# `task_physics__ray_optics__ray_bounce_count`

## Summary
- Domain: `physics`
- Scene id: `ray_optics`
- Task group: `optics`
- Query id: `bounce_count`
- Answer type: `integer`
- Evidence type: unordered `point_set`

## Contract
The image shows a graph-paper ray setup with an initial direction and diagonal mirrors. The task asks how many mirror reflections occur before the implied ray exits the board.

Evidence is the set of rendered mirror-bounce pixel points. The calibrated public mix uses the `five_mirror` scene with answer support `1..5`, where bounce counts are constructively controlled without zero-bounce cases.

Evidence is projected after the final whole-board layout offset, so each point uses rendered pixel coordinates.

## Prompt And Trace
Prompt bundle: `physics_optics_v0`; family key: `mirror_ray_diagram`; task key: `ray_trace_query`; query id key: `bounce_count`.

Outputs `query_id="bounce_count"`. The trace records mirror placements, path cells, bounce cells, answer support, evidence points, technical diagram style, font family, whole-board layout placement, and post-render noise metadata.

## Rendering
The renderer uses shared `technical_diagram_style` for the outer sheet, board/grid palette, frame, and post-render noise. It samples one readout font family per board and applies whole-board layout placement before computing evidence.

## Determinism
Generation is deterministic from `instance_seed`. The prompt image does not draw the solved full ray path; evidence comes from the hidden trace path.

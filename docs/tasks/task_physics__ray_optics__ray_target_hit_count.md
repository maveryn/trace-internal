# `task_physics__ray_optics__ray_target_hit_count`

## Summary
- Domain: `physics`
- Scene id: `ray_optics`
- Task group: `optics`
- Query id: `target_hit_count`
- Answer type: `integer`
- Evidence type: unordered `point_set`

## Contract
The image shows a graph-paper ray setup with an initial direction, one to three diagonal mirrors, and target points. The task asks how many target points the implied ray touches before exit.

Evidence is the set of rendered hit-target pixel points. Mirror-count scene variants stay inside this task because they are scene support knobs for the same target-hit counting contract.

Evidence is projected after the final whole-board layout offset, so each point uses rendered pixel coordinates.

## Prompt And Trace
Prompt bundle: `physics_optics_v0`; family key: `mirror_ray_diagram`; task key: `ray_trace_query`; query id key: `target_hit_count`.

Outputs `query_id="target_hit_count"`. The calibrated public mix uses answers `1..5`, four or five target points, and no `quad_mirror` scenes. The trace records mirror placements, target placements, path cells, answer support, evidence points, technical diagram style, font family, whole-board layout placement, and post-render noise metadata.

## Rendering
The renderer uses shared `technical_diagram_style` for the outer sheet, board/grid palette, frame, and post-render noise. It samples one readout font family per board and applies whole-board layout placement before computing evidence.

## Determinism
Generation is deterministic from `instance_seed`. The prompt image does not draw the solved full ray path; evidence comes from the hidden trace path.

# `task_geometry__cuboid_views__cuboid_projection_surface_area_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `cuboid_views`
4. Public query id: `default`
5. Query id: `surface_area_from_orthographic_views`
6. Answer type: `number`
7. Evidence type: `keyed_bbox_map`

## Prompt Bundle
- Bundle id: `geometry_cuboid_orthographic_views_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Compute the total surface area of a cuboid from its front, right, and top orthographic rectangular views. The visible labels give the three view perimeters, from which `L`, `W`, and `H` are inferred before computing `2(LW + LH + WH)` as an integer.

## Evidence
Prompt-facing evidence is a `keyed_bbox_map` over the three visible orthographic view rectangles: `top_view`, `front_view`, and `right_view`. Each rectangle contains the perimeter label used to infer the cuboid dimensions. The `SA=?` cue remains render metadata, not public evidence. Verifier evidence is projected from the same generated scene metadata used to compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/cuboid_orthographic_views.py`

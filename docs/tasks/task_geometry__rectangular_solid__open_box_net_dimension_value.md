# `task_geometry__rectangular_solid__open_box_net_dimension_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `rectangular_solid`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query ids: `open_box_dimension_from_corner_cut`, `open_box_volume_from_net`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_corner_cut_open_box_net, unknown_role=base_length_or_base_width_or_volume, formula_schema=open_box_net_corner_cut); scene=rectangular_solid; scope=open_box_net_dimension_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_rectangular_solid_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `sheet_bbox`, `cutout_bbox`, `base_panel_bbox`, and `target_region_bbox`. Sheet labels, cut-size labels, fold hints, hatching, and `?` markers are visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/rectangular_solid.py`

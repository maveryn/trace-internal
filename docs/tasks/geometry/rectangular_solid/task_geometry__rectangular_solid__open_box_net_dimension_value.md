# `task_geometry__rectangular_solid__open_box_net_dimension_value`

## Contract
1. Domain: `geometry`
2. Scene id: `rectangular_solid`
3. Task id: `task_geometry__rectangular_solid__open_box_net_dimension_value`
4. Supported `query_id` values: `open_box_dimension_from_corner_cut`, `open_box_volume_from_net`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task always binds sheet, cutout, base panel, and target region roles)

## Program Contract
- `solve_formula(corner_cut_open_box_net, unknown_role=base_dimension|volume, formula_schema=open_box_corner_cut_dimensions); scene=rectangular_solid; scope=open_box_net_dimension_value`

## Query Semantics
- `open_box_dimension_from_corner_cut` asks for one marked resulting base dimension after equal corner squares are removed and the sides fold up.
- `open_box_volume_from_net` asks for the resulting open-top box volume from the visible sheet dimensions and cut size.
- The sampled target base dimension role, sheet dimensions, cut size, style, font, and layout jitter are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/rectangular_solid/geometry_rectangular_solid_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed boxes: `sheet_bbox`, `cutout_bbox`, `base_panel_bbox`, and `target_region_bbox`. Sheet labels, cut labels, hatching, and the `?` marker remain visible diagram content and private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/rectangular_solid.yaml`
- Prompt bundle: `prompts/geometry/rectangular_solid/geometry_rectangular_solid_v1.json`
- Task module: `trace/tasks/geometry/rectangular_solid/open_box_net_dimension_value.py`

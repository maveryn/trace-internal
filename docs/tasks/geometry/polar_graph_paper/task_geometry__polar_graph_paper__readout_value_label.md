# task_geometry__polar_graph_paper__readout_value_label

## Contract
1. Domain: `geometry`
2. Scene id: `polar_graph_paper`
3. Query ids: `radius_readout_label`, `angle_readout_label`
4. Answer schema: `option_letter`
5. Annotation schema: `point`

## Program Contract
select_option(read_polar_graph_component(point=P, component in {radius, angle_degrees}), options=A..F); scene=polar_graph_paper; scope=readout_value_label

## Task Summary
- Scene: `polar_graph_paper`
- Objective contract: `readout_value_label`
- Public task id: `task_geometry__polar_graph_paper__readout_value_label`
- Query ids: `radius_readout_label`, `angle_readout_label`

## Answer Schema
- `option_letter`
- The answer is the visible option label `A` through `F` whose displayed value matches the requested readout.

## Annotation Schema
- `point`
- The annotation is the pixel point at plotted point `P`.

## Query Semantics
- `radius_readout_label`: read the polar radius of point `P`.
- `angle_readout_label`: read the polar angle of point `P` in degrees.

## Rendering Notes
- The scene draws polar graph paper, point `P`, and exactly six visible options.
- Option ordering and distractor values are internal sampling metadata, not public query branches.
- The plotted point lies on a polar ring/spoke intersection by construction.

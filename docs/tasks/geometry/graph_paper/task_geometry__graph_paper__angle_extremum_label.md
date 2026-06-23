# `task_geometry__graph_paper__angle_extremum_label`

## Contract
1. Domain: `geometry`
2. Scene id: `graph_paper`
3. Task id: `task_geometry__graph_paper__angle_extremum_label`
4. Supported `query_id`: `largest`, `smallest`
5. Answer schema: `option_letter`
6. Annotation schema: `point_map`

## Program Contract
- `select_labeled_angle_extremum(extremum={largest|smallest}, output_role=angle_label); scene=graph_paper; scope=labeled_angle_set`

## Prompt Bundle
- Prompt text is loaded from `geometry_graph_paper_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
The annotation is a keyed pixel point map with keys `ray_a`, `vertex`, and `ray_b` for the selected angle.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

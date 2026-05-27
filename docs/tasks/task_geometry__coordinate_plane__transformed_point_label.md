# `task_geometry__coordinate_plane__transformed_point_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public query variant: `default`
5. Query id: `translate_point`, `translate_by_reference_vector`, `reflect_over_vertical_line`, `reflect_over_horizontal_line`, or `rotate_90_about_marked_center`
6. Answer type: `option_letter`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_coordinate_algebra_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the lettered candidate image point after applying the visible coordinate transformation to point `P`.

The scene supports translations by an integer vector, translations by a plotted reference vector, reflections over marked vertical or horizontal lines, and 90-degree rotations about a marked center. The verifier computes the target point from the metadata transformation and keeps exactly one candidate at that coordinate.

## Evidence
Verifier evidence is the final-image pixel bounding box around the selected candidate point. Graph coordinates, transformation text, reflection line, candidate points, and target image point are recorded in trace metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Query IDs, candidate labels, marker styles/colors, graph frame, transformation parameters, prompt bundle IDs, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Prompt bundle: `prompts/geometry/coordinate/geometry_coordinate_algebra_v0.json`
- Task module: `trace/tasks/geometry/coordinate/algebra.py`

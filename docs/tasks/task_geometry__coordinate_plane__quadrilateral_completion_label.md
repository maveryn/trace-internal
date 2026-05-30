# `task_geometry__coordinate_plane__quadrilateral_completion_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public query id: `default`
5. Query id: `parallelogram_completion_label`, `rectangle_completion_label`, `square_completion_label`, or `rhombus_completion_label`
6. Answer type: `option_letter`
7. Evidence type: `point_set`

## Prompt Bundle
- Bundle id: `geometry_coordinate_quadrilateral_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the lettered candidate point that completes the requested quadrilateral with the three unlabeled graph-paper points.

The scene samples exact lattice-point square, rectangle, rhombus, and parallelogram cases. Rectangle and rhombus branches avoid square ambiguity, and the parallelogram branch avoids rectangle/rhombus/square distractors so the selected candidate is unique.

## Evidence
Verifier evidence is one final-image pixel point at the center of the selected candidate marker. Graph coordinates, candidate classifications, and the hidden missing point are recorded only in trace metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Query IDs, candidate labels, marker styles/colors, graph frame, prompt bundle IDs, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Prompt bundle: `prompts/geometry/coordinate/geometry_coordinate_quadrilateral_v0.json`
- Task module: `trace/tasks/geometry/coordinate/quadrilateral.py`

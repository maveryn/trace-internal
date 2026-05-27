# `task_geometry__coordinate_plane__missing_endpoint_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public query id: `default`
5. Query id: `missing_endpoint_from_midpoint` or `missing_startpoint_from_midpoint`
6. Answer type: `option_letter`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_coordinate_algebra_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the lettered candidate point that completes segment `PQ` when one endpoint and midpoint `M` are plotted on a coordinate grid.

The rendered diagram draws the known half-segment from the visible endpoint to `M` and includes a small midpoint cue. The verifier computes the hidden endpoint from the midpoint relation, using `Q = 2M - P` or `P = 2M - Q`. Distractor points are unique lattice points and do not share the target coordinate.

## Evidence
Verifier evidence is the final-image pixel bounding box around the selected candidate point. Graph coordinates, midpoint formula, candidate points, and target endpoint are recorded in trace metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Query IDs, candidate labels, marker styles/colors, graph frame, prompt bundle IDs, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Prompt bundle: `prompts/geometry/coordinate/geometry_coordinate_algebra_v0.json`
- Task module: `trace/tasks/geometry/coordinate/algebra.py`

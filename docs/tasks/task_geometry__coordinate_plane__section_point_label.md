# `task_geometry__coordinate_plane__section_point_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public query id: `default`
5. Query id: `one_third_from_p_to_q` or `two_thirds_from_p_to_q`
6. Answer type: `option_letter`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_coordinate_algebra_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the lettered candidate point at a one-third or two-thirds section of segment `PQ`, starting from `P` toward `Q`.

The verifier computes the target point from the section formula `P + k/3 * (Q - P)`, where `k` is `1` or `2`. Sampled endpoints make the section point an integer lattice point, and exactly one candidate has the target coordinate.

## Evidence
Verifier evidence is the final-image pixel bounding box around the selected candidate point. Graph coordinates, section ratio, candidate points, and target point are recorded in trace metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Query IDs, candidate labels, marker styles/colors, graph frame, prompt bundle IDs, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Prompt bundle: `prompts/geometry/coordinate/geometry_coordinate_algebra_v0.json`
- Task module: `trace/tasks/geometry/coordinate/algebra.py`

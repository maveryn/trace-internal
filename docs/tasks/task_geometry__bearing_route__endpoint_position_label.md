# `task_geometry__bearing_route__endpoint_position_label`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `bearing_route`
4. Query id: `endpoint_position_label`
5. Answer type: `option_letter`
6. Evidence type: `keyed_point_map`

## Prompt Bundle
- Bundle id: `geometry_bearing_route_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Select the labeled endpoint reached by following two visible compass-bearing
instructions from the start point. Bearings are shown in the diagram as
degrees clockwise from north. Candidate endpoint labels are sampled from the
safe global uppercase label pool and drawn directly in the image.

## Evidence
Prompt-facing evidence is a `keyed_point_map` grounding the `start_point` and
`reached_endpoint` marker centers. The route instruction panel and endpoint
label boxes remain visible input annotations plus render metadata, not public
evidence. Verifier evidence is projected from the same pixel geometry used to
render the scene and compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Sampling axes, prompt bundle ids, selected visual style, font
family, candidate labels, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Prompt bundle: `prompts/geometry/measurement/geometry_bearing_route_v0.json`
- Task module: `trace/tasks/geometry/measurement/bearing_route.py`

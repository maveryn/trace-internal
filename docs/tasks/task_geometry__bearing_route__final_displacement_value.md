# `task_geometry__bearing_route__final_displacement_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `bearing_route`
4. Query id: `final_displacement_value`
5. Answer type: `number`
6. Evidence type: `keyed_point_map`

## Prompt Bundle
- Bundle id: `geometry_bearing_route_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Compute the direct displacement from start to finish after following two
compass-bearing route legs. Bearings are shown in the diagram as degrees
clockwise from north. Route cases are sampled from integer right-triangle
supports so the final displacement is a unique integer.

## Evidence
Prompt-facing evidence is a `keyed_point_map` grounding the `start_point`,
`turn_point`, and `finish_point` route vertices. The compass rose, bearing
note, route-leg annotations, and dashed displacement cue remain visible
annotations plus render metadata, not public evidence. Verifier evidence is
projected from the same pixel geometry used to render the scene and compute
the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Sampling axes, prompt bundle ids, selected visual style, font
family, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Prompt bundle: `prompts/geometry/measurement/geometry_bearing_route_v0.json`
- Task module: `trace/tasks/geometry/measurement/bearing_route.py`

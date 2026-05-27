# `task_geometry__graph_paper__line_slope_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `graph_paper`
4. Public query variant: `default`
5. Query id: `slope`
6. Answer type: `number`
7. Evidence type: `point_set`

## Prompt Bundle
- Bundle id: `geometry_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Read the slope of a plotted line.

The public task uses the shared geometry `measurement` implementation. The concrete query branch is recorded in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/value.py`

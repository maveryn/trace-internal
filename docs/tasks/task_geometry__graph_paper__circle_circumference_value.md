# `task_geometry__graph_paper__circle_circumference_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `graph_paper`
4. Public query id: `default`
5. Query id: `perimeter`
6. Answer type: `pi_expression`
7. Evidence type: `point_set`

## Prompt Bundle
- Bundle id: `geometry_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Compute a circle circumference in kπ form.

The public task uses the shared geometry `measurement` implementation. The concrete query branch is recorded in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/value.py`

# `task_geometry__circle_theorem__tangent_chord_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `circle`
3. Scene id: `circle_theorem`
4. Public query id: `default`
5. Query ids: `tangent_chord_angle_from_arc`, `tangent_chord_angle_from_inscribed`
6. Answer type: `integer`
7. Evidence type: `keyed_point_map`

## Prompt Bundle
- Bundle id: `geometry_circle_theorem_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Solve a missing tangent-chord angle using either the intercepted arc measure or the matching inscribed angle in the alternate segment.

The public task is a narrowed wrapper around the shared geometry `circle` implementation. The selected query name is retained only in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Prompt-facing evidence is a `keyed_point_map`: a JSON object mapping the visible construction point labels that define the tangent-chord angle and its matching arc or inscribed angle to their pixel points. Visible angle and arc measurement labels remain annotations and render metadata, not public evidence. Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/circle.yaml`
- Task module: `trace/tasks/geometry/circle/theorem_value.py`

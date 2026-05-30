# `task_geometry__circle_theorem__secant_secant_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `circle`
3. Scene id: `circle_theorem`
4. Public query id: `default`
5. Query id: `secant_secant_length` or `secant_secant_variable_segment_length`
6. Answer type: `integer`
7. Evidence type: `keyed_point_map`

## Prompt Bundle
- Bundle id: `geometry_circle_theorem_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Solve a missing length in a secant-secant diagram, including numeric and variable-segment forms.

The public task wraps two equivalent secant-secant theorem queries. The selected query is retained only in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Prompt-facing evidence is a `keyed_point_map`: a JSON object mapping the visible construction point labels that define the two secants and queried segment to their pixel points. Visible measurement labels remain annotations and render metadata, not public evidence. Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/circle.yaml`
- Task module: `trace/tasks/geometry/circle/theorem_value.py`

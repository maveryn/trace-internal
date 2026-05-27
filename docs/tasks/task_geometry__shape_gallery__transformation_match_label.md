# `task_geometry__shape_gallery__transformation_match_label`

## Contract
1. Domain: `geometry`
2. Task group: `transformation`
3. Scene id: `shape_gallery`
4. Public query id: `default`
5. Query id: `translation_match`, `reflection_match`, or `rotation_match`
6. Answer type: `option_letter`
7. Evidence type: `point_set`

## Prompt Bundle
- Bundle id: `geometry_transformation_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the candidate polygon matching the requested transformation of the reference polygon.

The public task wraps translation, reflection, and rotation candidate-match queries over the same reference/candidate gallery. The selected query is retained only in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/transformation.yaml`
- Task module: `trace/tasks/geometry/transformation/match.py`

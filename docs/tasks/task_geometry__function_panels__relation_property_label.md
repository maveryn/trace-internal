# `task_geometry__function_panels__relation_property_label`

## Contract
1. Domain: `geometry`
2. Task group: `analytical`
3. Scene id: `function_panels`
4. Public query variant: `default`
5. Query id: `function_status_label` or `one_to_one_status_label`
6. Answer type: `option_letter`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_function_property_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the panel matching the requested function property.

The public task wraps function-status and one-to-one property queries over the same six-panel function grid. The selected query is retained only in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/analytical.yaml`
- Task module: `trace/tasks/geometry/analytical/function_property_label.py`

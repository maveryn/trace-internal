# `task_geometry__function_graph__average_rate_value`

## Contract
1. Domain: `geometry`
2. Task group: `graphing`
3. Scene id: `function_graph`
4. Public query id: `default`
5. Query id: `average_rate_between_marked_points`
6. Answer type: `number`
7. Evidence type: `point_set`

## Prompt Bundle
- Bundle id: `geometry_graphing_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Compute the average rate of change between two marked points on a plotted function graph.

The answer is the secant slope `(y_B - y_A) / (x_B - x_A)`, rounded to one decimal place.

## Evidence
Verifier evidence is the pixel point set for the marked endpoints A and B, projected from graph metadata. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/graphing.yaml`
- Task module: `trace/tasks/geometry/graphing/rate.py`

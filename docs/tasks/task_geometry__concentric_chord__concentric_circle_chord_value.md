# `task_geometry__concentric_chord__concentric_circle_chord_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `concentric_chord`
4. Public query id: `default`
5. Query id: `chord_length_from_radii` or `inner_radius_from_chord`
6. Answer type: `number`
7. Evidence type: `keyed_point_map`

## Prompt Bundle
- Bundle id: `geometry_concentric_circle_chord_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Compute either the chord length or the inner radius in a diagram with two
concentric circles where a chord of the outer circle is tangent to the inner
circle. The verifier uses `R^2 = r^2 + (c/2)^2`; answers are rounded to one
decimal place.

## Evidence
Prompt-facing evidence is a `keyed_point_map` over the visible construction
points `O`, `A`, `B`, and `T`, where `O` is the shared center, `A` and `B` are
the chord endpoints, and `T` is the tangency point. Radius and chord-length
labels remain visible annotations and render metadata, not public evidence.
Verifier evidence is projected from the same generated scene metadata used to
compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Sampling axes, query ids, prompt bundle ids, and render choices
must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/concentric_circle_chord.py`

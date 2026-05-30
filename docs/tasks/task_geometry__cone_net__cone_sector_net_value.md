# `task_geometry__cone_net__cone_sector_net_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `cone_net`
4. Public query id: `default`
5. Query id: `base_radius_from_sector_angle` or `height_from_sector_angle`
6. Answer type: `number`
7. Evidence type: `keyed_point_map`

## Prompt Bundle
- Bundle id: `geometry_cone_sector_net_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Compute either the base radius or the height of a cone formed from a circular
sector net. The sector radius is the cone slant height, and the sector arc
becomes the cone base circumference. Height queries first derive the base
radius, then use the right-triangle relation between height, radius, and slant
height. Answers are numeric and rounded to one decimal place.

## Evidence
Prompt-facing evidence is a `keyed_point_map` over labeled construction
points. Both queries use the sector points `S`, `P`, and `Q` plus cone base
center `C`; base-radius queries add cone base-right point `R`, while height
queries add cone apex point `A`. Slant-height, sector-angle, and target labels
remain visible annotations and render metadata, not public evidence. Verifier
evidence is projected from the same generated scene metadata used to compute
the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Sampling axes, query ids, prompt bundle ids, and render choices
must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/cone_sector_net.py`

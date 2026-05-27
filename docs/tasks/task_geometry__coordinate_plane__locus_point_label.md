# `task_geometry__coordinate_plane__locus_point_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public query variant: `default`
5. Query id: `circle_region_point`, `annulus_region_point`, `vertical_strip_region_point`, or `half_plane_intersection_region_point`
6. Answer type: `option_letter`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_coordinate_locus_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the single lettered candidate point that lies in the shaded coordinate
locus region.

The scene draws one coordinate grid with a shaded circle, annulus, vertical
strip, or intersection of two half-planes. Candidate points are unique lattice
points. Exactly one candidate satisfies the region membership predicate, and
all candidate graph coordinates and memberships are retained in metadata.

## Evidence
Verifier evidence is the final-image pixel bounding box around the selected
candidate point. The shaded region specification and candidate membership
trace are metadata-backed.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Query IDs, candidate labels, marker styles/colors, graph
frame, prompt bundle IDs, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Prompt bundle: `prompts/geometry/coordinate/geometry_coordinate_locus_v0.json`
- Task module: `trace/tasks/geometry/coordinate/locus_region.py`

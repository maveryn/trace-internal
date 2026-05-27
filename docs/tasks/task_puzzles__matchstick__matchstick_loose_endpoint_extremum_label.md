# `task_puzzles__matchstick__matchstick_loose_endpoint_extremum_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `matchstick`
3. Task group: `logic`
4. Query ids: `most_loose_endpoints`, `fewest_loose_endpoints`
5. Objective: choose the labeled stick arrangement with the unique largest or smallest loose-endpoint count.

## Answer And Evidence
1. Answer type: `option_letter`
2. Evidence type: `bbox_set`
3. User-facing evidence contains the selected option-panel bbox.
4. The trace records each option edge set, each option loose-endpoint count, the selected extremum query, and grid size.

## Rendering
The shared `matchstick` renderer supports wooden matches, colored rods, chalk sticks, neon rods, and metal rods. Each instance shows six labeled arrangements with no Source panel.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, renderer/config versions, and recorded query/scene variants.

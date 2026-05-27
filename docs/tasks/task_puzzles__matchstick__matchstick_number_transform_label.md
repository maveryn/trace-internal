# `task_puzzles__matchstick__matchstick_number_transform_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `matchstick`
3. Task group: `logic`
4. Query ids: `add_one_stick`, `remove_one_stick`
5. Objective: choose the labeled candidate number reachable from the Source number by adding or removing exactly one matchstick.

## Answer And Evidence
1. Answer type: `option_letter`
2. Evidence type: `bbox_set`
3. User-facing evidence contains the selected option-panel bbox.
4. The trace records the Source number, selected answer number, changed digit index, added/removed segment keys, and reachability status for every option.

## Rendering
The shared `matchstick` renderer supports wooden matches, colored rods, chalk sticks, neon rods, and metal rods. The Source and six labeled options are rendered as two-digit matchstick numbers.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, renderer/config versions, and recorded query/scene variants.

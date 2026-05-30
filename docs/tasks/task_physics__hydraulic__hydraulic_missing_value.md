# `task_physics__hydraulic__hydraulic_missing_value`

## Summary
- Domain: `physics`
- Scene id: `hydraulic`
- Task group: `fluids`
- Task id: `task_physics__hydraulic__hydraulic_missing_value`
- Query id: `missing_output_force|missing_input_force|missing_piston_area`
- Answer type: `integer`
- Evidence type: `keyed_bbox_map`

## Visual Scaffold
- The image shows one connected three-piston hydraulic system.
- The setup includes:
  - an input fluid chamber with a piston,
  - a middle reference fluid chamber with a piston,
  - an output fluid chamber with a piston,
  - a connecting fluid pipe,
  - piston area labels,
  - downward force arrows,
  - one red `?` label on the missing force or output-area quantity.
- Active `scene_variant` values:
  - `wide_bench`
  - `compact_frame`
  - `tall_columns`

## Query IDs
- `missing_output_force`
  - input force, the middle reference piston, and all piston areas are shown; the output force is marked `?`
- `missing_input_force`
  - output force, the middle reference piston, and all piston areas are shown; the input force is marked `?`
- `missing_piston_area`
  - input force, output force, the middle reference piston, and input area are shown; the output piston area is marked `?`
- Outputs put the concrete branch in `query_id`.

## Reasoning Contract
- The hydraulic system is ideal and uses Pascal's law across all connected pistons:
  `F_input / A_input = F_middle / A_middle = F_output / A_output`.
- The generator constructs integer-valued scenes from an integer mechanical-advantage ratio: `A_output = A_input * mechanical_advantage` and `F_output = F_input * mechanical_advantage`.
- The middle reference piston is also an integer-ratio piston at the same pressure, and its ratio is different from the output ratio when a compatible value exists.
- The final answer is unique by construction for each query branch.

## Evidence Contract
- Prompt-facing evidence is a `keyed_bbox_map` over only the known force/area labels needed to compute the missing value.
- `missing_output_force` uses keys `input_force`, `input_area`, and `output_area`.
- `missing_input_force` uses keys `output_force`, `input_area`, and `output_area`.
- `missing_piston_area` uses keys `input_force`, `output_force`, and `input_area`.
- The red `?` target label and middle reference labels remain visible cues but are not prompt-facing evidence for the current query branches.

## Sampling Notes
- Input-force support is `4..12`.
- Input-area support is `2..9`.
- Mechanical-advantage support is `3..8`, excluding trivial doubling cases in the calibrated public mix.
- Output-force and output-area answer supports are filtered to constructively feasible integer products.
- Under the seeded task sampler, scene, query, and answer-support cycles are decoupled so the scene/query cross-product is covered.

## Prompt Policy
- Prompt text should identify the system as a connected three-piston hydraulic piston diagram.
- Prompt text should ask only for an integer force or area value.
- Prompt-facing evidence should stay on the minimal known force and area labels, keyed by semantic role.

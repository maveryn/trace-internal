# `task_physics_mechanics_spring_extension`

## Summary
- Domain: `physics`
- Task group: `mechanics`
- Task id: `task_physics_mechanics_spring_extension`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Visual scaffold
- The image shows two identical vertical springs in separate cards.
- Each card includes:
  - a top support bar,
  - one spring,
  - one ruler marked in extension units,
  - one weight block that is either shown directly or replaced by a red `?`.
- Active `scene_variant` values:
  - `paired_springs`
  - `staggered_springs`
  - `textured_spring`

## Query variants
- `missing_weight_for_extension`
  - one spring provides a known weight/extension reference
  - the right spring shows its extension but the weight block is a red `?`
  - answer: missing integer weight
- `missing_extension_for_weight`
  - one spring provides a known weight/extension reference
  - the right spring shows the weight value, while a red `?` tag marks an unknown extension on the ruler
  - answer: missing integer extension
- `extension_difference`
  - both springs show their extensions
  - answer: absolute difference between the two shown extension values

## Reasoning contract
- Springs are identical within each instance.
- Hooke-style proportionality is constructed directly in the trace: `extension = scale_factor * weight`.
- The visible left measurement gives the reference pair.
- The right measurement changes either the weight or the extension depending on `task_variant`.
- All sampled values are integers by construction.

## Evidence contract
- `missing_weight_for_extension`
  - prompt-facing evidence is the unordered set of:
    - reference weight block,
    - reference extension marker,
    - marked red `?` weight block,
    - queried extension marker
- `missing_extension_for_weight`
  - prompt-facing evidence is the unordered set of:
    - reference weight block,
    - reference extension marker,
    - shown query weight block,
    - marked red `?` extension tag
- `extension_difference`
  - prompt-facing evidence is the unordered set of the two shown extension markers

## Sampling notes
- Scale factors come from a small integer support, currently `1..3`.
- Weight values stay within a compact integer range, currently `1..9`.
- Extension values stay within the visible ruler range, currently `1..12`.
- The task balances answer support per query variant rather than exposing a single fixed support for all variants.

## Prompt policy
- Prompt text should say that the springs are identical.
- Prompt text should ask only for integer weight / extension / difference values.
- Prompt-facing evidence should stay on weight blocks and ruler markers, not on card chrome or the support bars.

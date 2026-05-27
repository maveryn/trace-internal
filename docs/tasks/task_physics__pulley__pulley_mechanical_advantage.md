# `task_physics__pulley__pulley_mechanical_advantage`

## Summary
- Domain: `physics`
- Scene id: `pulley`
- Task group: `mechanics`
- Task id: `task_physics__pulley__pulley_mechanical_advantage`
- Query id: `force_relation`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Visual scaffold
- The image shows one ideal block-and-tackle pulley setup.
- The setup includes:
  - a fixed upper pulley block,
  - a moving lower pulley block,
  - full vertical rope strands connecting the upper and lower blocks,
  - optional cut non-supporting strands attached to either the upper or lower block but not both,
  - a load block,
  - an effort-force arrow.
- Active `scene_variant` values:
  - `open_block`
  - `compact_block`
  - `tall_block`
    - the variants adjust the vertical spacing between blocks.

## Query IDs
- `force_relation`
  - `solve_for=effort_force`: the load force is shown and the effort force is marked `?`
  - `solve_for=load_force`: the effort force is shown and the load force is marked `?`
  - outputs `query_id="force_relation"`

## Reasoning contract
- The pulley system is ideal, with no friction.
- Mechanical advantage equals the number of full vertical rope strands that connect the fixed upper block to the moving lower block.
- Cut strands are visual distractors and do not contribute to mechanical advantage.
- The trace constructs integer force values using `load_force = effort_force * support_segment_count`.
- The final answer is unique by construction for each solve target.

## Evidence contract
- `force_relation` with `solve_for=effort_force`
  - prompt-facing evidence is the unordered set of:
    - all full supporting vertical rope-strand bboxes,
    - the shown load-force label bbox,
    - the marked `?` effort-force label/arrow bbox
- `force_relation` with `solve_for=load_force`
  - prompt-facing evidence is the unordered set of:
    - all full supporting vertical rope-strand bboxes,
    - the shown effort-force label/arrow bbox,
    - the marked `?` load-force label bbox

## Sampling notes
- Each sample draws one system.
- Full connected supporting-strand counts use the support `2..6`.
- Cut non-supporting strand counts use the support `0..4`.
- Connected and cut-strand counts are sampled independently; review sampling does not force a joint connected/cut grid.
- Missing effort-force answers use the support `4..18`.
- Missing load-force answers use feasible products from `support_segment_count in 2..6` and `effort_force in 4..18`.
- Under the seeded task sampler, scene, solve target, and answer-support cycles are decoupled so equal-size axes cover the scene/solve-target cross-product and do not alias one subfamily's answer support.

## Prompt policy
- Prompt text should identify the setup as one ideal pulley system.
- Prompt text should ask only for an integer force value.
- Prompt-facing evidence should stay on full supporting rope strands and the relevant load/effort labels, not cut strands or decorative frame elements.

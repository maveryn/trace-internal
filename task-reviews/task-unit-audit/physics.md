# Physics Task-Unit Audit

Task-unit audit for `domain=physics` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The physics domain is promising and visually grounded, but it is also the clearest example of young tasks being a bit over-consolidated.
2. All five current tasks are diagram-first and image-dependent, so none should be retired.
3. The main pressure point is that several tasks combine:
   - a full-diagram quantity question, and
   - a marked-placeholder / missing-value question
   inside one task id, which creates noticeably different witness semantics under uniform task sampling.
4. Recommended domain outcome:
   - `Keep`: `3`
   - `Split`: `2`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_physics_circuits_equivalent_resistance`
- Outcome: `Split`
- Why: this task currently mixes two different resistor-network grounding families:
  - full-network equivalent-resistance reasoning (`total_resistance`)
  - marked missing-resistor inference in a paired-circuit equality scene (`missing_resistor_value`)
- Scene variety: high, but mixed rather than uniformly broad.
- Query variety: moderate, but the query variants use different visual scaffolds:
  - one single circuit between `A` and `B`,
  - two side-by-side circuits with a red `?` resistor and an equality cue.
- Grounding necessity: strong in both halves, but the operative witness differs:
  - all resistor boxes in the asked network,
  - one marked missing resistor in a paired-comparison scene.
- Evidence fit: mixed; the task switches from full-network resistor evidence to one-box placeholder evidence inside one task id.
- Follow-up:
  1. Keep `total_resistance` as one equivalent-network task.
  2. Move `missing_resistor_value` into a separate missing-component circuits task.

### `task_physics_mechanics_force_diagram`
- Outcome: `Keep`
- Why: despite differing evidence scope, this still reads as one coherent axis-aligned force-diagram family over the same block-and-arrows scaffold.
- Scene variety: moderate (`free_body_box|textured_block`) within one stable diagram grammar.
- Query variety: moderate (`net_horizontal_force|net_vertical_force|balancing_force_horizontal|balancing_force_vertical`) but still one consistent force-addition / force-balancing family.
- Grounding necessity: strong; the solver must read the shown force arrows and their directions/magnitudes.
- Evidence fit: acceptable; queried-axis arrows vs the marked `?` arrow differ slightly, but both are still local witnesses on the same force diagram.
- Follow-up: if mechanics grows substantially later, `net_force` vs `balancing_force` could become a useful split, but it does not feel necessary now.

### `task_physics_mechanics_lever_balance`
- Outcome: `Keep`
- Why: one coherent lever-arithmetic family over the same beam/fulcrum/weight scaffold.
- Scene variety: moderate (`center_fulcrum|offset_fulcrum|textured_beam`) within one stable lever diagram grammar.
- Query variety: moderate (`left_torque|right_torque|missing_weight_to_balance`) but still one consistent torque/balance family.
- Grounding necessity: strong; the model must read weight values, distances, and sides of the fulcrum.
- Evidence fit: acceptable; queried-side weights vs the marked `?` weight differ somewhat, but both remain stable lever-local witnesses.
- Follow-up: none required now.

### `task_physics_mechanics_spring_extension`
- Outcome: `Keep`
- Why: one coherent paired-springs proportionality family.
- Scene variety: moderate (`paired_springs|staggered_springs|textured_spring`) under one stable two-card scaffold.
- Query variety: moderate (`missing_weight_for_extension|missing_extension_for_weight|extension_difference`) but still one consistent “infer a quantity from the paired spring relation” family.
- Grounding necessity: strong; the solver must read both visible spring cards, rulers, and blocks.
- Evidence fit: acceptable; the witness set changes across missing-value vs difference variants, but all evidence stays on weight blocks and extension markers within the same paired-springs scene.
- Follow-up: none required now.

### `task_physics_optics_ray_trace`
- Outcome: `Split`
- Why: this task currently mixes two different hidden-ray families:
  - bounce-point counting (`bounce_count`)
  - target-hit counting (`target_hit_count`)
- Scene variety: high, but too mixed for one task unit.
- Query variety: moderate, but the scene contents and witnesses differ materially:
  - `bounce_count` scenes emphasize mirrors only,
  - `target_hit_count` scenes add target dots and ask about target hits instead of reflections.
- Grounding necessity: strong in both halves, but the solver is tracking different witness objects.
- Evidence fit: mixed; the task switches from bounce-point evidence to hit-target evidence inside one id.
- Follow-up:
  1. Keep `bounce_count` as one mirror-bounce task.
  2. Keep `target_hit_count` as one target-hit ray-tracing task.

## Recommended next action
1. Leave the three mechanics tasks unchanged for now.
2. Treat `task_physics_circuits_equivalent_resistance` and `task_physics_optics_ray_trace` as the first concrete physics split candidates during benchmark-unit rebalancing.
3. If physics expands later, use this domain as a reminder to separate full-diagram quantity questions from marked-placeholder inference tasks when they begin to diverge visually.

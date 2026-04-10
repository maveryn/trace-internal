# Physics Task Setup

Use this document for the active `physics` domain contract.

For cross-domain coverage rollups, use `docs/project/STATUS.md` and `docs/domains/TASK_FAMILY_VARIANTS.md` instead of repeating those inventories here.

## 1) Domain scope
1. `physics` should stay diagram-first: the image must contain the operative quantities and spatial grounding needed to solve the task.
2. Early physics tasks should use light arithmetic (`+`, `-`, small products) rather than formula-heavy derivations.
3. Prompt-facing evidence should stay on the visible witness objects in the diagram (for example force arrows, weights, resistors, or ray targets), not on decorative scene chrome.

## 2) Active families
### `mechanics`
1. Active tasks:
   - `task_physics_mechanics_force_diagram`
   - `task_physics_mechanics_lever_balance`
   - `task_physics_mechanics_spring_extension`
2. `task_physics_mechanics_force_diagram` scene/query surface:
   - `scene_variant`: `free_body_box|textured_block`
   - `query_variant`: `net_horizontal_force|net_vertical_force|balancing_force_horizontal|balancing_force_vertical`
3. `task_physics_mechanics_force_diagram` evidence contract:
   - unordered `bbox_set` over the shown queried-axis arrows for `net_*`
   - one-box `bbox_set` over the marked `?` arrow for `balancing_force_*`
4. `task_physics_mechanics_force_diagram` prompt policy:
   - ask for force magnitudes only (no signed-force convention),
   - balancing variants must mention the marked direction explicitly,
   - balancing placeholders should stay aligned to the shown-arrow lane system as one more arrow on the queried side of the block,
   - answers remain plain integers in newtons.
5. `task_physics_mechanics_lever_balance` scene/query surface:
   - `scene_variant`: `center_fulcrum|offset_fulcrum|textured_beam`
   - `query_variant`: `left_torque|right_torque|missing_weight_to_balance`
6. `task_physics_mechanics_lever_balance` evidence contract:
   - unordered `bbox_set` over the weight blocks on the queried side for `left_torque|right_torque`
   - one-box `bbox_set` over the marked `?` weight block for `missing_weight_to_balance`
7. `task_physics_mechanics_lever_balance` prompt policy:
   - ask for torque or missing-weight magnitudes only,
   - keep all needed distances visible on the beam,
   - keep prompt-facing evidence on the weight blocks rather than the beam or fulcrum,
   - allow non-semantic accent-color variation on the beam / fulcrum / shown weights, but keep the marked `?` weight visibly red.
8. `task_physics_mechanics_spring_extension` scene/query surface:
   - `scene_variant`: `paired_springs|staggered_springs|textured_spring`
   - `query_variant`: `missing_weight_for_extension|missing_extension_for_weight|extension_difference`
9. `task_physics_mechanics_spring_extension` evidence contract:
   - unordered `bbox_set` over the reference weight + reference extension marker + query-side missing weight / shown weight + query-side extension marker / red `?` extension tag for the two missing-value variants
   - unordered `bbox_set` over the two shown extension markers for `extension_difference`
10. `task_physics_mechanics_spring_extension` prompt policy:
   - say explicitly that the two springs are identical,
   - keep the arithmetic grounded in the shown weight/extension pairs rather than in an explicit formula label,
   - keep prompt-facing evidence on the weight blocks and ruler markers,
   - allow non-semantic accent-color variation on the card chrome / supports / springs while keeping missing-value markers visibly red.
### `circuits`
1. Active tasks:
   - `task_physics_circuits_equivalent_resistance`
2. `task_physics_circuits_equivalent_resistance` scene/query surface:
   - `scene_variant`: `parallel|simple_series_parallel`
   - `query_variant`: `total_resistance|missing_resistor_value`
3. `task_physics_circuits_equivalent_resistance` evidence contract:
   - unordered resistor-box `bbox_set` over the asked network for `total_resistance`
   - one-box `bbox_set` over the marked red `?` resistor for `missing_resistor_value`
4. `task_physics_circuits_equivalent_resistance` prompt policy:
   - ask explicitly for equivalent resistance between labeled terminals `A` and `B`,
   - keep resistor labels as plain integers in the boxes and leave units to the prompt text,
   - keep prompt-facing evidence on the resistor boxes rather than on the wires,
   - require every active scene to contain a real parallel section rather than a pure series chain,
   - when `scene_variant` is not fixed for `total_resistance`, resolve the target resistance from the query-level feasible union support first and then choose a compatible scene family for that target so the per-variant answer distribution remains healthy,
   - filter configured answer supports down to the constructively feasible subset for the chosen scene/query family before balanced sampling,
   - for `missing_resistor_value`, use two side-by-side circuits with an equality cue and keep the missing resistor visibly red in the left circuit.
### `optics`
1. Active tasks:
   - `task_physics_optics_ray_trace`
2. `task_physics_optics_ray_trace` scene/query surface:
   - `scene_variant`: `single_mirror|double_mirror|triple_mirror|quad_mirror`
   - `query_variant`: `bounce_count|target_hit_count`
3. `task_physics_optics_ray_trace` evidence contract:
   - unordered `graph_point_set` over the bounce points for `bounce_count`
   - unordered `graph_point_set` over the hit target points for `target_hit_count`
4. `task_physics_optics_ray_trace` prompt policy:
   - ask the user to infer the hidden ray path from the shown initial direction plus the mirrors,
   - keep only the initial ray direction visible in the prompt image and keep the solved path in trace/debug artifacts,
   - keep prompt-facing evidence on graph points rather than on mirror/target bboxes,
   - use large unlabeled target points for `target_hit_count` and no separate bounce circles for `bounce_count`,
   - reserve `single_mirror|double_mirror|triple_mirror` for `target_hit_count`, while `bounce_count` uses `quad_mirror` so that variant keeps a broad, well-balanced answer support.

## 3) V1 physics-domain policy
1. Prefer one stable diagram scaffold per task id; widen scene/query variety inside that task before adding more ids.
2. Keep arithmetic grounded in the visible diagram: if a quantity is not shown or clearly implied by the diagram, do not require it in the first physics tasks.
3. Early mechanics tasks should keep vectors axis-aligned unless the task is explicitly about angled-force decomposition.
4. Prefer integer-valued constructions so answer verification stays exact and prompt-facing evidence remains local.

## 4) Shared helper placement
1. Cross-domain scene/query compatibility sampling now lives in `trace/tasks/shared/variant_sampling.py`.
2. Physics-domain visual defaults belong in `trace/tasks/physics/shared/visual_defaults.py`.
3. Physics-domain normalized complexity helpers belong in `trace/tasks/physics/shared/complexity.py`.
4. Physics-domain named accent themes belong in `trace/tasks/physics/shared/style.py`.
5. Physics-domain resistor-network rendering helpers belong in `trace/tasks/physics/shared/circuit_scene.py`.
6. Physics-domain optics-board rendering helpers belong in `trace/tasks/physics/shared/optics_scene.py`.
7. Spring-extension rendering is currently task-local in `trace/tasks/physics/mechanics/spring_extension.py`; only the reusable physics theme / complexity / support helpers live under `trace/tasks/physics/shared/*`.

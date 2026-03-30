# Physics Task Setup

Use this document for the active `physics` domain contract.

## 1) Domain scope
1. `physics` should stay diagram-first: the image must contain the operative quantities and spatial grounding needed to solve the task.
2. Early physics tasks should use light arithmetic (`+`, `-`, small products) rather than formula-heavy derivations.
3. Prompt-facing evidence should stay on the visible witness objects in the diagram (for example force arrows, weights, resistors, or ray targets), not on decorative scene chrome.

## 2) Active family
### `mechanics`
1. Active task: `task_physics_mechanics_force_diagram`
2. Current scene/query surface:
   - `scene_variant`: `free_body_box|surface_block|textured_block`
   - `query_variant`: `net_horizontal_force|net_vertical_force|balancing_force_horizontal|balancing_force_vertical`
3. Evidence contract:
   - unordered `bbox_set` over the shown queried-axis arrows for `net_*`
   - one-box `bbox_set` over the marked `? N` arrow for `balancing_force_*`
4. Prompt policy:
   - ask for force magnitudes only (no signed-force convention),
   - balancing variants must mention the marked direction explicitly,
   - balancing placeholders should stay aligned to the shown-arrow lane system and remain within the block-side span,
    - answers remain plain integers in newtons.

## 3) V1 physics-domain policy
1. Prefer one stable diagram scaffold per task id; widen scene/query variety inside that task before adding more ids.
2. Keep arithmetic grounded in the visible diagram: if a quantity is not shown or clearly implied by the diagram, do not require it in the first physics tasks.
3. Early mechanics tasks should keep vectors axis-aligned unless the task is explicitly about angled-force decomposition.
4. Prefer integer-valued constructions so answer verification stays exact and prompt-facing evidence remains local.

## 4) Good next physics families
1. `mechanics/lever_balance`
2. `circuits/equivalent_resistance`
3. `optics/ray_trace`
4. `mechanics/spring_extension`

## 5) Shared helper placement
1. Cross-domain scene/query compatibility sampling now lives in `trace/tasks/shared/variant_sampling.py`.
2. Physics-domain visual defaults belong in `trace/tasks/physics/shared/visual_defaults.py`.
3. Physics-domain normalized complexity helpers belong in `trace/tasks/physics/shared/complexity.py`.

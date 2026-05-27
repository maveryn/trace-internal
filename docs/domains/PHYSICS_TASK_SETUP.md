# Physics Task Setup

Use this document for the active `physics` domain contract.

For cross-domain coverage rollups, use `docs/project/STATUS.md` and `docs/domains/SCENE_TASK_QUERY_GUIDE.md` instead of repeating those inventories here.

## 1) Domain scope
1. `physics` should stay diagram-first: the image must contain the operative quantities and spatial grounding needed to solve the task.
2. Physics tasks should use visible, diagram-grounded arithmetic or formulas rather than hidden assumptions.
3. Prompt-facing evidence should stay on the visible witness objects in the diagram (for example force arrows, weights, resistors, or ray targets), not on decorative scene chrome.

## 2) Active families
### `mechanics`
1. Active tasks:
   - `task_physics__lever__side_torque_value`
   - `task_physics__lever__missing_weight_balance_value`
   - `task_physics__pulley__pulley_mechanical_advantage`
   - `task_physics__spring__spring_missing_value`
   - `task_physics__spring__spring_extension_difference`
   - `task_physics__collision__sticky_collision_direction_choice`
   - `task_physics__collision__sticky_collision_velocity_component_value`
2. Lever scene/query surface:
   - `scene_variant`: `center_fulcrum|offset_fulcrum|textured_beam`
   - public task ids: `task_physics__lever__side_torque_value`, `task_physics__lever__missing_weight_balance_value`
   - `query_id`: `side_torque|missing_weight_to_balance`
   - `torque_side`: `left|right` for `side_torque`
   - public missing-weight calibration uses `textured_beam`, answer support `1..6`, and at most two shown weights per side
3. Lever evidence contract:
   - unordered `bbox_set` over the weight blocks on the queried side for `side_torque`
   - one-box `bbox_set` over the marked `?` weight block for `missing_weight_to_balance`
4. Lever prompt policy:
   - ask for torque or missing-weight magnitudes only,
   - keep all needed distances visible on the beam,
   - keep prompt-facing evidence on the weight blocks rather than the beam or fulcrum,
   - allow non-semantic accent-color variation on the beam / fulcrum / shown weights, but keep the marked `?` weight visibly red.
5. `task_physics__pulley__pulley_mechanical_advantage` scene/query surface:
   - `scene_variant`: `open_block|compact_block|tall_block`
   - `query_id`: `force_relation`
   - `solve_for`: `effort_force|load_force`
6. `task_physics__pulley__pulley_mechanical_advantage` evidence contract:
   - unordered `bbox_set` over the full vertical strands connecting the fixed and moving blocks,
   - one-box `bbox_set` over the marked `?` force label.
7. `task_physics__pulley__pulley_mechanical_advantage` prompt policy:
   - ask for ideal pulley force magnitudes only,
   - say to use full connecting strands and ignore cut strands,
   - keep prompt-facing evidence on the supporting strands and marked force label.
8. Spring scene/query surface:
   - `scene_variant`: `paired_springs|staggered_springs|textured_spring`
   - public task ids: `task_physics__spring__spring_missing_value`, `task_physics__spring__spring_extension_difference`
   - `query_id`: `missing_value|extension_difference`
   - `solve_for`: `weight|extension` for `missing_value`
9. Spring evidence contract:
   - unordered `bbox_set` over the reference weight + reference extension marker + query-side missing weight / shown weight + query-side extension marker / red `?` extension tag for the two missing-value variants
   - unordered `bbox_set` over the two shown extension markers for `extension_difference`
10. Spring prompt policy:
   - say explicitly that the two springs are identical,
   - keep the arithmetic grounded in the shown weight/extension pairs rather than in an explicit formula label,
   - keep prompt-facing evidence on the weight blocks and value-labeled ruler markers,
   - allow non-semantic accent-color variation on the card chrome / supports / springs while keeping missing-value markers visibly red,
   - calibrate `extension_difference` with query-specific scale factor `2` and answer support `{2,4,8,10,12}` to avoid over-sampling small visual gaps.
11. Sticky-collision scene/query surface:
   - `scene_variant`: `wide_table|compact_table|gridded_table`
   - public task ids: `task_physics__collision__sticky_collision_direction_choice`, `task_physics__collision__sticky_collision_velocity_component_value`
   - `query_id`: `direction_choice|velocity_component`
   - `component_axis`: `x|y` for `velocity_component`
   - inputs are two perpendicular pucks with visible masses, speeds, and approach directions; the stuck pair shows the combined mass.
12. Sticky-collision evidence contract:
   - one-box `bbox_set` over the correct candidate arrow for `direction_choice`
   - one-box `bbox_set` over the queried component's puck, input velocity arrow, mass/speed labels, and the combined-mass label for `velocity_component`
13. Sticky-collision prompt policy:
   - ask for the candidate final direction or one signed integer velocity component only,
   - keep all momentum quantities visible in the diagram,
   - do not render the solved final arrow in the main scene; candidate arrows are proposed answers, not a revealed solution,
   - keep prompt-facing evidence on the decisive puck labels/arrows or the selected candidate arrow.
### `circuits`
1. Active tasks:
   - `task_physics__resistor__total_resistance_value`
   - `task_physics__paired_resistor__missing_resistor_value`
2. Circuit scene/task surface:
   - `scene_variant`: `parallel|simple_series_parallel`
   - `query_id`: `total_resistance|missing_resistor_value`
3. Circuit evidence contract:
   - unordered resistor-box `bbox_set` over the asked network for `total_resistance`
   - one-box `bbox_set` over the marked red `?` resistor for `missing_resistor_value`
4. Circuit prompt policy:
   - ask explicitly for equivalent resistance between labeled terminals `A` and `B`,
   - keep resistor labels as plain integers in the boxes and leave units to the prompt text,
   - keep prompt-facing evidence on the resistor boxes rather than on the wires,
   - require every active scene to contain a real parallel section rather than a pure series chain,
   - keep calibrated public total-resistance answers in `1..20` ohms,
   - for calibrated `total_resistance`, use one visible parallel block with optional series resistors,
   - when `scene_variant` is not fixed for `total_resistance`, resolve the target resistance from the query-id feasible union support first and then choose a compatible scene family for that target so the per-variant answer distribution remains healthy,
   - filter configured answer supports down to the constructively feasible subset for the chosen scene/query-id family before balanced sampling,
   - keep calibrated public `missing_resistor_value` answers in `{1, 3, 4, 5, 6, 8}`,
   - for `missing_resistor_value`, use two side-by-side circuits with an equality cue, show the common total resistance plus the known left-side resistance excluding `?`, and keep the missing resistor visibly red in the left circuit.
### `electrostatics`
1. Active tasks:
   - `task_physics__electrostatic_field__field_direction_choice`
   - `task_physics__electrostatic_field__zero_field_point_label`
   - `task_physics__electrostatic_field__potential_value`
2. Electrostatics field-map scene/query surface:
   - `scene_variant`: `clean_grid|paper_grid|dense_grid`
   - public task ids: `task_physics__electrostatic_field__field_direction_choice`, `task_physics__electrostatic_field__zero_field_point_label`, `task_physics__electrostatic_field__potential_value`
   - `query_id`: `field_direction_choice|zero_field_point_label|potential_value`
   - `direction_mode`: `electric_field_direction|force_on_positive_charge|force_on_negative_charge` for `field_direction_choice`
   - direction-choice scenes use fixed point charges, a marked point `P`, and eight candidate arrows; zero-field scenes use unequal same-sign charges and six labeled candidate points; potential scenes use three visible charge labels and `r` distance labels with `k=1`.
3. Electrostatics evidence contract:
   - one-box `bbox_set` over the correct candidate direction arrow for `field_direction_choice`
   - one-box `bbox_set` over the correct candidate point for `zero_field_point_label`
   - one-box `bbox_set` over the charge/point/distance witness region for `potential_value`
4. Electrostatics prompt policy:
   - ask for a single option letter or a signed integer potential only,
   - use query-specific scene descriptions so direction, zero-field, and potential prompts only mention the visible cues relevant to that query,
   - keep all field or potential quantities visible in the diagram,
   - keep force-on-negative-charge as an internal branch of the direction-choice task rather than a separate public task,
   - keep prompt-facing evidence on the selected arrow, selected point, or potential witness region rather than on axis chrome.
### `magnetism`
1. Active tasks:
   - `task_physics__magnetic_force__force_direction_choice`
2. Magnetism force-field scene/query surface:
   - `scene_variant`: `clean_panel|field_grid|lab_card`
   - public task id: `task_physics__magnetic_force__force_direction_choice`
   - `query_id`: `force_direction_choice`
   - `field_orientation`: `out_of_page|into_page`
   - `velocity_direction`, `charge_sign`, and candidate-arrow placement are internal axes for `force_direction_choice`.
   - public calibration uses `field_grid` with correct-answer letters `B|C|D|E|G|H`; all eight candidate arrows remain visible.
3. Magnetism evidence contract:
   - one-box `bbox_set` over the correct candidate force arrow for `force_direction_choice`
4. Magnetism prompt policy:
   - ask for a single option letter only,
   - keep the magnetic-field orientation, charge sign, and velocity vector visible in the diagram,
   - keep field orientation and sign/velocity changes as internal query axes rather than separate public tasks,
   - keep prompt-facing evidence on the selected candidate arrow rather than on decorative field-symbol chrome.
### `fluids`
1. Active tasks:
   - `task_physics__hydraulic__hydraulic_missing_value`
2. Hydraulic piston scene/query surface:
   - `scene_variant`: `wide_bench|compact_frame|tall_columns`
   - `query_id`: `missing_output_force|missing_input_force|missing_piston_area`
3. Hydraulic piston evidence contract:
   - unordered `bbox_set` over all six force and piston-area labels in the connected three-piston system,
   - the red `?` label is included as the missing quantity witness,
   - fluid chambers, pipe outlines, and decorative frame elements are not prompt-facing evidence.
4. Hydraulic piston prompt policy:
   - ask for integer force values in newtons or integer piston area in `cm^2`,
   - keep Pascal-law reasoning grounded in the shown input, middle-reference, and output force/area labels,
   - use calibrated mechanical-advantage ratios `3..8` so the public task avoids trivial doubling cases,
   - keep the missing label visibly red while allowing non-semantic accent-color variation on the chambers, fluid, and pistons.
### `optics`
1. Active tasks:
   - `task_physics__ray_optics__ray_bounce_count`
   - `task_physics__ray_optics__ray_target_hit_count`
2. Optics scene/query surface:
   - `scene_variant`: `single_mirror|double_mirror|triple_mirror|quad_mirror|five_mirror`
   - `query_id`: `bounce_count|target_hit_count`
3. Optics evidence contract:
   - unordered pixel `point_set` over the rendered bounce-point centers for `bounce_count`
   - unordered pixel `point_set` over the rendered hit target-point centers for `target_hit_count`
4. Optics prompt policy:
   - ask the user to infer the hidden ray path from the shown initial direction plus the mirrors,
   - keep only the initial ray direction visible in the prompt image and keep the solved path in trace/debug artifacts,
   - keep prompt-facing evidence on pixel points rather than on graph-coordinate labels or large mirror/target bboxes,
   - use large unlabeled target points for `target_hit_count` and no separate bounce circles for `bounce_count`,
   - calibrate `target_hit_count` on answers `1..5` with four or five target points,
   - reserve `single_mirror|double_mirror|triple_mirror` for `target_hit_count`, while `bounce_count` uses `five_mirror` with answers `1..5` so that the calibrated public mix avoids zero-bounce hard cases.
### `thermodynamics`
1. Active tasks:
   - `task_physics__pv_diagram__pv_work_value`
   - `task_physics__pv_diagram__pv_process_sign_choice`
2. PV diagram scene/query surface:
   - `scene_variant`: `clean_grid|paper_grid|bold_grid`
   - public task ids: `task_physics__pv_diagram__pv_work_value`, `task_physics__pv_diagram__pv_process_sign_choice`
   - `query_id`: `work_value|process_sign_choice`
   - calibrated `work_value` sampling uses `work_mode=single_process`; explicit rectangular-cycle construction remains a supported internal renderer path but is not in the default public calibration mix
   - `target_sign`: `positive|negative|zero` for `process_sign_choice`
3. PV diagram evidence contract:
   - one-box `bbox_set` over the highlighted PV process or cycle for `work_value`
   - one-box `bbox_set` over the correct labeled mini-process option for `process_sign_choice`
4. PV diagram prompt policy:
   - ask for signed integer work in joules or a single option letter only,
   - keep pressure in `kPa`, volume in `L`, and the `1 kPa*L = 1 J` conversion visible or prompt-explicit,
   - for numeric work, state the single-process formula `P * (V_final - V_initial)` and use rightward expansion as positive gas work and leftward compression as negative gas work,
   - keep prompt-facing evidence on the highlighted path or selected candidate process rather than on axis chrome.
### `waves`
1. Active tasks:
   - `task_physics__wave_interference__interference_point_choice`
   - `task_physics__wave_interference__path_difference_value`
2. Wave-interference scene/query surface:
   - `scene_variant`: `clean_tank|grid_tank|lab_sheet`
   - public task ids: `task_physics__wave_interference__interference_point_choice`, `task_physics__wave_interference__path_difference_value`
   - `query_id`: `interference_point_choice|path_difference_value`
   - `phase_relation`: `in_phase|opposite_phase`
   - `target_condition`: `constructive|destructive` for `interference_point_choice`
   - `interference_point_choice` uses five candidate points `A-E` in the calibrated public mix.
   - `path_difference_value` answers count absolute source-to-point path difference in `lambda/2` steps, calibrated on answers `1..4`.
3. Wave evidence contract:
   - one-box `bbox_set` over the correct candidate point for `interference_point_choice`
   - one-box `bbox_set` over both labeled source-to-`P` path guides and point `P` for `path_difference_value`
4. Wave prompt policy:
   - ask for a single option letter or integer `lambda/2` step count only,
   - keep source phase, crest/trough rings, source labels, and ring-spacing legend visible,
   - keep constructive/destructive condition and source phase as internal axes rather than separate public tasks,
   - keep prompt-facing evidence on the selected point or compact path-difference witness region rather than on decorative wavefront rings.

## 3) Physics-domain policy
1. Prefer one stable diagram scaffold per task id; widen scene/query variety inside that task before adding more ids.
2. Keep arithmetic grounded in the visible diagram: if a quantity is not shown or clearly implied by the diagram, do not require it.
3. Mechanics tasks should keep vectors axis-aligned unless the task is explicitly about angled-force decomposition.
4. Prefer integer-valued constructions so answer verification stays exact and prompt-facing evidence remains local.
5. Physics visual diversity should stay non-semantic: light background tints, named accent palettes, and the shared coordinate-preserving post-render noise policy are allowed, but layout jitter, coordinate/origin shifts, extra measurement grids, stroke thinning, stronger noise, or decorative patterns should not be added unless a task explicitly owns that visual signal.
6. Shared physics background variants and post-render noise live in `configs/domains/physics/base.yaml` and are inherited by the active mechanics, circuits, electrostatics, magnetism, fluids, optics, thermodynamics, and waves task groups through the domain visual-default loader; the default noise `apply_prob` is `0.5`.

## 4) Shared helper placement
1. Cross-domain scene/query compatibility sampling now lives in `trace/tasks/shared/variant_sampling.py`.
2. Physics-domain visual defaults belong in `trace/tasks/physics/shared/visual_defaults.py`.
3. Physics-domain normalized complexity helpers belong in `trace/tasks/physics/shared/complexity.py`.
4. Physics-domain named accent themes belong in `trace/tasks/physics/shared/style.py`.
5. Physics-domain resistor-network rendering helpers belong in `trace/tasks/physics/shared/circuit_scene.py`.
6. Physics-domain optics-board rendering helpers belong in `trace/tasks/physics/shared/optics_scene.py`.
7. Spring-extension, sticky-collision, electrostatics field-map, magnetism force-field, hydraulic-piston, PV-diagram, and wave-interference rendering are currently task-local; only the reusable physics theme / complexity / support helpers live under `trace/tasks/physics/shared/*`.

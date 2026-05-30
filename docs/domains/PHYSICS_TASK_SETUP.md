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
   - unordered `bbox_set` over the known weight blocks and marked `?` weight block needed to solve `missing_weight_to_balance`
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
   - `keyed_bbox_map` over the full vertical strands connecting the fixed and moving blocks plus the relevant force labels,
   - strand keys are `support_1`, `support_2`, ...,
   - `known_force` is the shown force label and `target_force` is the marked `?` force label.
7. `task_physics__pulley__pulley_mechanical_advantage` prompt policy:
   - ask for ideal pulley force magnitudes only,
   - say to use full connecting strands,
   - keep prompt-facing evidence on the supporting strands, shown known-force label, and marked target-force label.
8. Spring scene/query surface:
   - `scene_variant`: `paired_springs|staggered_springs|textured_spring`
   - public task ids: `task_physics__spring__spring_missing_value`, `task_physics__spring__spring_extension_difference`
   - `query_id`: `missing_value|extension_difference`
   - `solve_for`: `weight|extension` for `missing_value`
9. Spring evidence contract:
   - `keyed_bbox_map` over role-bound witnesses for `missing_value`: `reference_weight`, `reference_extension`, `query_weight`, and `query_extension`
   - unordered `bbox_set` over the two shown extension markers for `extension_difference`
10. Spring prompt policy:
   - say explicitly that the two springs are identical,
   - keep the arithmetic grounded in the shown weight/extension pairs rather than in an explicit formula label,
   - keep prompt-facing evidence on the weight blocks and value-labeled ruler markers,
   - allow non-semantic accent-color variation on the card chrome / supports / springs while keeping missing-value markers visibly red,
   - calibrate `extension_difference` with query-specific scale factor `2` and answer support `{2,4,8,10,12}` to avoid over-sampling small visual gaps,
   - sample shared technical-diagram backgrounds/palettes, one readout font family per diagram, and whole-diagram layout placement before projecting evidence.
11. Sticky-collision scene/query surface:
   - `scene_variant`: `wide_table|compact_table|gridded_table`
   - public task ids: `task_physics__collision__sticky_collision_direction_choice`, `task_physics__collision__sticky_collision_velocity_component_value`
   - `query_id`: `direction_choice|velocity_component`
   - `component_axis`: `x|y` for `velocity_component`
   - inputs are two perpendicular pucks with visible masses, speeds, and approach directions; the stuck pair shows the combined mass.
12. Sticky-collision evidence contract:
   - input-witness `keyed_point_map` over puck-center roles `A`, `B`, and `A+B` for both `direction_choice` and `velocity_component`
13. Sticky-collision prompt policy:
   - ask for the candidate final direction or one signed integer velocity component only,
   - keep all momentum quantities visible in the diagram,
   - do not render the solved final arrow in the main scene; candidate arrows are proposed answers, not a revealed solution,
   - keep prompt-facing evidence on the compact puck-state witnesses rather than on arrows, selected options, numeric annotations, answer labels, or decorative table chrome.
### `circuits`
1. Active tasks:
   - `task_physics__circuit_equivalent__total_resistance_value`
   - `task_physics__circuit_equivalent__total_capacitance_value`
2. Circuit scene/task surface:
   - scene id: `circuit_equivalent`
   - `scene_variant`: `series_parallel`
   - `query_id`: `total_resistance|total_capacitance`
   - every generated circuit must contain at least one series component and one or two parallel component blocks.
3. Circuit evidence contract:
   - input-witness `keyed_bbox_map` over visible component labels
   - resistor keys are `R1`, `R2`, ... and capacitor keys are `C1`, `C2`, ...
   - each bbox encloses the engineering symbol plus its value label; wires and terminal labels are not separate evidence.
4. Circuit prompt policy:
   - ask explicitly for equivalent resistance or capacitance between labeled terminals `A` and `B`,
   - draw resistors as zigzag engineering symbols and capacitors as parallel-plate symbols,
   - avoid pure-series and pure-parallel circuit diagrams in this calibrated public surface,
   - render component values in the keyed labels (`R1=... ohm`, `C1=... uF`),
   - keep prompt-facing evidence on the labeled components rather than on wires, terminals, or decorative circuit chrome,
   - keep calibrated public capacitance answers in `1..20`; resistance uses
     the constructively feasible subset `2..20` for mixed series-parallel
     circuits,
   - filter configured answer supports down to the constructively feasible subset for the chosen scene/query-id family before balanced sampling,
   - sample non-semantic palettes, technical-diagram backgrounds, stroke widths, fonts, and whole-diagram layout jitter independently of the answer.
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
   - direction-choice scenes use fixed point charges labeled with combined key/value tags like `Q1=+4`, a marked point `P`, and eight candidate arrows; zero-field scenes use two unequal same-sign fixed charges labeled `Q1` and `Q2` by the same key/value convention and six labeled candidate points; potential scenes use three fixed charges labeled `Q1`, `Q2`, and `Q3`, point `P`, and `r` distance labels with `k=1`.
3. Electrostatics evidence contract:
   - input-witness `keyed_point_map` over keys `Q1`, `Q2`, `Q3`, and `P` for `field_direction_choice`
   - input-witness `keyed_point_map` over keys `Q1` and `Q2` for `zero_field_point_label`
   - input-witness `keyed_point_map` over keys `Q1`, `Q2`, `Q3`, and `P` for `potential_value`
4. Electrostatics prompt policy:
   - ask for a single option letter or a signed integer potential only,
   - use query-specific scene descriptions so direction, zero-field, and potential prompts only mention the visible cues relevant to that query,
   - keep all field or potential quantities visible in the diagram,
   - keep force-on-negative-charge as an internal branch of the direction-choice task rather than a separate public task,
   - keep prompt-facing evidence on input witness objects/primitives rather than on the selected option, numeric annotations, answer label, or axis chrome.
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
   - input-witness `keyed_bbox_map` over keys `field_orientation`, `charge`, and `velocity` for `force_direction_choice`
4. Magnetism prompt policy:
   - ask for a single option letter only,
   - keep the magnetic-field orientation, charge sign, and velocity vector visible in the diagram,
   - keep field orientation and sign/velocity changes as internal query axes rather than separate public tasks,
   - keep prompt-facing evidence on the input witnesses rather than on selected candidate arrows, decorative field-symbol chrome, or option labels.
### `fluids`
1. Active tasks:
   - `task_physics__hydraulic__hydraulic_missing_value`
2. Hydraulic piston scene/query surface:
   - `scene_variant`: `wide_bench|compact_frame|tall_columns`
   - `query_id`: `missing_output_force|missing_input_force|missing_piston_area`
3. Hydraulic piston evidence contract:
   - `keyed_bbox_map` over only the known force/area labels needed to compute the missing value,
   - `missing_output_force` keys are `input_force`, `input_area`, and `output_area`,
   - `missing_input_force` keys are `output_force`, `input_area`, and `output_area`,
   - `missing_piston_area` keys are `input_force`, `output_force`, and `input_area`,
   - the red `?` target label and middle-reference labels stay visible as cues but are not evidence targets for the current query branches,
   - fluid chambers, pipe outlines, and decorative frame elements are not prompt-facing evidence.
4. Hydraulic piston prompt policy:
   - ask for integer force values in newtons or integer piston area in `cm^2`,
   - keep Pascal-law reasoning grounded in the shown input/output force/area labels while retaining the middle-reference piston as a visible consistency cue,
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
5. Optics rendering policy:
   - use shared `technical_diagram_style` for the outer sheet, board/grid palette, frame modes, and post-render noise,
   - sample one readout font family per board for coordinate labels,
   - move/place the whole board as one unit and project point evidence after final placement.
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
5. PV diagram rendering policy:
   - use shared `technical_diagram_style` for background/palette/frame/noise,
   - sample one readout font family per diagram,
   - apply whole-diagram layout placement before projecting evidence coordinates.
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
   - `path_difference_value` answers count absolute source-to-point path difference in `lambda/2` steps, calibrated on answers `1..5`.
3. Wave evidence contract:
   - unordered `point_set` over the center of the selected candidate point for `interference_point_choice`
   - `keyed_bbox_map` over the two labeled source-to-`P` path guides for `path_difference_value`, with keys `S1P` and `S2P`
4. Wave prompt policy:
   - ask for a single option letter or integer `lambda/2` step count only,
   - keep source phase, crest/trough rings, source labels, and ring-spacing legend visible,
   - keep constructive/destructive condition and source phase as internal axes rather than separate public tasks,
   - keep prompt-facing evidence on the selected point or keyed path-difference guide witnesses rather than on decorative wavefront rings,
   - sample shared technical-diagram backgrounds/palettes, one readout font family per tank, and whole-tank layout placement before projecting evidence.

## 3) Physics-domain policy
1. Prefer one stable diagram scaffold per task id; widen scene/query variety inside that task before adding more ids.
2. Keep arithmetic grounded in the visible diagram: if a quantity is not shown or clearly implied by the diagram, do not require it.
3. Mechanics tasks should keep vectors axis-aligned unless the task is explicitly about angled-force decomposition.
4. Prefer integer-valued constructions so answer verification stays exact and prompt-facing evidence remains local.
5. Physics visual diversity should stay non-semantic: background tints, shared technical diagram treatments, named accent palettes, layout placement, stroke variation, and the shared coordinate-preserving post-render noise policy are allowed when sampled before rendering and recorded in metadata. Any layout movement must project evidence after final placement.
6. Shared physics background variants and post-render noise live in `configs/domains/physics/base.yaml` and the shared `technical_diagram_style` layer; the default noise `apply_prob` is `0.5`.

## 4) Shared helper placement
1. Cross-domain scene/query compatibility sampling now lives in `trace/tasks/shared/variant_sampling.py`.
2. Physics-domain visual defaults belong in `trace/tasks/physics/shared/visual_defaults.py`.
3. Physics-domain normalized complexity helpers belong in `trace/tasks/physics/shared/complexity.py`.
4. Physics-domain named accent themes belong in `trace/tasks/physics/shared/style.py`.
5. Physics-domain resistor-network rendering helpers belong in `trace/tasks/physics/shared/circuit_scene.py`.
6. Physics-domain optics-board rendering helpers belong in `trace/tasks/physics/shared/optics_scene.py`.
7. Spring-extension, PV-diagram, and wave-interference rendering remain task-local, while sticky-collision, electrostatics field-map, magnetism force-field, hydraulic-piston, circuits, and pulley now use shared rendering/style helpers where available. All audited physics renderers should use the shared technical diagram style adapter unless the scene has a documented incompatibility.

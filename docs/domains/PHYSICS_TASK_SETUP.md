# Physics Task Setup

Use this document for the active `physics` domain contract.

For cross-domain coverage rollups, use `docs/project/STATUS.md` and `docs/domains/SCENE_TASK_QUERY_GUIDE.md` instead of repeating those inventories here.

## 1) Domain scope
1. `physics` should stay diagram-first: the image must contain the operative quantities and spatial grounding needed to solve the task.
2. Physics tasks should use visible, diagram-grounded arithmetic or formulas rather than hidden assumptions.
3. Prompt-facing annotation should stay on the visible witness objects in the diagram (for example force arrows, weights, resistors, or ray targets), not on decorative scene chrome.

## 2) Active families
### `mechanics`
1. Active tasks:
   - `task_physics__lever__side_torque_value`
   - `task_physics__lever__missing_weight_balance_value`
   - `task_physics__pulley__pulley_mechanical_advantage`
   - `task_physics__spring__spring_missing_value`
   - `task_physics__spring__spring_extension_difference`
   - `task_physics__collision__incoming_path_cause_choice`
   - `task_physics__collision__sticky_collision_direction_choice`
   - `task_physics__collision__sticky_collision_velocity_component_value`
   - `task_physics__free_body_forces__net_force_direction_choice`
   - `task_physics__orbital_motion__focus_location_label`
   - `task_physics__orbital_motion__orbital_speed_extremum_label`
   - `task_physics__motion_graph__velocity_sign_choice`
   - `task_physics__motion_graph__speed_change_state_choice`
   - `task_physics__motion_graph__interval_displacement_value`
   - `task_physics__stack_stability__stability_status_label`
   - `task_physics__gear_train__output_direction_label`
   - `task_physics__gear_train__output_speed_value`
2. Lever scene/query surface:
   - `scene_variant`: `center_fulcrum|offset_fulcrum|textured_beam`
   - public task ids: `task_physics__lever__side_torque_value`, `task_physics__lever__missing_weight_balance_value`
   - `query_id`: `side_torque|missing_weight_to_balance`
   - `torque_side`: `left|right` for `side_torque`
   - public missing-weight calibration uses `textured_beam`, answer support `1..6`, and at most two shown weights per side
3. Lever annotation contract:
   - unordered `bbox_set` over the weight blocks on the queried side for `side_torque`
   - `keyed_bbox_set_map` over `known_weights` and `target_weight` for `missing_weight_to_balance`
4. Lever prompt policy:
   - ask for torque or missing-weight magnitudes only,
   - keep all needed distances visible on the beam,
   - keep prompt-facing annotation on the weight blocks rather than the beam or fulcrum,
   - allow non-semantic accent-color variation on the beam / fulcrum / shown weights, but keep the marked `?` weight visibly red.
5. `task_physics__pulley__pulley_mechanical_advantage` scene/query surface:
   - `scene_variant`: `open_block|compact_block|tall_block`
   - `query_id`: `force_relation`
   - `solve_for`: `effort_force|load_force`
6. `task_physics__pulley__pulley_mechanical_advantage` annotation contract:
   - `keyed_bbox_map` over the full vertical strands connecting the fixed and moving blocks plus the relevant force labels,
   - strand keys are `support_1`, `support_2`, ...,
   - `known_force` is the shown force label and `target_force` is the marked `?` force label.
7. `task_physics__pulley__pulley_mechanical_advantage` prompt policy:
   - ask for ideal pulley force magnitudes only,
   - say to use full connecting strands,
   - keep prompt-facing annotation on the supporting strands, shown known-force label, and marked target-force label.
8. Spring scene/query surface:
   - `scene_variant`: `paired_springs|staggered_springs|textured_spring`
   - public task ids: `task_physics__spring__spring_missing_value`, `task_physics__spring__spring_extension_difference`
   - `query_id`: `missing_value|extension_difference`
   - `solve_for`: `weight|extension` for `missing_value`
9. Spring annotation contract:
   - `keyed_bbox_map` over role-bound witnesses for `missing_value`: `reference_weight`, `reference_extension`, `query_weight`, and `query_extension`
   - unordered `bbox_set` over the two shown extension markers for `extension_difference`
10. Spring prompt policy:
   - say explicitly that the two springs are identical,
   - keep the arithmetic grounded in the shown weight/extension pairs rather than in an explicit formula label,
   - keep prompt-facing annotation on the weight blocks and value-labeled ruler markers,
   - allow non-semantic accent-color variation on the card chrome / supports / springs while keeping missing-value markers visibly red,
   - calibrate `extension_difference` with query-specific scale factor `2` and answer support `{2,4,8,10,12}` to avoid over-sampling small visual gaps,
   - sample shared technical-diagram backgrounds/palettes, one readout font family per diagram, and whole-diagram layout placement before projecting annotation.
11. Sticky-collision scene/query surface:
   - `scene_variant`: `wide_table|compact_table|gridded_table`
   - public task ids: `task_physics__collision__sticky_collision_direction_choice`, `task_physics__collision__sticky_collision_velocity_component_value`
   - `query_id`: `direction_choice|velocity_component`
   - `component_axis`: `x|y` for `velocity_component`
   - inputs are two perpendicular pucks with visible masses, speeds, and approach directions; the stuck pair shows the combined mass.
12. Sticky-collision annotation contract:
   - input-witness `keyed_point_map` over puck-center roles `A`, `B`, and `A+B` for both `direction_choice` and `velocity_component`
13. Sticky-collision prompt policy:
   - ask for the candidate final direction or one signed integer velocity component only,
   - keep all momentum quantities visible in the diagram,
   - do not render the solved final arrow in the main scene; candidate arrows are proposed answers, not a revealed solution,
   - keep prompt-facing annotation on the compact puck-state witnesses rather than on arrows, selected options, numeric annotations, answer labels, or decorative table chrome.
14. Collision-aftermath scene/query surface:
   - `scene_variant`: `aftermath_table|aftermath_gridded_table|aftermath_compact_table`
   - public task id: `task_physics__collision__incoming_path_cause_choice`
   - `query_id`: `incoming_path_cause_choice`
   - scenes show an impact marker, a target puck after impact with its motion trail, and six labeled candidate incoming paths.
15. Collision-aftermath annotation contract:
   - `keyed_bbox_map` over `impact_point` and `target_after_motion`
   - annotation must mark the impact marker and aftermath puck/trail witnesses, not candidate option arrows or option letters.
16. Collision-aftermath prompt policy:
   - ask for a single option letter only,
   - use backward causal wording from the shown aftermath to the incoming path,
   - keep the correct option letter independent of direction, color, and scene variant,
   - keep candidate arrows visually neutral; do not highlight or otherwise reveal the correct incoming path.
17. Free-body-forces scene/query surface:
   - public task id: `task_physics__free_body_forces__net_force_direction_choice`
   - `scene_variant`: `clean_table|gridded_table|lab_card`
   - `query_id`: `net_force_direction_choice`
   - scenes show one object with several cardinal applied-force arrows, visible force ids and magnitude labels, and eight neutral candidate net-force arrows A-H.
18. Free-body-forces annotation contract:
   - unordered `bbox_set` over each applied force arrow and its magnitude label
   - annotation must not mark option arrows, option letters, the object body by itself, decorative panel chrome, or a solved resultant arrow.
19. Free-body-forces prompt policy:
   - ask for the direction of the net force, not the direction of motion,
   - use candidate arrow letters as visual answer options,
   - construct diagonal resultants from equal residual horizontal and vertical components,
   - keep option letter, color, duplicate/canceling force layout, and scene variant independent of the answer.
20. Orbital-motion scene/query surface:
   - public task ids: `task_physics__orbital_motion__focus_location_label`, `task_physics__orbital_motion__orbital_speed_extremum_label`
   - `query_id`: `sun_focus_label|greatest_speed_position_label|least_speed_position_label`
   - focus-location scenes show an ellipse and labeled candidate points without a semantic Sun marker; speed-extremum scenes show the Sun at one focus and labeled positions on the orbit.
21. Orbital-motion annotation contract:
   - `keyed_point_map` over `center`, `selected_focus`, `major_axis_endpoint_1`, and `major_axis_endpoint_2` for `focus_location_label`
   - `keyed_point_map` over `sun` and `selected_position` for `orbital_speed_extremum_label`
22. Orbital-motion prompt policy:
   - ask for a single candidate label only,
   - use Kepler-first-law/focus wording for focus location and perihelion/aphelion speed reasoning for speed extrema,
   - keep prompt-facing annotation on the local focus/position points rather than on option labels or decorative orbit chrome.
23. Motion-graph scene/query surface:
   - public task ids: `task_physics__motion_graph__velocity_sign_choice`, `task_physics__motion_graph__speed_change_state_choice`, `task_physics__motion_graph__interval_displacement_value`
   - `scene_variant`: `clean_grid|paper_grid|bold_grid`
   - qualitative-state `query_id`: `velocity_sign_choice|speed_change_state_choice`
   - interval-displacement `query_id`: `constant_velocity_interval_displacement|constant_acceleration_interval_displacement`
   - `velocity_sign_choice` renders an `x`-vs-`t` graph and asks for the motion state from the marked interval's slope
   - `speed_change_state_choice` renders a `v`-vs-`t` graph and asks for the speed-change state from the marked interval's velocity sign and slope
   - `interval_displacement_value` renders only nonnegative `v`-vs-`t` graphs and asks for integer displacement over the marked interval.
24. Motion-graph annotation contract:
   - `keyed_bbox_map` over `query_region` and `curve_segment`
   - `query_region` marks the highlighted time interval; `curve_segment` marks the local graph segment used to infer the state
   - visible option boxes are answer choices and must not be prompt-facing annotation
   - interval-displacement annotation uses `keyed_bbox_map` keys `marked_interval`, `velocity_segment`, and `axis_scale`; it must not mark derived displacement text or any prompt-only formula.
25. Motion-graph prompt policy:
   - ask for a single option letter only for `velocity_sign_choice` and `speed_change_state_choice`, and an integer displacement in meters for `interval_displacement_value`,
   - keep position-time velocity-sign and velocity-time speed-change semantics as separate public contracts because they use different graph semantics,
   - keep interval-displacement as a separate public contract because it changes answer type and reasoning program from qualitative state choice to numeric area under a velocity-time graph,
   - reject near-zero slopes or near-zero velocity values except for explicit stationary or constant-speed cases,
   - keep curve style, grid/background treatment, marked interval placement, and option order independent of the answer.
   - for interval displacement, keep velocities nonnegative and endpoint values/grid spacing chosen so the rectangle or trapezoid area is an integer.
26. Stack-stability scene/query surface:
   - public task id: `task_physics__stack_stability__stability_status_label`
   - `query_id`: `stable_stack_label|tipping_stack_label`
   - renders six labeled equal-density brick stacks; each stack shows a red center-of-mass marker, a dashed vertical projection, and a support-footprint bracket.
   - `stable_stack_label` has exactly one stable stack and tipping distractors; `tipping_stack_label` has exactly one tipping stack and stable distractors.
   - tip direction is an internal balanced axis for visual variety and is not a separate public query.
27. Stack-stability annotation contract:
   - `keyed_bbox_map` over `center_of_mass`, `projection`, and `support_footprint` for the selected stack only
   - annotation must not mark option letters, decorative cells, unrelated stacks, or prompt-only answer labels.
28. Stack-stability prompt policy:
   - ask for a single option letter only,
   - define stability through whether the center-of-mass projection falls inside or outside the support-footprint bracket,
   - keep brick color, row count, stack position, and option letter independent of stable/tipping status except for the intended COM/support geometry.
29. Gear-train scene/query surface:
   - public task ids: `task_physics__gear_train__output_direction_label`, `task_physics__gear_train__output_speed_value`
   - `scene_variant`: `straight_chain|staggered_chain|arc_chain`
   - `query_id`: `marked_output_direction|simple_gear_ratio_output_speed`
   - direction scenes show `2..6` directly meshed gears, an input gear with a visible rotation arrow, and a marked output gear.
   - speed scenes show `2..4` directly meshed gears with tooth-count labels, a visible input rpm label, and a marked output rpm label.
30. Gear-train annotation contract:
   - direction task: `keyed_bbox_map` over `input_gear`, `input_rotation_arrow`, `output_gear`, and `gear_train`
   - speed task: `keyed_bbox_map` over `input_gear`, `output_gear`, and `gear_train`
   - annotation marks the visible gear witnesses, input arrow for direction, and tooth/speed labels for speed. It must not mark a solved output arrow, derived output speed, or decorative background.
31. Gear-train prompt policy:
   - direction asks for exactly `clockwise` or `counterclockwise`,
   - speed asks for an integer rpm value using `output_rpm = input_rpm * input_teeth / output_teeth`,
   - keep v1 to simple direct gear meshes where every adjacent mesh reverses direction,
   - use idler gears as visual context only for speed; they do not change the simple input/output tooth-count ratio,
   - keep gear count, layout, gear radii, colors, and input side independent of the final answer except for the intended parity or ratio relation.
### `circuits`
1. Active tasks:
   - `task_physics__circuit_equivalent__total_resistance_value`
   - `task_physics__circuit_equivalent__total_capacitance_value`
   - `task_physics__bulb_circuit__brightness_extremum_label`
   - `task_physics__switch_circuit__lit_bulb_count`
   - `task_physics__circuit_state_change__bulb_brightness_change_label`
   - `task_physics__bridge_circuit__bridge_missing_resistance_value`
   - `task_physics__analog_meter__meter_readout_value`
2. Circuit scene/task surface:
   - scene id: `circuit_equivalent`
   - `scene_variant`: `series_parallel`
   - `query_id`: `total_resistance|total_capacitance`
   - every generated circuit must contain at least one series component and one or two parallel component blocks.
   - bulb-brightness scenes use scene id `bulb_circuit`, `scene_variant=series_unequal|parallel_unequal|mixed_branch`, and `query_id=brightest_bulb_label|dimmest_bulb_label`.
   - switch-circuit scenes use scene id `switch_circuit`, `scene_variant=mixed_branch`, and `query_id=lit_bulb_count`; all generated scenes include parallel branches plus a local sub-branch, not simple series-only layouts.
   - circuit-state-change scenes use scene id `circuit_state_change` and `query_id=brightens_after_switch_change|dims_after_switch_change|turns_on_after_switch_change|turns_off_after_switch_change`; all generated scenes show five labeled bulbs, visible resistance labels, and one red-boxed switch action cue.
   - bridge-balance scenes use scene id `bridge_circuit`, `scene_variant=rectangular_bridge`, and `query_id=missing_bridge_resistance`.
   - analog-meter scenes use scene id `analog_meter`, `query_id=ammeter_readout|voltmeter_readout`, and profiles `ammeter_a|ammeter_ma|voltmeter_v`.
3. Circuit annotation contract:
   - input-witness `keyed_bbox_map` over visible component labels
   - resistor keys are `R1`, `R2`, ... and capacitor keys are `C1`, `C2`, ...
   - each bbox encloses the engineering symbol plus its value label; wires and terminal labels are not separate annotation.
   - bulb-brightness annotation is a `keyed_bbox_map` over all visible bulbs `B1` through `B5`, with each bbox enclosing the bulb symbol plus its resistance label.
   - switch-circuit annotation is an unordered `bbox_set` over only the bulb symbols that will be on; if no bulbs are on, annotation is an empty array.
   - circuit-state-change annotation is a `keyed_bbox_map` over `changed_switch` and bulb labels `B1` through `B5`; bulb bboxes include each bulb symbol and resistance label, and `changed_switch` marks the switch-action cue.
   - bridge-balance annotation is a `keyed_bbox_map` over the known visible resistor labels, `target_resistor`, and `zero_meter`; the zero meter is included because it supplies the null-balance condition.
   - analog-meter annotation is a `keyed_bbox_map` over `needle`, `scale_region`, and `unit_label`; annotation marks the visible readout witnesses rather than the meter casing or decorative panel.
4. Circuit prompt policy:
   - ask explicitly for equivalent resistance or capacitance between labeled terminals `A` and `B`,
   - draw resistors as zigzag engineering symbols and capacitors as parallel-plate symbols,
   - avoid pure-series and pure-parallel circuit diagrams in this calibrated public surface,
   - render component values in the keyed labels (`R1=... ohm`, `C1=... uF`),
   - keep prompt-facing annotation on the labeled components rather than on wires, terminals, or decorative circuit chrome,
   - keep calibrated public capacitance answers in `1..20`; resistance uses
     the constructively feasible subset `2..20` for mixed series-parallel
     circuits,
   - filter configured answer supports down to the constructively feasible subset for the chosen scene/query-id family before balanced sampling,
   - sample non-semantic palettes, technical-diagram backgrounds, stroke widths, fonts, and whole-diagram layout jitter independently of the answer.
   - for bulb brightness, ask for the bulb label only, keep resistance labels visible, state ideal-battery/wire semantics through the scene/prompt contract, and do not encode brightness with glow intensity.
   - keep bulb-brightness ranking and equivalent-component calculations as separate public task contracts.
   - for switch circuits, ask for the integer count only, keep switch positions visually open/closed, and do not visually glow lit bulbs.
   - for circuit state changes, ask for one bulb label only, keep before/after state encoded by the red-boxed switch action cue, and do not visually glow bulbs or draw derived current paths.
   - keep circuit-state-change brightness comparison separate from static bulb-brightness extrema and switch-connectivity bulb counts.
   - for bridge balance, ask for the missing resistance only, show the target as a question-mark resistor, keep the center meter reading visibly zero, and keep bridge-balance solves separate from equivalent-resistance calculations.
   - for analog meters, ask for the integer readout in the displayed unit, keep the scale conventional left-to-right/clockwise, and keep first-version needle positions exactly on supported tick values.
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
   - view contracts are query-specific: direction arrows, zero-field candidate points, and potential distance labels are distinct query-facing scaffolds under the same field-map scene renderer.
3. Electrostatics annotation contract:
   - input-witness `keyed_point_map` over keys `Q1`, `Q2`, `Q3`, and `P` for `field_direction_choice`
   - input-witness `keyed_point_map` over keys `Q1` and `Q2` for `zero_field_point_label`
   - input-witness `keyed_point_map` over keys `Q1`, `Q2`, `Q3`, and `P` for `potential_value`
4. Electrostatics prompt policy:
   - ask for a single option letter or a signed integer potential only,
   - use query-specific scene descriptions so direction, zero-field, and potential prompts only mention the visible cues relevant to that query,
   - keep all field or potential quantities visible in the diagram,
   - keep force-on-negative-charge as an internal branch of the direction-choice task rather than a separate public task,
   - keep prompt-facing annotation on input witness objects/primitives rather than on the selected option, numeric annotations, answer label, or axis chrome.
### `magnetism`
1. Active tasks:
   - `task_physics__electromagnetic_induction__induced_current_direction_count`
   - `task_physics__magnetic_force__force_direction_choice`
   - `task_physics__wire_magnetism__wire_field_direction_choice`
2. Magnetism force-field scene/query surface:
   - `scene_variant`: `clean_panel|field_grid|lab_card`
   - public task id: `task_physics__magnetic_force__force_direction_choice`
   - `query_id`: `force_direction_choice`
   - `field_orientation`: `out_of_page|into_page`
   - `velocity_direction`, `charge_sign`, and candidate-arrow placement are internal axes for `force_direction_choice`.
   - public calibration uses `field_grid` with correct-answer letters `B|C|D|E|G|H`; all eight candidate arrows remain visible.
3. Magnetism annotation contract:
   - input-witness `keyed_bbox_map` over keys `field_orientation`, `charge`, and `velocity` for `force_direction_choice`
4. Magnetism prompt policy:
   - ask for a single option letter only,
   - keep the magnetic-field orientation, charge sign, and velocity vector visible in the diagram,
   - keep field orientation and sign/velocity changes as internal query axes rather than separate public tasks,
   - keep prompt-facing annotation on the input witnesses rather than on selected candidate arrows, decorative field-symbol chrome, or option labels.
5. Wire-magnetism scene/query surface:
   - public task id: `task_physics__wire_magnetism__wire_field_direction_choice`
   - `query_id`: `field_direction_at_point`
   - the scene shows one straight current-carrying wire, a current arrow, a marked point `P`, and six labeled direction options with one correct into-page/out-of-page field option.
6. Wire-magnetism annotation contract:
   - `keyed_bbox_map` over `wire_current` and `point_p`
   - option boxes remain visible answer choices but are not prompt-facing annotation.
7. Wire-magnetism prompt policy:
   - ask for a single option letter only,
   - keep the current direction and point location visually clear enough for right-hand-rule reasoning,
   - balance current direction, point side, wire orientation, and option order independently of the correct answer.
8. Electromagnetic-induction scene/query surface:
   - public task id: `task_physics__electromagnetic_induction__induced_current_direction_count`
   - `query_id`: `clockwise_induced_current_count|counterclockwise_induced_current_count|no_induced_current_count`
   - the scene shows six mini-panels, each with a conducting loop, into-page or out-of-page magnetic-field symbols, and a visible cue for increasing, decreasing, or unchanged magnetic flux.
   - supported answers are `0..6`.
9. Electromagnetic-induction annotation contract:
   - unordered `bbox_set` over the full mini-panel boxes whose loop matches the queried induced-current class
   - if the answer is `0`, annotation is an empty array
   - annotation must not mark individual field symbols, loop arrows, cue text alone, option labels, or decorative panel chrome.
10. Electromagnetic-induction prompt policy:
   - ask for an integer count only,
   - keep clockwise, counterclockwise, and no-current as query branches under the same public task contract,
   - keep prompt-facing annotation on the matching mini-panels rather than on derived current arrows or explanatory annotations,
   - sample target count across `0..6` and construct the panel set to match the sampled answer exactly.
### `fluids`
1. Active tasks:
   - `task_physics__hydraulic__hydraulic_missing_value`
   - `task_physics__graduated_cylinder__volume_readout_value`
   - `task_physics__graduated_cylinder__displacement_volume_value`
   - `task_physics__buoyancy_density__object_density_value`
   - `task_physics__manometer__pressure_difference_value`
   - `task_physics__fluid_flow__continuity_speed_value`
2. Buoyancy-density scene/query surface:
   - public task id: `task_physics__buoyancy_density__object_density_value`
   - `query_id`: `floating_object_density_value`
   - scenes show a floating object divided into equal parts, a visible liquid surface, and a liquid-density label.
3. Buoyancy-density annotation contract:
   - `keyed_bbox_map` over `floating_object`, `waterline`, `fluid_density_label`, and `submerged_fraction_marker`
   - annotation marks only the visual witnesses needed to read the submerged fraction and liquid density; it must not mark derived answer text or decorative tank/background elements.
4. Buoyancy-density prompt policy:
   - ask for object density in `g/cm^3` as a decimal number,
   - keep the visible waterline aligned to an equal-part division boundary so the submerged fraction is visually unambiguous,
   - balance scene variant, object shape, target answer, liquid density, and submerged fraction independently so color or shape is never tied to the answer.
5. Fluid-flow scene/query surface:
   - public task id: `task_physics__fluid_flow__continuity_speed_value`
   - `query_id`: `continuity_missing_speed`
   - scenes show a steady two-station pipe/nozzle with station labels `1` and `2`, cross-section area labels in `cm^2`, one known speed, one missing speed label, and a flow arrow.
   - `orientation`: `horizontal_pipe|vertical_pipe` is an internal rendering axis.
6. Fluid-flow annotation contract:
   - `keyed_bbox_map` over `station_1`, `station_2`, and `flow_path`
   - station boxes include the visible area/speed labels for that station; the flow path marks the pipe and arrow witness.
   - decorative panel/background elements and the derived answer are not prompt-facing annotation.
7. Fluid-flow prompt policy:
   - ask for a positive integer speed in `m/s`,
   - use continuity `A1 * v1 = A2 * v2` with visible area labels rather than diameter labels in the first calibrated version,
   - balance missing `v1` versus missing `v2`, answer support, orientation, pipe taper, and fluid color independently.
8. Hydraulic piston scene/query surface:
   - `scene_variant`: `wide_bench|compact_frame|tall_columns`
   - `query_id`: `missing_output_force|missing_input_force|missing_piston_area|missing_input_area`
9. Hydraulic piston annotation contract:
   - `keyed_bbox_map` over only the known force/area labels needed to compute the missing value,
   - `missing_output_force` keys are `input_force`, `input_area`, and `output_area`,
   - `missing_input_force` keys are `output_force`, `input_area`, and `output_area`,
   - `missing_piston_area` keys are `input_force`, `output_force`, and `input_area`,
   - `missing_input_area` keys are `input_force`, `output_force`, and `output_area`,
   - the red `?` target label and middle-reference labels stay visible as cues but are not annotation targets for the current query branches,
   - fluid chambers, pipe outlines, and decorative frame elements are not prompt-facing annotation.
10. Hydraulic piston prompt policy:
   - ask for integer force values in newtons or integer piston area in `cm^2`,
   - keep Pascal-law reasoning grounded in the shown input/output force/area labels while retaining the middle-reference piston as a visible consistency cue,
   - use calibrated mechanical-advantage ratios `3..8` so the public task avoids trivial doubling cases,
   - keep the missing label visibly red while allowing non-semantic accent-color variation on the chambers, fluid, and pistons.
11. Graduated-cylinder scene/query surface:
   - public task ids: `task_physics__graduated_cylinder__volume_readout_value`, `task_physics__graduated_cylinder__displacement_volume_value`
   - `query_id`: `single_cylinder_volume_readout|before_after_displacement_volume`
   - volume-readout scenes show one cylinder; displacement scenes show matched `Before` and `After` cylinders with the same scale.
12. Graduated-cylinder annotation contract:
   - `keyed_bbox_map` over `meniscus` and `scale_region` for single-cylinder readout
   - `keyed_bbox_map` over `before_meniscus`, `before_scale_region`, `after_meniscus`, and `after_scale_region` for displacement
13. Graduated-cylinder prompt policy:
   - ask for integer `mL` values only,
   - keep the meniscus and nearby tick scale readable,
   - keep annotation on the role-bound meniscus/scale witnesses rather than on vessel chrome or decorative liquid/object areas.
14. Manometer scene/query surface:
   - public task id: `task_physics__manometer__pressure_difference_value`
   - `query_id`: `u_tube_pressure_difference`
   - scenes show a U-tube manometer with pressure points `A` and `B`, two liquid levels, a visible height-difference marker, and a `rho g` conversion label.
15. Manometer annotation contract:
   - `keyed_bbox_map` over `left_pressure_point`, `right_pressure_point`, `height_difference`, and `fluid_density_label`
   - annotation marks only the pressure-point labels, height witness, and conversion label needed to compute the pressure difference; it must not mark the derived answer or decorative tube/background elements.
16. Manometer prompt policy:
   - ask for the absolute pressure difference between `A` and `B` as an integer `kPa` value,
   - keep first-version scenes single-fluid with integer centimeter height differences and integer `kPa/cm` conversion labels,
   - balance which side has higher pressure independently from answer value, height difference, conversion factor, and fluid color.
### `optics`
1. Active tasks:
   - `task_physics__ray_optics__ray_bounce_count`
   - `task_physics__ray_optics__ray_target_hit_count`
   - `task_physics__refraction_layers__medium_speed_order_label`
   - `task_physics__shadow_cause__light_source_label`
   - `task_physics__lens_optics__image_property_choice`
2. Optics scene/query surface:
   - `scene_variant`: `single_mirror|double_mirror|triple_mirror|quad_mirror|five_mirror`
   - `query_id`: `bounce_count|target_hit_count`
   - view contracts are query-specific: `bounce_count` grounds hidden-path reflection points, while `target_hit_count` grounds visible target points intersected by the hidden path.
   - refraction layers use scene id `refraction_layers`, query id `three_medium_speed_order`, and three labeled media `M1`, `M2`, and `M3` with a visible ray crossing two interfaces.
   - shadow-cause uses scene id `shadow_cause`, query id `source_from_shadow_label`, one visible object, one cast shadow, and six labeled candidate light sources.
   - lens-optics uses scene id `lens_optics`, query id `converging_lens_image_property_choice`, one converging thin lens, focal marks `F` and `2F` on both sides, one object arrow, and four visible image-property option cards.
3. Optics annotation contract:
   - unordered pixel `point_set` over the rendered bounce-point centers for `bounce_count`
   - unordered pixel `point_set` over the rendered hit target-point centers for `target_hit_count`
   - `keyed_bbox_map` over the local ray/normal interactions for refraction, with keys `interface_1_bend` and `interface_2_bend`
   - `keyed_bbox_map` over the visible object and cast shadow for shadow-cause, with keys `object` and `shadow`; candidate light-source labels and lamp boxes are answer options, not annotation.
   - `keyed_bbox_map` over visible lens-optics witnesses, with keys `lens`, `object_arrow`, and `focal_marks`; option cards and option letters are answer choices, not annotation.
4. Optics prompt policy:
   - ask the user to infer the hidden ray path from the shown initial direction plus the mirrors,
   - keep only the initial ray direction visible in the prompt image and keep the solved path in trace/debug artifacts,
   - keep prompt-facing annotation on pixel points rather than on graph-coordinate labels or large mirror/target bboxes,
   - use large unlabeled target points for `target_hit_count` and no separate bounce circles for `bounce_count`,
   - calibrate `target_hit_count` on answers `1..5` with four or five target points,
   - reserve `single_mirror|double_mirror|triple_mirror` for `target_hit_count`, while `bounce_count` uses `five_mirror` with answers `1..5` so that the calibrated public mix avoids zero-bounce hard cases.
   - for refraction, ask for the visible option letter giving the fastest-to-slowest light-speed order; do not show numeric refractive-index or speed labels, and do not use the option boxes as annotation.
   - for shadow-cause, ask for the visible light-source label; do not reveal source or shadow directions in prompt text, and do not use option lamps/letters as annotation.
   - for lens-optics, ask for the visible option letter describing the image as real/virtual, upright/inverted, and larger/smaller/same-size from the object position relative to `F` and `2F`.
   - lens-optics v0 is converging-lens only; it excludes diverging lenses, object-at-F/no-image cases, and prompt wording that names the sampled object-position case.
5. Optics rendering policy:
   - use shared `technical_diagram_style` for the outer sheet, board/grid palette, frame modes, and post-render noise,
   - sample one readout font family per board for coordinate labels,
   - move/place the whole board as one unit and project point annotation after final placement.
   - refraction layers may vary horizontal/vertical layer orientation and ray entry side while keeping speed ranks independent from media colors, labels, and option placement.
   - shadow-cause varies shadow direction, object shape, object color, and option-letter placement independently; only the object-to-shadow direction determines the correct opposite light-source location.
   - lens-optics varies the object-position case, scene style, option order, option letter, and accent color independently; do not draw the solved image arrow in the prompt image.
### `thermodynamics`
1. Active tasks:
   - `task_physics__piston_cylinder__boundary_work_value`
   - `task_physics__thermometer__temperature_conversion_value`
   - `task_physics__thermal_mixing__final_temperature_value`
   - `task_physics__pv_diagram__pv_work_value`
   - `task_physics__pv_diagram__pv_process_sign_choice`
2. PV diagram scene/query surface:
   - `scene_variant`: `clean_grid|paper_grid|bold_grid`
   - public task ids: `task_physics__pv_diagram__pv_work_value`, `task_physics__pv_diagram__pv_process_sign_choice`
   - `query_id`: `work_value|process_sign_choice`
   - calibrated `work_value` sampling uses `work_mode=single_process`; explicit rectangular-cycle construction remains a supported internal renderer path but is not in the default public calibration mix
   - `target_sign`: `positive|negative|zero` for `process_sign_choice`
3. PV diagram annotation contract:
   - one-box `bbox_set` over the highlighted PV process or cycle for `work_value`
   - one-box `bbox_set` over the process arrow in the correct labeled mini-process option for `process_sign_choice`
4. PV diagram prompt policy:
   - ask for signed integer work in joules or a single option letter only,
   - keep pressure in `kPa`, volume in `L`, and the `1 kPa*L = 1 J` conversion visible or prompt-explicit,
   - for numeric work, state the single-process formula `P * (V_final - V_initial)` and use rightward expansion as positive gas work and leftward compression as negative gas work,
   - keep prompt-facing annotation on the highlighted path or selected candidate process rather than on axis chrome.
5. PV diagram rendering policy:
   - use shared `technical_diagram_style` for background/palette/frame/noise,
   - sample one readout font family per diagram,
   - apply whole-diagram layout placement before projecting annotation coordinates.
6. Piston-cylinder scene/query surface:
   - public task id: `task_physics__piston_cylinder__boundary_work_value`
   - `query_id`: `constant_pressure_boundary_work`
   - scenes show initial and final piston-cylinder states at the same pressure, with pressure in `MPa`, volumes in `L`, and a process arrow.
   - orientation is an internal axis: `vertical_pair|horizontal_pair`.
7. Piston-cylinder annotation contract:
   - `keyed_bbox_map` over `piston_cylinder`, `initial_state_label`, `final_state_label`, and `process_arrow`
   - state-label boxes are annotation because they provide the pressure and volume operands; decorative frame/background grid lines are not annotation.
8. Piston-cylinder prompt policy:
   - ask for signed integer boundary work in `kJ`,
   - use `W = P * (V_final - V_initial)` and the visible conversion `1 MPa*L = 1 kJ`,
   - use positive work for expansion and negative work for compression,
   - omit zero-work cases in the initial calibrated support.
9. Thermometer scene/query surface:
   - public task id: `task_physics__thermometer__temperature_conversion_value`
   - `query_id`: `celsius_to_fahrenheit_value|fahrenheit_to_celsius_value`
   - scenes show one vertical thermometer with a visible liquid level, numeric tick scale, and source unit label.
   - scale profile is an internal axis; the first public version keeps source values tick-aligned and target answers integer-valued.
10. Thermometer annotation contract:
   - `keyed_bbox_map` over `liquid_level`, `scale_region`, and `source_unit_label`
   - annotation marks the visible source readout witnesses only; the converted target value is derived from the prompt formula and must not appear as image text.
11. Thermometer prompt policy:
   - ask for the converted integer temperature in the target unit,
   - include the relevant conversion formula in the prompt,
   - do not add a separate simple readout task unless a future audit shows that thermometer readout alone is needed.
12. Thermal-mixing scene/query surface:
   - public task id: `task_physics__thermal_mixing__final_temperature_value`
   - `query_id`: `equal_amount_final_temperature`
   - scenes show `2..4` separate cups of the same liquid with equal amounts and visible Celsius temperature labels, being poured into an insulated mixing container.
13. Thermal-mixing annotation contract:
   - unordered `bbox_set` over the initial cups and their visible temperature labels
   - annotation marks only the initial-state temperature witnesses; the final mixing container and derived final temperature are not annotation targets.
14. Thermal-mixing prompt policy:
   - ask for the integer final equilibrium temperature in degrees Celsius,
   - state that the liquid amounts are equal, the liquid is the same, and the system is insulated/no heat is lost,
   - construct initial temperatures so their average is an integer,
   - keep cup count, cup order, liquid color, and temperature placement independent of the answer.

### `measurement`
1. Active tasks:
   - `task_physics__vernier_caliper__length_readout_value`
2. Vernier-caliper scene/query surface:
   - public task id: `task_physics__vernier_caliper__length_readout_value`
   - `query_id`: `main_scale_vernier_mm`
   - scenes show one horizontal Vernier caliper measuring an object, with a visible main millimeter scale, a sliding vernier scale, a vernier zero mark, and a `0.1 mm` vernier resolution.
   - `main_mm`, `aligned_vernier_tick`, and target answer are internal numeric axes inside one readout contract.
3. Vernier-caliper annotation contract:
   - `keyed_bbox_map` over `main_scale_region`, `vernier_zero`, `vernier_scale_region`, and `aligned_vernier_tick`
   - annotation marks only the visible scale witnesses needed to compute the readout; it must not mark derived answer text, decorative caliper casing alone, or the measured object as a replacement for the scale.
4. Vernier-caliper prompt policy:
   - ask for the measured length in millimeters as a one-decimal numeric value with no unit string,
   - state or show the `0.1 mm` vernier resolution,
   - keep the answer fractional in tenths of a millimeter so the task remains distinct from an ordinary ruler readout,
   - balance main-scale reading and aligned vernier tick independently of color, layout jitter, font, and background style.

### `waves`
1. Active tasks:
   - `task_physics__wave_interference__interference_point_choice`
   - `task_physics__wave_interference__path_difference_value`
   - `task_physics__waveform_panel__wave_property_extremum_label`
   - `task_physics__signal_transform__sinusoid_component_spectrum_match_label`
   - `task_physics__signal_transform__periodic_harmonic_spectrum_match_label`
   - `task_physics__signal_transform__pulse_width_spectrum_match_label`
2. Waveform-panel scene/query surface:
   - public task id: `task_physics__waveform_panel__wave_property_extremum_label`
   - `scene_variant`: `clean_stack|grid_stack|lab_sheet`
   - `query_id`: `highest_amplitude_label|lowest_amplitude_label|highest_frequency_label|lowest_frequency_label|longest_wavelength_label|shortest_wavelength_label`
   - scenes show `4`, `5`, or `6` stacked sinusoidal waveform panels labeled `A` onward on one shared horizontal scale.
3. Waveform-panel annotation contract:
   - unordered `bbox_set` containing one box around the selected waveform panel, including its label and waveform
   - annotation must not include all panels, background grid lines, title text, or derived property labels.
4. Waveform-panel prompt policy:
   - ask for a single selected panel letter only,
   - keep amplitude, frequency, and wavelength comparisons grounded in the visible wave geometry rather than numeric labels,
   - keep panel count, scene style, query property, and correct panel letter as internal axes,
   - construct unique extrema with adequate amplitude or cycle-count separation.
5. Signal-transform scene/query surface:
   - public task ids: `task_physics__signal_transform__sinusoid_component_spectrum_match_label`, `task_physics__signal_transform__periodic_harmonic_spectrum_match_label`, `task_physics__signal_transform__pulse_width_spectrum_match_label`
   - `scene_variant`: `clean_match|grid_match|lab_sheet`
   - each public task fixes one query id: `sinusoid_component_spectrum`, `periodic_wave_harmonic_spectrum`, or `pulse_width_spectrum`
   - scenes show one time-domain waveform panel and five labeled one-sided magnitude-spectrum option panels.
   - sinusoid-component tasks support single-sinusoid and two-tone waveforms; periodic-harmonic tasks support square, triangle, and sawtooth waveforms; pulse-width tasks support narrow and wide rectangular pulses.
6. Signal-transform annotation contract:
   - `keyed_bbox_map` over `input_waveform` and `selected_spectrum`
   - annotation marks the input waveform panel and the selected matching spectrum option; it must not mark every option, decorative axes, prompt text, or hidden semantic labels.
7. Signal-transform prompt policy:
   - ask for a single option letter only,
   - keep options visual rather than prompt-only choices,
   - use one-sided magnitude spectra in the initial public version,
   - keep waveform family, query id, option label, spectrum distractors, and style independent where feasible,
   - avoid equation choices, phase spectra, dense tick labels, and hidden textual names for the waveform family.
8. Wave-interference scene/query surface:
   - `scene_variant`: `clean_tank|grid_tank|lab_sheet`
   - public task ids: `task_physics__wave_interference__interference_point_choice`, `task_physics__wave_interference__path_difference_value`
   - `query_id`: `interference_point_choice|path_difference_value`
   - `phase_relation`: `in_phase|opposite_phase`
   - `target_condition`: `constructive|destructive` for `interference_point_choice`
   - `interference_point_choice` uses five candidate points `A-E` in the calibrated public mix.
   - `path_difference_value` answers count absolute source-to-point path difference in `lambda/2` steps, calibrated on answers `1..5`.
9. Wave-interference annotation contract:
   - unordered `point_set` over the center of the selected candidate point for `interference_point_choice`
   - `keyed_bbox_map` over the two labeled source-to-`P` path guides for `path_difference_value`, with keys `S1P` and `S2P`
10. Wave-interference prompt policy:
   - ask for a single option letter or integer `lambda/2` step count only,
   - keep source phase, crest/trough rings, source labels, and ring-spacing legend visible,
   - keep constructive/destructive condition and source phase as internal axes rather than separate public tasks,
   - keep prompt-facing annotation on the selected point or keyed path-difference guide witnesses rather than on decorative wavefront rings,
   - sample shared technical-diagram backgrounds/palettes, one readout font family per tank, and whole-tank layout placement before projecting annotation.

## 3) Concrete task-program schemas
Use these concrete schemas for taxonomy review; generic placeholders such as
`formula.solve_unknown` or `physics.direction_or_sign_rule` are draft-only.

| Scene | Task slug | Program schema |
| --- | --- | --- |
| `circuit_equivalent` | `total_resistance_value` | `equivalent_resistance(components=resistor_components_between_terminals, topology=series_parallel_network)` |
| `circuit_equivalent` | `total_capacitance_value` | `equivalent_capacitance(components=capacitor_components_between_terminals, topology=series_parallel_network)` |
| `bulb_circuit` | `brightness_extremum_label` | `label(arg_extreme(bulbs, power_in_visible_circuit, direction=brightest_or_dimmest))` |
| `switch_circuit` | `lit_bulb_count` | `count(filter(bulbs, lies_on_complete_path(bulb_edge, battery_positive, battery_negative, closed_switches)))` |
| `circuit_state_change` | `bulb_brightness_change_label` | `label(select(bulbs, brightness_change_after_switch_action(bulb)=target_change_class))` |
| `bridge_circuit` | `bridge_missing_resistance_value` | `solve_balanced_bridge_resistance(resistors_r1_r2_r3_r4, zero_meter_condition, unknown_slot)` |
| `collision` | `incoming_path_cause_choice` | `option_letter(select(candidate_incoming_paths, incoming_path_vector=target_after_motion_vector_from_impact_point))` |
| `collision` | `sticky_collision_direction_choice` | `option_letter(direction(momentum_sum(pucks_a_b), mode=final_sticky_velocity))` |
| `collision` | `sticky_collision_velocity_component_value` | `component(final_velocity(momentum_sum(pucks_a_b), combined_mass), axis=component_axis)` |
| `electrostatic_field` | `field_direction_choice` | `option_letter(direction(net_field(charges_q1_q2_q3, point_p), mode=direction_mode))` |
| `electrostatic_field` | `potential_value` | `sum(point_charge_potential(charges_q1_q2_q3, point_p, k=1))` |
| `electrostatic_field` | `zero_field_point_label` | `option_letter(select(candidate_points, net_field(charges_q1_q2, candidate_point)=zero_field))` |
| `buoyancy_density` | `object_density_value` | `liquid_density * submerged_fraction(floating_object, waterline, equal_part_marker)` |
| `fluid_flow` | `continuity_speed_value` | `solve_continuity_speed(area_1, speed_1, area_2, speed_2, unknown_speed_slot)` |
| `hydraulic` | `hydraulic_missing_value` | `solve_pascal_law(input_force, input_area, output_force, output_area, unknown_slot)` |
| `graduated_cylinder` | `volume_readout_value` | `read_scale_value(meniscus, graduated_scale, unit=mL)` |
| `graduated_cylinder` | `displacement_volume_value` | `read_scale_value(after_meniscus, graduated_scale) - read_scale_value(before_meniscus, graduated_scale)` |
| `electromagnetic_induction` | `induced_current_direction_count` | `count(filter(induction_panels, induced_current_direction(panel)=target_current_class))` |
| `free_body_forces` | `net_force_direction_choice` | `option_letter(direction(sum(applied_force_vectors)))` |
| `lever` | `side_torque_value` | `sum(weight_i * distance_i for weight_i in weights_on_queried_side)` |
| `lever` | `missing_weight_balance_value` | `solve_torque_balance(left_weight_distance_terms, right_weight_distance_terms, unknown_weight)` |
| `magnetic_force` | `force_direction_choice` | `option_letter(direction(charge_sign * cross_product(velocity_vector, magnetic_field_orientation)))` |
| `wire_magnetism` | `wire_field_direction_choice` | `option_letter(direction(right_hand_rule_around_current_wire(current_direction, point_p_side)))` |
| `gear_train` | `output_direction_label` | `direction(propagate_adjacent_mesh_reversals(input_gear_rotation, gear_count), target=marked_output_gear)` |
| `gear_train` | `output_speed_value` | `input_rpm * input_gear_tooth_count / output_gear_tooth_count` |
| `motion_graph` | `interval_displacement_value` | `area_under_velocity_time_curve(marked_interval, segment_mode=constant_velocity_or_constant_acceleration)` |
| `motion_graph` | `velocity_sign_choice` | `option_letter(classify_velocity_sign(marked_position_time_graph_interval))` |
| `motion_graph` | `speed_change_state_choice` | `option_letter(classify_speed_change(marked_velocity_time_graph_interval))` |
| `orbital_motion` | `focus_location_label` | `option_letter(select(candidate_points, point_is_focus_of_ellipse))` |
| `orbital_motion` | `orbital_speed_extremum_label` | `option_letter(arg_extreme(candidate_orbit_positions, distance_to_sun_focus, direction=nearest_or_farthest))` |
| `pulley` | `pulley_mechanical_advantage` | `solve_ideal_pulley(load_force, effort_force, support_strand_count, unknown_slot)` |
| `piston_cylinder` | `boundary_work_value` | `pressure_mpa * (final_volume_l - initial_volume_l)` |
| `pv_diagram` | `pv_work_value` | `pressure * (final_volume - initial_volume)` |
| `pv_diagram` | `pv_process_sign_choice` | `option_letter(select(candidate_processes, sign(volume_change(process))=target_sign))` |
| `thermal_mixing` | `final_temperature_value` | `average(initial_temperatures_same_liquid_equal_amounts_insulated_system)` |
| `thermometer` | `temperature_conversion_value` | `convert_temperature(read_scale_value(liquid_level, thermometer_scale, source_unit), source_unit, target_unit)` |
| `vernier_caliper` | `length_readout_value` | `read_vernier_caliper(main_scale_at_vernier_zero, aligned_vernier_tick, resolution=0.1 mm)` |
| `ray_optics` | `ray_bounce_count` | `count(reflection_points(hidden_ray_path))` |
| `ray_optics` | `ray_target_hit_count` | `count(filter(target_points, intersects(hidden_ray_path, target_point)))` |
| `refraction_layers` | `medium_speed_order_label` | `option_letter(order_by_speed(media_m1_m2_m3, inferred_from=ray_bending_at_interfaces))` |
| `shadow_cause` | `light_source_label` | `option_letter(select(candidate_light_sources, direction_from_object_to_light_source=opposite(direction_from_object_to_cast_shadow)))` |
| `lens_optics` | `image_property_choice` | `option_letter(classify_converging_lens_image_property(object_position_relative_to_focal_marks))` |
| `spring` | `spring_missing_value` | `solve_hooke_ratio(reference_weight, reference_extension, query_weight, query_extension, unknown_slot)` |
| `spring` | `spring_extension_difference` | `abs(extension_a - extension_b)` |
| `stack_stability` | `stability_status_label` | `option_letter(select(brick_stacks, center_of_mass_projection_inside_support_base=status_predicate))` |
| `wave_interference` | `interference_point_choice` | `option_letter(select(candidate_points, interference_condition(path_difference_parity, phase_relation)=target_condition))` |
| `wave_interference` | `path_difference_value` | `abs(distance(source_s1, point_p) - distance(source_s2, point_p)) / lambda_half_step` |
| `waveform_panel` | `wave_property_extremum_label` | `option_letter(arg_extreme(waveform_panels, property=amplitude_or_frequency_or_wavelength, direction=highest_or_lowest))` |
| `signal_transform` | `sinusoid_component_spectrum_match_label` | `option_letter(select(spectrum_options, spike_components=sinusoid_components(input_waveform)))` |
| `signal_transform` | `periodic_harmonic_spectrum_match_label` | `option_letter(select(spectrum_options, harmonic_pattern=periodic_wave_harmonics(input_waveform)))` |
| `signal_transform` | `pulse_width_spectrum_match_label` | `option_letter(select(spectrum_options, spectrum_lobe_width=inverse_pulse_width(input_waveform)))` |

## 4) Physics-domain policy
1. Prefer one stable diagram scaffold per task id; widen scene/query variety inside that task before adding more ids.
2. Keep arithmetic grounded in the visible diagram: if a quantity is not shown or clearly implied by the diagram, do not require it.
3. Mechanics tasks should keep vectors axis-aligned unless the task is explicitly about angled-force decomposition.
4. Prefer integer-valued constructions so answer verification stays exact and prompt-facing annotation remains local.
5. Physics visual diversity should stay non-semantic: background tints, shared technical diagram treatments, named accent palettes, layout placement, stroke variation, and the shared coordinate-preserving post-render noise policy are allowed when sampled before rendering and recorded in metadata. Any layout movement must project annotation after final placement.
6. Shared physics background variants and post-render noise live in `configs/domains/physics/base.yaml` and the shared `technical_diagram_style` layer; the default noise `apply_prob` is `0.5`.

## 5) Shared helper placement
1. Cross-domain scene/query compatibility sampling now lives in `trace/tasks/shared/variant_sampling.py`.
2. Physics-domain visual defaults belong in `trace/tasks/physics/shared/visual_defaults.py`.
3. Physics-domain normalized complexity helpers belong in `trace/tasks/physics/shared/complexity.py`.
4. Physics-domain named accent themes belong in `trace/tasks/physics/shared/style.py`.
5. Physics-domain resistor-network rendering helpers belong in `trace/tasks/physics/shared/circuit_scene.py`.
6. Physics-domain optics-board rendering helpers belong in `trace/tasks/physics/shared/optics_scene.py`.
7. Physics-domain visual option-card rendering belongs in `trace/tasks/physics/shared/option_cards.py`; tasks with answer choices drawn as lettered cards should use this helper so badge/text clearance and option bbox diagnostics remain consistent.
8. Physics-domain vector-arrow direction and bbox helpers belong in `trace/tasks/physics/shared/vector_arrows.py`; direction-choice and vector-diagram tasks should use this helper for named physics directions, screen-space endpoint projection, and conservative arrow bbox metadata.
9. Physics-domain rounded text-label tags belong in `trace/tasks/physics/shared/label_tags.py`; force labels, candidate letters, and small annotation tags should use this helper when they need padded backing boxes and bbox metadata.
10. Spring-extension, PV-diagram, and wave-interference rendering remain task-local, while sticky-collision, electrostatics field-map, magnetism force-field, buoyancy-density, hydraulic-piston, circuits, pulley, motion-graph option cards, lens-optics option cards, free-body force labels, and collision-aftermath candidate labels now use shared rendering/style helpers where available. All audited physics renderers should use the shared technical diagram style adapter unless the scene has a documented incompatibility.

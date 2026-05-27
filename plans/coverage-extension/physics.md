# Physics Coverage Extension

## Scope

This note tracks physics-domain coverage gaps found from the external benchmark
failure analysis, then records candidate changes for `physics`.

Current working conclusion: the physics domain already has a useful canonical
diagram base, but it is still narrow compared with external exam-style
benchmarks. Active tasks cover lever torque and missing weights, ideal pulleys,
spring extension, sticky collisions, equivalent resistance, missing resistor
values, electrostatic field direction, zero-field points, electric potential,
magnetic force direction, hydraulic piston missing values, mirror ray tracing,
PV work/sign, and two-source wave interference. The remaining benchmark gaps
are mostly about broader mechanics force diagrams, energy/work, richer
circuits/electronics, refraction/lenses, engineering mechanisms, and
physics-diagram styling.

Relevant benchmark cues:

- MMMU-ProVis: broad physics, electronics, energy/power, mechanical
  engineering, architecture/engineering, and materials questions. The curated
  review marks physics/electronics/energy/mechanical engineering diagrams as
  `partial`: TRACE covers canonical synthetic diagrams, but not the wider
  engineering imagery.
- MathVista TestMini: geometry/physics arithmetic and math-targeted diagrams,
  including a spring-compression/work example.
- MathVision: arithmetic constraints and balance/weight puzzles, plus
  contest-style diagrams that sometimes cross into mechanics.
- ERQA: action effects, robot trajectories, contact, gripper state, and
  spatial/mechanical consequences. These are related to physics but usually
  need a robotics/manipulation scene rather than a plain physics diagram.
- BLINK and EmbSpatial: depth, spatial relation, reflectance, and multi-view
  matching. These are mostly `three_d` or `illustrations` unless the task is a
  controlled optics/material diagram.

Boundary rule:

- Put a task in `physics` when the answer depends on a visible synthetic
  physical setup plus an explicitly modeled law: forces, torque, work, energy,
  motion, circuits, fields, fluids, optics, heat, waves, or mechanism state.
- Put it in `geometry` when the answer is purely a mathematical measure or
  construction with no physical law.
- Put it in `charts` when the source of truth is ordinary chart reading rather
  than a physical model, even if the axes are physical units. Use `physics`
  only when physical interpretation or a physics formula is part of the
  verifier contract.
- Put it in `three_d` when the primary source of truth is camera viewpoint,
  3D spatial relation, physical depth, or rendered object pose.
- Put embodied gripper actions, robot trajectories, task progress, and object
  manipulation into a future robotics scene, likely under `three_d`, unless the
  image is a simplified 2D physics diagram with metadata-defined actions.
- Keep open science, materials diagnosis, medicine, biology, agriculture, and
  factual engineering knowledge out of `physics` unless the answer is fully
  grounded in the visible diagram metadata.

## Current Physics Surface

Closest active scene families:

- Lever balance diagrams with center/offset fulcrums and textured beams.
- Ideal pulley block diagrams.
- Paired spring diagrams with extension markers.
- Sticky-collision tabletop diagrams with masses, velocities, and candidate
  final arrows.
- Series/parallel resistor circuits.
- Electrostatics field maps with point charges, candidate arrows, candidate
  zero-field points, and potential witness regions.
- Magnetism force-field cards with charge sign, velocity, magnetic-field
  orientation, and candidate force arrows.
- Hydraulic piston systems.
- Mirror-board ray tracing scenes.
- PV diagrams for work and process-sign selection.
- Wave-interference tanks with source phase, rings, candidate points, and
  path-difference guides.

Closest active task families:

- Mechanics: torque, balance, pulley mechanical advantage, spring missing
  value, spring extension difference, sticky-collision direction, and
  sticky-collision velocity component.
- Circuits: total resistance and missing resistor value.
- Electrostatics/magnetism: field direction, zero-field point, potential
  value, and magnetic-force direction.
- Fluids: hydraulic missing force or piston area.
- Optics: ray bounce count and target-hit count.
- Thermodynamics: PV work value and PV process-sign choice.
- Waves: interference point choice and path-difference value.

## Identified Issues

### P1. Exam-Style Physics Diagram Breadth

Status: `partial`

MMMU-ProVis and MathVista include textbook and exam diagrams that mix labels,
subfigures, answer choices, annotations, and distractor measurements. TRACE
physics tasks are clean, canonical, and task-specific.

Closest existing tasks:

- `proposal:physics/circuits/total_resistance_value`
- `proposal:physics/mechanics/side_torque_value`
- `proposal:physics/magnetism/force_direction_choice`
- `proposal:physics/waves/path_difference_value`
- `proposal:physics/thermodynamics/pv_process_sign_choice`

Interpretation:

- Many failures are not missing laws; they are broader diagram grammar and
  presentation.
- Add style and layout variation carefully: worksheet cards, answer-option
  panels, extra non-operative labels, inset diagrams, and light distractor
  annotations are useful, but the operative evidence must stay local and
  readable.
- Do not require unstated textbook knowledge beyond the law encoded by the
  task.

### P2. Free-Body, Force Balance, And Inclined-Plane Mechanics

Status: `gap / partial`

Current mechanics coverage has levers, pulleys, springs, and sticky collisions,
but not general force diagrams. External physics and engineering questions
often ask about net force, acceleration direction, friction, tension, normal
force, or components on an incline.

Closest existing tasks:

- `proposal:physics/mechanics/side_torque_value`
- `proposal:physics/mechanics/missing_weight_balance_value`
- `proposal:physics/mechanics/pulley_mechanical_advantage`
- `proposal:physics/mechanics/sticky_collision_direction_choice`

Interpretation:

- This is the main mechanics gap.
- First versions should stay integer-valued and axis-aligned where possible:
  horizontal pulls, vertical weights, simple ramps with small integer
  components, and one marked unknown.
- Evidence should be force arrows, labels, support/contact marks, and the
  marked object, not the full decorative scene.

### P3. Work, Energy, And Spring Compression

Status: `partial`

MathVista includes spring work/compression questions, and MathVision includes
balance/weight or constraint puzzles that sometimes use energy-like reasoning.
TRACE has spring extension and force balance, but not work-energy or
area-under-force reasoning.

Closest existing tasks:

- `proposal:physics/mechanics/spring_missing_value`
- `proposal:physics/mechanics/spring_extension_difference`
- `proposal:physics/mechanics/missing_weight_balance_value`
- `proposal:geometry/measurement/pythagorean_length_value`

Interpretation:

- Spring work is a natural extension of the spring scene, but it should be
  kept simple: visible `k`, visible compression, and integer or small rational
  answer support.
- Work-energy scenes should avoid long derivations. Good first contracts ask
  for work by a constant force, change in gravitational potential energy, or
  spring work from a visible force-displacement graph.

### P4. Kinematics, Motion Graphs, And Projectile Diagrams

Status: `gap / boundary-sensitive`

Physics benchmarks often include position-time, velocity-time, acceleration,
projectile, circular-motion, or relative-motion diagrams. TRACE currently has
sticky collision motion but no general kinematics task family.

Closest existing tasks:

- `proposal:physics/mechanics/sticky_collision_direction_choice`
- `proposal:physics/mechanics/sticky_collision_velocity_component_value`
- `proposal:charts/scientific/curve_intersection_count`
- `proposal:geometry/graphing/extremum_count`

Interpretation:

- Pure chart readout over a motion graph should stay in `charts`.
- Physics-owned motion graphs should require physical interpretation such as
  displacement from signed area, acceleration sign from slope, or final
  velocity from a visible constant acceleration setup.
- Projectile scenes should start with discrete candidate landing labels rather
  than free-form continuous coordinates.

### P5. Circuit And Electronics Reasoning Beyond Equivalent Resistance

Status: `partial`

MMMU-ProVis includes electronics and energy/power subjects. TRACE circuits
currently cover resistor equivalence and missing resistor values, but not
voltage/current/power, switch states, bulbs, meters, or basic Kirchhoff-style
reasoning.

Closest existing tasks:

- `proposal:physics/circuits/total_resistance_value`
- `proposal:physics/circuits/missing_resistor_value`

Interpretation:

- This is a strong next-wave gap because it reuses circuit rendering
  infrastructure.
- Keep the first versions small: one battery, simple series/parallel blocks,
  visible ammeter/voltmeter readings, and integer Ohm's-law values.
- Avoid open electronics schematics, component recognition, and real circuit
  debugging unless every component and rule is metadata-defined.

### P6. Electromagnetism And Induction

Status: `partial`

Current electromagnetism coverage includes electrostatic field direction,
zero-field point, potential, and magnetic force on a charge. MMMU-ProVis
physics examples include induction/Faraday-style reasoning and broader field
diagrams.

Closest existing tasks:

- `proposal:physics/electrostatics/field_direction_choice`
- `proposal:physics/electrostatics/zero_field_point_label`
- `proposal:physics/electrostatics/potential_value`
- `proposal:physics/magnetism/force_direction_choice`

Interpretation:

- Current field tasks cover vector direction, but not changing flux, induced
  current, wire force, solenoids, or field-line density comparisons.
- First induction tasks should use option labels and visible change arrows so
  the verifier does not depend on implicit text knowledge.

### P7. Optics Beyond Mirror Ray Tracing

Status: `partial`

BLINK has reflectance and visual correspondence, while MMMU-ProVis physics
examples include speed of light in media and optics-style diagrams. Current
TRACE optics covers mirror-board ray tracing only.

Closest existing tasks:

- `proposal:physics/optics/ray_bounce_count`
- `proposal:physics/optics/ray_target_hit_count`
- `proposal:three_d/spatial/camera_distance_extremum_label`

Interpretation:

- Reflection ray tracing is covered, but refraction, lenses, shadows, and image
  formation are gaps.
- Relative reflectance/albedo in natural images should stay in `three_d` or
  `illustrations` unless we synthesize a controlled optics/material diagram.
- First optics additions should use labeled media, simple Snell-law ratios, or
  lens-ray construction with a single option label.

### P8. Fluids Beyond Hydraulics

Status: `partial`

TRACE has hydraulic piston reasoning, but fluids benchmarks can include
pressure with depth, buoyancy, connected vessels, flow continuity, or manometer
readouts.

Closest existing tasks:

- `proposal:physics/fluids/hydraulic_missing_value`

Interpretation:

- Add one or two static-fluid scenes before dynamic flow.
- Good first contracts: pressure difference from depth, buoyant force from
  displaced volume, float/sink option, connected-vessel level comparison, and
  manometer pressure difference.

### P9. Thermodynamics Beyond PV Work

Status: `partial`

Current thermodynamics coverage is PV work and process-sign selection. External
physics/science diagrams may involve heat flow, calorimetry, ideal gas state
changes, phase changes, or heat engines.

Closest existing tasks:

- `proposal:physics/thermodynamics/pv_work_value`
- `proposal:physics/thermodynamics/pv_process_sign_choice`

Interpretation:

- PV diagrams are covered for a narrow query set.
- Good first expansions are ideal-gas missing state values, heat-flow direction
  between labeled temperatures, calorimetry with small integer heat capacities,
  and phase-change segment labels.
- Open chemistry/materials diagnosis should remain out of scope.

### P10. Waves Beyond Two-Source Interference

Status: `partial`

Current wave coverage handles two-source interference point selection and path
difference. Physics benchmarks may include wavelength/frequency/speed,
standing waves, string harmonics, sound pitch, or Doppler-like diagrams.

Closest existing tasks:

- `proposal:physics/waves/interference_point_choice`
- `proposal:physics/waves/path_difference_value`

Interpretation:

- The scene grammar for waves exists, but query breadth is narrow.
- Add simple scalar relations first: `v = f lambda`, harmonic/node counts, and
  standing-wave wavelength from a drawn string.
- Doppler should wait until the diagram vocabulary is clear enough to avoid
  relying on memorized qualitative rules alone.

### P11. Engineering Mechanisms And Machines

Status: `gap / partial`

MMMU-ProVis includes mechanical engineering and energy/power. Current physics
mechanics has levers and pulleys, but not gears, belts, cams, linkages,
supports, trusses, or simple machines beyond the existing pulley scene.

Closest existing tasks:

- `proposal:physics/mechanics/pulley_mechanical_advantage`
- `proposal:physics/mechanics/side_torque_value`
- `proposal:puzzles/spatial/sokoban_path_sequence_label`

Interpretation:

- Gear trains and simple mechanisms fit `physics/mechanics` if the source of
  truth is mechanical state, direction, ratio, or force transfer.
- Structural truss/support diagrams are boundary-sensitive: pure geometry goes
  to `geometry`; force/torque equilibrium goes to `physics`.
- Avoid real-world engineering recognition unless the schematic is fully
  synthetic and labeled.

### P12. Robotics And Embodied Manipulation

Status: `gap`, but not primarily physics-owned.

ERQA failures involve robot grippers, camera motion, contact, grasp state, and
trajectory outcomes. Physics has collision and force tasks, but it does not
model embodied manipulation or multi-step action effects.

Closest existing tasks:

- `proposal:physics/mechanics/sticky_collision_direction_choice`
- `proposal:three_d/spatial/object_relation_label`
- `proposal:pages/process/flow_condition_path_endpoint_label`

Interpretation:

- Add a robotics/manipulation scene only if embodied evaluation becomes a
  priority.
- That scene likely belongs under `three_d`, with physics-inspired metadata for
  contact, trajectory, and object state.
- Do not fold full robotics into current 2D physics diagrams.

### P13. Broad Science And Domain Knowledge

Status: `out_of_scope / neighboring-domain`

MMMU-ProVis includes agriculture, biology, medicine, chemistry, materials, and
other knowledge-heavy visual questions. Some are scientific, but they are not
physics tasks unless the answer follows from visible physical quantities and a
synthetic rule.

Closest existing tasks:

- `proposal:physics/thermodynamics/pv_process_sign_choice`
- `proposal:physics/electrostatics/field_direction_choice`
- `proposal:charts/scientific/curve_intersection_count`

Interpretation:

- Keep visual diagnosis, species/material recognition, lab medicine, chemistry
  reactions, and open subject expertise out of physics.
- If needed later, create separate science-diagram scenes with explicit
  metadata, rather than stretching physics.

## Candidate Changes

### C1. Physics Worksheet And Exam-Style Rendering

Add renderer/style variation that can apply to several existing physics scenes:
worksheet panels, option boxes, light grid paper, inset diagrams, visible
formula cards when the formula is part of the task contract, and harmless
distractor labels. Keep evidence local to the operative physical objects.

Addresses: P1.

### C2. Free-Body Force Diagram Scene

Add a reusable mechanics scene for one marked object with force arrows, support
surfaces, friction arrows, tension arrows, and one unknown. Start with small
integer values and axis-aligned or simple incline components.

Candidate tasks:

- `proposal:physics/mechanics/net_force_component_value`
- `proposal:physics/mechanics/acceleration_direction_choice`
- `proposal:physics/mechanics/friction_force_value`
- `proposal:physics/mechanics/tension_value`
- `proposal:physics/mechanics/normal_force_value`

Addresses: P2.

### C3. Work And Energy Scene

Add simple work-energy diagrams with visible distances, force labels, spring
compression, and height changes. Prefer integer work/energy outputs and avoid
multi-formula chains.

Candidate tasks:

- `proposal:physics/mechanics/constant_force_work_value`
- `proposal:physics/mechanics/spring_work_value`
- `proposal:physics/mechanics/gravitational_energy_change_value`
- `proposal:physics/mechanics/work_energy_final_speed_value`

Addresses: P3.

### C4. Motion Graph And Kinematics Scene

Add a physics-owned motion scene only when the query needs physical
interpretation beyond chart readout. Reuse chart-like rendering patterns where
possible, but keep the task under physics when the verifier computes kinematic
quantities.

Candidate tasks:

- `proposal:physics/mechanics/motion_graph_displacement_value`
- `proposal:physics/mechanics/motion_graph_acceleration_sign_choice`
- `proposal:physics/mechanics/constant_acceleration_missing_value`
- `proposal:physics/mechanics/projectile_landing_label`

Addresses: P4.

### C5. Circuit Voltage, Current, Power, And Switches

Extend the circuit scene to include batteries, meters, bulbs, switches, and
query-specific highlighted branches. Keep first versions to one or two
applications of Ohm's law.

Candidate tasks:

- `proposal:physics/circuits/branch_current_value`
- `proposal:physics/circuits/resistor_voltage_value`
- `proposal:physics/circuits/power_dissipation_value`
- `proposal:physics/circuits/missing_voltage_value`
- `proposal:physics/circuits/switch_bulb_state_count`

Addresses: P5.

### C6. Induction And Wire-Force Diagrams

Add a small electromagnetic induction/force family with visible magnetic-field
orientation, loop motion or flux-change arrows, and candidate current/force
directions.

Candidate tasks:

- `proposal:physics/magnetism/wire_force_direction_choice`
- `proposal:physics/magnetism/induced_current_direction_choice`
- `proposal:physics/magnetism/flux_change_sign_choice`
- `proposal:physics/magnetism/field_strength_extremum_label`

Addresses: P6.

### C7. Refraction, Lens, And Shadow Optics

Extend optics beyond mirror boards. Use labeled media, simple refractive-index
ratios, lenses with focal points, and object/screen diagrams.

Candidate tasks:

- `proposal:physics/optics/refraction_exit_label`
- `proposal:physics/optics/lens_image_side_label`
- `proposal:physics/optics/lens_ray_target_label`
- `proposal:physics/optics/shadow_length_value`
- `proposal:physics/optics/medium_speed_rank_label`

Addresses: P7.

### C8. Static Fluids Scene

Add static-fluid diagrams before dynamic-flow diagrams: tanks with labeled
depths, submerged blocks, connected vessels, and manometers.

Candidate tasks:

- `proposal:physics/fluids/pressure_depth_difference_value`
- `proposal:physics/fluids/buoyant_force_value`
- `proposal:physics/fluids/float_sink_label`
- `proposal:physics/fluids/connected_vessel_level_label`
- `proposal:physics/fluids/manometer_pressure_difference_value`

Addresses: P8.

### C9. Heat And Ideal-Gas Scene

Add simple thermodynamics diagrams that are not PV-work only: gas-state tables
paired with piston drawings, heat-flow cards, phase-change curves, and
calorimetry containers.

Candidate tasks:

- `proposal:physics/thermodynamics/ideal_gas_missing_value`
- `proposal:physics/thermodynamics/heat_flow_direction_choice`
- `proposal:physics/thermodynamics/calorimetry_temperature_value`
- `proposal:physics/thermodynamics/phase_segment_label`

Addresses: P9.

### C10. Standing-Wave And Wave-Speed Scene

Extend wave coverage to scalar wave relations and standing-wave diagrams.

Candidate tasks:

- `proposal:physics/waves/speed_missing_value`
- `proposal:physics/waves/frequency_wavelength_value`
- `proposal:physics/waves/standing_wave_node_count`
- `proposal:physics/waves/harmonic_label`

Addresses: P10.

### C11. Gear And Simple-Mechanism Scene

Add synthetic mechanical linkage diagrams for direction and ratio transfer.
This should stay schematic, metadata-backed, and visually simple.

Candidate tasks:

- `proposal:physics/mechanics/gear_rotation_direction_choice`
- `proposal:physics/mechanics/gear_speed_ratio_value`
- `proposal:physics/mechanics/belt_rotation_direction_choice`
- `proposal:physics/mechanics/compound_machine_mechanical_advantage_value`

Addresses: P11.

### C12. Keep Neighboring Gaps Out Of Physics

Do not solve these inside current `physics`:

- Full robot gripper trajectory and action-effect prediction: future robotics
  scene, likely `three_d`.
- Natural-image spatial relation, depth, and recognition: `three_d` or
  `illustrations`.
- Broad science diagnosis, materials recognition, medicine, agriculture, and
  chemistry knowledge: future science-specific domains/scenes only if
  metadata-grounded.
- Pure chart readout of physical data: `charts`.
- Pure mathematical geometry of a physics-looking figure: `geometry`.

Addresses: P12, P13.

## Suggested First Wave

1. Add a free-body force diagram scene with
   `proposal:physics/mechanics/net_force_component_value` and
   `proposal:physics/mechanics/acceleration_direction_choice`.
2. Add one spring/work-energy task, preferably
   `proposal:physics/mechanics/spring_work_value`, because it directly extends the
   existing spring scene and maps to MathVista-style failures.
3. Extend circuits with `proposal:physics/circuits/branch_current_value` or
   `proposal:physics/circuits/resistor_voltage_value`.
4. Add one refraction/lens optics task, preferably
   `proposal:physics/optics/refraction_exit_label` or
   `proposal:physics/optics/medium_speed_rank_label`.
5. Add worksheet/exam-style rendering variants across selected existing
   physics tasks after the task logic is stable, so current coverage gains
   visual breadth without changing every verifier contract at once.

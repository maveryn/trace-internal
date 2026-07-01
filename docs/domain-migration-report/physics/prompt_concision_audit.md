# Prompt Concision Audit

- rendered prompts: `148`
- tasks covered: `50`
- observed query ids covered: `74`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_physics__analog_meter__meter_readout_value | `ammeter_readout, voltmeter_readout` | `{'ammeter_readout': 1, 'voltmeter_readout': 1}` | 2 | `` |
| task_physics__bridge_circuit__bridge_missing_resistance_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__bulb_circuit__brightness_extremum_label | `brightest_bulb_label, dimmest_bulb_label` | `{'brightest_bulb_label': 1, 'dimmest_bulb_label': 1}` | 2 | `` |
| task_physics__buoyancy_density__object_density_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__circuit_equivalent__total_capacitance_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__circuit_equivalent__total_resistance_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__circuit_state_change__bulb_brightness_change_label | `brightens_after_switch_change, dims_after_switch_change, turns_off_after_switch_change, turns_on_after_switch_change` | `{'brightens_after_switch_change': 1, 'dims_after_switch_change': 1, 'turns_off_after_switch_change': 1, 'turns_on_after_switch_change': 1}` | 4 | `` |
| task_physics__collision__sticky_collision_direction_choice | `single` | `{'single': 1}` | 2 | `` |
| task_physics__collision__sticky_collision_speed_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__electromagnetic_induction__induced_current_direction_count | `clockwise_induced_current_count, counterclockwise_induced_current_count, no_induced_current_count` | `{'clockwise_induced_current_count': 1, 'counterclockwise_induced_current_count': 1, 'no_induced_current_count': 1}` | 3 | `` |
| task_physics__electrostatic_field__field_direction_choice | `electric_field_direction, force_on_negative_charge, force_on_positive_charge` | `{'electric_field_direction': 1, 'force_on_negative_charge': 1, 'force_on_positive_charge': 1}` | 3 | `` |
| task_physics__electrostatic_field__potential_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__electrostatic_field__zero_field_point_label | `single` | `{'single': 1}` | 2 | `` |
| task_physics__fluid_flow__continuity_speed_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__free_body_forces__net_force_direction_choice | `single` | `{'single': 1}` | 2 | `` |
| task_physics__gear_train__output_direction_label | `single` | `{'single': 1}` | 2 | `` |
| task_physics__gear_train__output_speed_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__graduated_cylinder__displacement_volume_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__graduated_cylinder__volume_readout_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__hydraulic__hydraulic_missing_value | `missing_input_area, missing_input_force, missing_output_force, missing_piston_area` | `{'missing_input_area': 1, 'missing_input_force': 1, 'missing_output_force': 1, 'missing_piston_area': 1}` | 4 | `` |
| task_physics__lens_optics__image_property_choice | `single` | `{'single': 1}` | 2 | `` |
| task_physics__lever__missing_weight_balance_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__lever__side_torque_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__magnetic_force__force_direction_choice | `single` | `{'single': 1}` | 2 | `` |
| task_physics__manometer__pressure_difference_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__motion_graph__average_speed_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__motion_graph__interval_displacement_value | `constant_acceleration_interval_displacement, constant_velocity_interval_displacement` | `{'constant_acceleration_interval_displacement': 1, 'constant_velocity_interval_displacement': 1}` | 2 | `` |
| task_physics__motion_graph__speed_change_state_choice | `single` | `{'single': 1}` | 2 | `` |
| task_physics__orbital_motion__focus_location_label | `single` | `{'single': 1}` | 2 | `` |
| task_physics__orbital_motion__orbital_speed_extremum_label | `greatest_speed_position_label, least_speed_position_label` | `{'greatest_speed_position_label': 1, 'least_speed_position_label': 1}` | 2 | `` |
| task_physics__piston_cylinder__boundary_work_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__pulley__pulley_mechanical_advantage | `missing_effort_force_value, missing_load_force_value` | `{'missing_effort_force_value': 1, 'missing_load_force_value': 1}` | 2 | `` |
| task_physics__pv_diagram__pv_process_sign_choice | `single` | `{'single': 1}` | 2 | `` |
| task_physics__pv_diagram__pv_work_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__ray_optics__ray_bounce_count | `single` | `{'single': 1}` | 2 | `` |
| task_physics__ray_optics__ray_target_hit_count | `single` | `{'single': 1}` | 2 | `` |
| task_physics__refraction_layers__medium_speed_order_label | `single` | `{'single': 1}` | 2 | `` |
| task_physics__shadow_cause__light_source_label | `single` | `{'single': 1}` | 2 | `` |
| task_physics__signal_transform__periodic_harmonic_spectrum_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_physics__spring__spring_extension_difference | `single` | `{'single': 1}` | 2 | `` |
| task_physics__spring__spring_missing_value | `missing_extension_for_weight, missing_weight_for_extension` | `{'missing_extension_for_weight': 1, 'missing_weight_for_extension': 1}` | 2 | `` |
| task_physics__stack_stability__stability_status_label | `stable_stack_label, tipping_stack_label` | `{'stable_stack_label': 1, 'tipping_stack_label': 1}` | 2 | `` |
| task_physics__switch_circuit__lit_bulb_count | `single` | `{'single': 1}` | 2 | `` |
| task_physics__thermal_mixing__final_temperature_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__thermometer__temperature_conversion_value | `celsius_to_fahrenheit_value, fahrenheit_to_celsius_value` | `{'celsius_to_fahrenheit_value': 1, 'fahrenheit_to_celsius_value': 1}` | 2 | `` |
| task_physics__vernier_caliper__length_readout_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__wave_interference__interference_point_choice | `constructive_interference_point_choice, destructive_interference_point_choice` | `{'constructive_interference_point_choice': 1, 'destructive_interference_point_choice': 1}` | 2 | `` |
| task_physics__wave_interference__path_difference_value | `single` | `{'single': 1}` | 2 | `` |
| task_physics__waveform_panel__wave_property_extremum_label | `highest_amplitude_label, highest_frequency_label, longest_wavelength_label, lowest_amplitude_label, lowest_frequency_label, shortest_wavelength_label` | `{'highest_amplitude_label': 1, 'highest_frequency_label': 1, 'longest_wavelength_label': 1, 'lowest_amplitude_label': 1, 'lowest_frequency_label': 1, 'shortest_wavelength_label': 1}` | 6 | `` |
| task_physics__wire_magnetism__wire_field_direction_choice | `single` | `{'single': 1}` | 2 | `` |

## Longest Prompts

### task_physics__circuit_state_change__bulb_brightness_change_label / answer_and_annotation / sample 3205996959760868

- `query_id`: `turns_off_after_switch_change`
- `instance_seed`: `3205996959760868`
- `word_count`: `136`
- `body_word_count`: `37`

```text
This circuit diagram shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. Using the bulb resistances and topology, which bulb is on before the switch action and off afterward?
Annotation format: set "annotation" to an object mapping "changed_switch" and each visible bulb label B1 through B5 to one [x0,y0,x1,y1] pixel box around the switch action cue and each bulb symbol with its resistance label.
Format for the "answer" field: set "answer" to the label of the bulb that turns off after the switch action as a string, for example "B2".
Example JSON:
{"annotation":{"changed_switch":[40,40,120,95],"B1":[130,40,210,120],"B2":[220,40,300,120],"B3":[310,40,390,120],"B4":[400,40,480,120],"B5":[490,40,570,120]},"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / answer_and_annotation / sample 2253101174342736

- `query_id`: `dims_after_switch_change`
- `instance_seed`: `2253101174342736`
- `word_count`: `131`
- `body_word_count`: `32`

```text
The visual shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. Select the label of the bulb that dims after the shown switch action.
Annotation format: set "annotation" to an object mapping "changed_switch" and each visible bulb label B1 through B5 to one [x0,y0,x1,y1] pixel box around the switch action cue and each bulb symbol with its resistance label.
Format for the "answer" field: set "answer" to the label of the bulb that becomes dimmer after the switch action as a string, for example "B2".
Example JSON:
{"annotation":{"changed_switch":[40,40,120,95],"B1":[130,40,210,120],"B2":[220,40,300,120],"B3":[310,40,390,120],"B4":[400,40,480,120],"B5":[490,40,570,120]},"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / answer_and_annotation / sample 298454826081349

- `query_id`: `brightens_after_switch_change`
- `instance_seed`: `298454826081349`
- `word_count`: `127`
- `body_word_count`: `30`

```text
The image shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. After the red-boxed switch action occurs, which labeled bulb becomes brighter?
Final answer format: set "answer" to the label of the bulb that becomes brighter after the switch action as a string, for example "B2".
Annotation format: set "annotation" to an object mapping "changed_switch" and each visible bulb label B1 through B5 to one [x0,y0,x1,y1] pixel box around the switch action cue and each bulb symbol with its resistance label.
Example JSON:
{"annotation":{"changed_switch":[40,40,120,95],"B1":[130,40,210,120],"B2":[220,40,300,120],"B3":[310,40,390,120],"B4":[400,40,480,120],"B5":[490,40,570,120]},"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / answer_and_annotation / sample 1196983518433529

- `query_id`: `turns_on_after_switch_change`
- `instance_seed`: `1196983518433529`
- `word_count`: `126`
- `body_word_count`: `30`

```text
The image shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. After the red-boxed switch action occurs, which labeled bulb turns on?
Answer format: set "answer" to the label of the bulb that turns on after the switch action as a string, for example "B2".
Annotation format: set "annotation" to an object mapping "changed_switch" and each visible bulb label B1 through B5 to one [x0,y0,x1,y1] pixel box around the switch action cue and each bulb symbol with its resistance label.
Example JSON:
{"annotation":{"changed_switch":[40,40,120,95],"B1":[130,40,210,120],"B2":[220,40,300,120],"B3":[310,40,390,120],"B4":[400,40,480,120],"B5":[490,40,570,120]},"answer":"B2"}
```

### task_physics__piston_cylinder__boundary_work_value / answer_and_annotation / sample 318230679367448

- `query_id`: `single`
- `instance_seed`: `318230679367448`
- `word_count`: `123`
- `body_word_count`: `51`

```text
The piston-cylinder diagram shows a piston-cylinder apparatus shown in initial and final states, with constant pressure in MPa, initial and final volumes in liters, and a process arrow. Compute the signed boundary work for the constant-pressure piston process. Use W = P x (V_final - V_initial) and 1 MPa x L = 1 kJ.
Annotation format: set "annotation" to an object with keys "pressure_readout", "initial_cylinder", and "final_cylinder", each mapped to one [x0,y0,x1,y1] pixel box.
Format for the "answer" field: set "answer" to the signed integer boundary work in kJ, using work done by the gas as positive.
Example JSON:
{"annotation":{"pressure_readout":[2.5,3,4.5,5],"initial_cylinder":[3,4.5,5,6],"final_cylinder":[4.5,5.5,6.5,7]},"answer":8}
```

### task_physics__vernier_caliper__length_readout_value / answer_and_annotation / sample 4548728908108208

- `query_id`: `single`
- `instance_seed`: `4548728908108208`
- `word_count`: `111`
- `body_word_count`: `46`

```text
The figure shows a Vernier caliper measuring an object, with a main scale in millimeters, a sliding vernier scale, and a 0.1 mm vernier resolution. Use the main millimeter scale and the aligned vernier tick to read the caliper. What length is shown in mm?
Format for the "annotation" field: set "annotation" to an object with keys "vernier_zero_tick" and "aligned_vernier_tick", each mapped to one [x,y] pixel point at the center of that tick mark.
Format for the "answer" field: set "answer" to the measured length in millimeters as a number with one decimal place and no unit.
Example JSON:
{"annotation":{"vernier_zero_tick":[410,356],"aligned_vernier_tick":[456,358]},"answer":23.4}
```

### task_physics__collision__sticky_collision_direction_choice / answer_and_annotation / sample 3427639663144369

- `query_id`: `single`
- `instance_seed`: `3427639663144369`
- `word_count`: `107`
- `body_word_count`: `48`

```text
The diagram shows a collision table with puck A moving horizontally, puck B moving vertically, visible mass and speed labels, a stuck A+B puck, signed axes, and four candidate direction arrows. The pucks stick at the center. Which labeled candidate arrow shows the direction they move afterward?
Annotation format: set "annotation" to an array of two line segments, each written as [[x0,y0],[x1,y1]], for puck A's motion arrow and puck B's motion arrow.
Answer format: set "answer" to the option letter A, B, C, or D of the correct candidate arrow.
Example JSON:
{"annotation":[[[176,304],[366,304]],[[436,158],[436,254]]],"answer":"D"}
```

### task_physics__collision__sticky_collision_speed_value / answer_and_annotation / sample 5096128980181968

- `query_id`: `single`
- `instance_seed`: `5096128980181968`
- `word_count`: `107`
- `body_word_count`: `49`

```text
This diagram shows a compact collision table with puck A moving horizontally, puck B moving vertically, visible mass and speed labels, a stuck A+B puck, and signed axes. Using the shown masses, speeds, and approach directions, what is the stuck pucks' final speed rounded to one decimal place?
Annotation format: set "annotation" to an array of two line segments, each written as [[x0,y0],[x1,y1]], for puck A's motion arrow and puck B's motion arrow.
Answer format: set "answer" to the final speed in m/s rounded to one decimal place.
Example JSON:
{"annotation":[[[176,304],[366,304]],[[436,158],[436,254]]],"answer":5.0}
```

### task_physics__free_body_forces__net_force_direction_choice / answer_and_annotation / sample 6016879397434784

- `query_id`: `single`
- `instance_seed`: `6016879397434784`
- `word_count`: `105`
- `body_word_count`: `35`

```text
The image shows one object with several labeled applied force arrows and eight labeled candidate net-force direction arrows. From the visible force arrows and magnitude labels, choose the candidate arrow showing the net force direction.
Annotation format: set "annotation" to an object with "force_diagram" as the [x0,y0,x1,y1] pixel box around the object, applied force arrows, and magnitude labels, and "selected_candidate" as the box around the selected candidate arrow option cell.
Answer format: set "answer" to the option letter of the candidate arrow showing the net force direction.
Example JSON:
{"annotation":{"force_diagram":[90,120,520,430],"selected_candidate":[450,610,570,700]},"answer":"C"}
```

### task_physics__circuit_equivalent__total_capacitance_value / answer_and_annotation / sample 3550618771244141

- `query_id`: `single`
- `instance_seed`: `3550618771244141`
- `word_count`: `103`
- `body_word_count`: `43`

```text
The circuit diagram shows one capacitor circuit between terminals A and B with at least one labeled parallel-plate capacitor in series with one or two labeled parallel capacitor blocks. Read the circuit between terminals A and B. What is its total equivalent capacitance?
Answer format: set "answer" to the total equivalent capacitance between terminals A and B as an integer number of microfarads.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the full capacitor network between terminals A and B, including the component symbols, value labels, and connecting wires.
Example JSON:
{"annotation":[90,120,760,520],"answer":8}
```

### task_physics__hydraulic__hydraulic_missing_value / answer_and_annotation / sample 2553155137309841

- `query_id`: `missing_input_area`
- `instance_seed`: `2553155137309841`
- `word_count`: `101`
- `body_word_count`: `38`

```text
The image shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. The connected fluid transmits equal pressure. What integer input piston area belongs at the marked red `?`?
Annotation format: set "annotation" to an object with keys "input_side" and "output_side"; each value is a [x0,y0,x1,y1] pixel box around the corresponding piston side, including its force label, chamber, and area label.
Answer format: set "answer" to the requested integer piston area in cm^2.
Example JSON:
{"annotation":{"input_side":[120,70,340,562],"output_side":[760,70,980,562]},"answer":6}
```

### task_physics__hydraulic__hydraulic_missing_value / answer_and_annotation / sample 8458915069719234

- `query_id`: `missing_input_force`
- `instance_seed`: `8458915069719234`
- `word_count`: `101`
- `body_word_count`: `38`

```text
The figure shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. Use the shown output force and piston areas. What input force is required at the red `?`?
Final answer format: set "answer" to the requested integer force value in newtons.
Annotation format: set "annotation" to an object with keys "input_side" and "output_side"; each value is a [x0,y0,x1,y1] pixel box around the corresponding piston side, including its force label, chamber, and area label.
Example JSON:
{"annotation":{"input_side":[120,70,340,562],"output_side":[760,70,980,562]},"answer":8}
```

### task_physics__hydraulic__hydraulic_missing_value / answer_and_annotation / sample 1188507802227299

- `query_id`: `missing_piston_area`
- `instance_seed`: `1188507802227299`
- `word_count`: `101`
- `body_word_count`: `35`

```text
This diagram shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. Using Pascal's law, what output piston area should replace the marked red `?` label?
Annotation format: set "annotation" to an object with keys "input_side" and "output_side"; each value is a [x0,y0,x1,y1] pixel box around the corresponding piston side, including its force label, chamber, and area label.
Format for the "answer" field: set "answer" to the requested integer piston area in cm^2.
Example JSON:
{"annotation":{"input_side":[120,70,340,562],"output_side":[760,70,980,562]},"answer":30}
```

### task_physics__circuit_equivalent__total_resistance_value / answer_and_annotation / sample 2605469048287086

- `query_id`: `single`
- `instance_seed`: `2605469048287086`
- `word_count`: `100`
- `body_word_count`: `37`

```text
The figure shows one resistor circuit between terminals A and B with at least one labeled zigzag resistor in series with one or two labeled parallel resistor blocks. Determine the network's total resistance between A and B.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the full resistor network between terminals A and B, including the component symbols, value labels, and connecting wires.
Format for the "answer" field: set "answer" to the total equivalent resistance between terminals A and B as an integer number of ohms.
Example JSON:
{"annotation":[90,120,760,520],"answer":8}
```

### task_physics__hydraulic__hydraulic_missing_value / answer_and_annotation / sample 7037654664443469

- `query_id`: `missing_output_force`
- `instance_seed`: `7037654664443469`
- `word_count`: `99`
- `body_word_count`: `37`

```text
The diagram shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. What force on the output piston corresponds to the shown input force and piston areas?
Annotation format: set "annotation" to an object with keys "input_side" and "output_side"; each value is a [x0,y0,x1,y1] pixel box around the corresponding piston side, including its force label, chamber, and area label.
Answer format: set "answer" to the requested integer force value in newtons.
Example JSON:
{"annotation":{"input_side":[120,70,340,562],"output_side":[760,70,980,562]},"answer":48}
```

### task_physics__lever__missing_weight_balance_value / answer_and_annotation / sample 7105513393750825

- `query_id`: `single`
- `instance_seed`: `7105513393750825`
- `word_count`: `99`
- `body_word_count`: `32`

```text
The figure shows a lever setup with a fulcrum, distance marks, and weight blocks. Use the shown weights and distances. What value must the marked `?` weight have for the lever to balance?
Annotation format: set "annotation" to an object with keys "known_weights" and "target_weight"; each value is an array of [x0,y0,x1,y1] pixel boxes around the known weight blocks or the marked `?` weight block used for the balance.
Answer format: set "answer" to the integer missing weight value.
Example JSON:
{"annotation":{"known_weights":[[192,282,250,334],[760,282,818,334]],"target_weight":[[430,282,488,334]]},"answer":5}
```

### task_physics__magnetic_force__force_direction_choice / answer_and_annotation / sample 6659740248566057

- `query_id`: `single`
- `instance_seed`: `6659740248566057`
- `word_count`: `98`
- `body_word_count`: `36`

```text
The diagram shows a magnetic-field panel with field-direction symbols, a charged particle, a velocity arrow, and eight labeled candidate force arrows. Using F=q v x B, choose the candidate arrow that matches the magnetic-force direction.
Annotation format: set "annotation" to an object mapping field_orientation, charge, and velocity to [x0,y0,x1,y1] pixel boxes around the magnetic-field label, charged particle, and velocity vector.
Required answer format: set "answer" to the option letter of the candidate force arrow.
Example JSON:
{"annotation":{"field_orientation":[86,72,216,110],"charge":[390,270,462,342],"velocity":[426,220,560,334]},"answer":"D"}
```

### task_physics__wave_interference__path_difference_value / answer_and_annotation / sample 3175647975572170

- `query_id`: `single`
- `instance_seed`: `3175647975572170`
- `word_count`: `98`
- `body_word_count`: `41`

```text
This figure shows a ripple-tank wave-interference pattern from two labeled sources. Read the two labeled guided paths to P. What integer path difference do they show in lambda/2 steps? Base the answer on the shown source phase and ring spacing.
Use this annotation format: set "annotation" to an array of two source-to-P pixel segments; each segment is [[x0,y0],[x1,y1]] and endpoint order does not matter.
Use this answer format: set "answer" to the integer absolute path difference counted in lambda/2 steps.
Example JSON:
{"annotation":[[[212,164],[486,356]],[[754,184],[486,356]]],"answer":3}
```

### task_physics__electrostatic_field__field_direction_choice / answer_and_annotation / sample 691949715568097

- `query_id`: `force_on_negative_charge`
- `instance_seed`: `691949715568097`
- `word_count`: `97`
- `body_word_count`: `40`

```text
The image shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Infer the force on the negative test charge at P. Which candidate arrow represents it?
Annotation format: set "annotation" to an object with keys "Q1", "Q2", "Q3", and "P"; each value is the [x,y] pixel point at the center of that marker.
Answer format: set "answer" to the option letter of the candidate arrow.
Example JSON:
{"annotation":{"Q1":[248,318],"Q2":[526,196],"Q3":[526,440],"P":[386,318]},"answer":"C"}
```

### task_physics__electrostatic_field__field_direction_choice / answer_and_annotation / sample 8308414192577222

- `query_id`: `force_on_positive_charge`
- `instance_seed`: `8308414192577222`
- `word_count`: `97`
- `body_word_count`: `40`

```text
The physics diagram shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Which candidate arrow shows the force direction on the positive test charge at P?
Answer format: set "answer" to the option letter of the candidate arrow.
Annotation format: set "annotation" to an object with keys "Q1", "Q2", "Q3", and "P"; each value is the [x,y] pixel point at the center of that marker.
Example JSON:
{"annotation":{"Q1":[248,318],"Q2":[526,196],"Q3":[526,440],"P":[386,318]},"answer":"C"}
```

### task_physics__electromagnetic_induction__induced_current_direction_count / answer_and_annotation / sample 8652736147108104

- `query_id`: `no_induced_current_count`
- `instance_seed`: `8652736147108104`
- `word_count`: `96`
- `body_word_count`: `34`

```text
This figure shows six mini-panels showing conducting loops, into-page or out-of-page magnetic-field symbols, and visible cues for changing or unchanged magnetic flux. Using the shown flux-change cues, how many loops have no induced current?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the full mini-panels whose loop has no induced current; use an empty array [] if none match.
Format for the "answer" field: set "answer" to the number of mini-panels whose loop has no induced current.
Example JSON:
{"annotation":[[60,70,390,420],[420,70,750,420]],"answer":2}
```

### task_physics__electrostatic_field__field_direction_choice / answer_and_annotation / sample 1511700211645757

- `query_id`: `electric_field_direction`
- `instance_seed`: `1511700211645757`
- `word_count`: `96`
- `body_word_count`: `39`

```text
This figure shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. At point P, choose the option arrow that matches the net electric field direction.
Answer format: set "answer" to the option letter of the candidate arrow.
Annotation format: set "annotation" to an object with keys "Q1", "Q2", "Q3", and "P"; each value is the [x,y] pixel point at the center of that marker.
Example JSON:
{"annotation":{"Q1":[248,318],"Q2":[526,196],"Q3":[526,440],"P":[386,318]},"answer":"C"}
```

### task_physics__lens_optics__image_property_choice / answer_and_annotation / sample 5656284987157397

- `query_id`: `single`
- `instance_seed`: `5656284987157397`
- `word_count`: `96`
- `body_word_count`: `34`

```text
This diagram shows a converging thin-lens diagram with a principal axis, F and 2F focal marks, one object arrow, and visible image-property option cards. Which option describes the image formed by the converging lens?
Annotation format: set "annotation" to an object with keys "lens", "object_arrow", and "focal_marks"; each value is a pixel bounding box [x0,y0,x1,y1] around that visible diagram element.
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":{"lens":[392,210,468,530],"object_arrow":[120,230,190,380],"focal_marks":[180,395,680,430]},"answer":"C"}
```

### task_physics__spring__spring_missing_value / answer_and_annotation / sample 2957435647730391

- `query_id`: `missing_weight_for_extension`
- `instance_seed`: `2957435647730391`
- `word_count`: `96`
- `body_word_count`: `26`

```text
The visual shows two matching spring setups with extension rulers. The two springs are identical. What integer weight belongs at the marked `?` on the right spring?
Final answer format: set "answer" to the integer missing weight or extension value.
Annotation format: set "annotation" to an object with keys "reference_weight", "reference_extension", "query_weight", and "query_extension"; each value is a [x0,y0,x1,y1] pixel box around the corresponding weight block or extension marker.
Example JSON:
{"annotation":{"reference_weight":[170,342,248,396],"reference_extension":[204,241,256,273],"query_weight":[595,226,647,260],"query_extension":[598,293,650,325]},"answer":4}
```

### task_physics__thermal_mixing__final_temperature_value / answer_and_annotation / sample 8825707600064752

- `query_id`: `single`
- `instance_seed`: `8825707600064752`
- `word_count`: `96`
- `body_word_count`: `43`

```text
The diagram shows separate liquid cups with visible Celsius temperature labels being poured into one insulated mixing container. The cups contain equal amounts of the same liquid and are mixed in the insulated container. What is the final equilibrium temperature in degrees Celsius?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around each visible initial temperature label used to compute the final temperature.
Required answer format: set "answer" to the integer final equilibrium temperature in degrees Celsius.
Example JSON:
{"annotation":[[130,230,190,270],[310,230,370,270]],"answer":45}
```

## Repeated Scaffolding Terms

## All Prompt Samples

### task_physics__analog_meter__meter_readout_value / ammeter_readout / answer_and_annotation / sample 8310095324628484

- `instance_seed`: `8310095324628484`
- `word_count`: `68`
- `body_word_count`: `26`

```text
The figure shows one analog meter face with a visible needle, numeric tick scale, and unit label. Determine the ammeter's integer readout from the needle position.
Annotation format: set "annotation" to the needle segment as [[x0,y0],[x1,y1]] in image pixel coordinates.
Format for the "answer" field: set "answer" to the integer ammeter reading in the displayed unit.
Example JSON:
{"annotation":[[512,482],[638,318]],"answer":7}
```

### task_physics__analog_meter__meter_readout_value / ammeter_readout / answer_only / sample 8310095324628484

- `instance_seed`: `8310095324628484`
- `word_count`: `44`
- `body_word_count`: `26`

```text
The figure shows one analog meter face with a visible needle, numeric tick scale, and unit label. Determine the ammeter's integer readout from the needle position.
Required answer format: set "answer" to the integer ammeter reading in the displayed unit.
Example JSON:
{"answer":7}
```

### task_physics__analog_meter__meter_readout_value / voltmeter_readout / answer_and_annotation / sample 2274850799070167

- `instance_seed`: `2274850799070167`
- `word_count`: `66`
- `body_word_count`: `27`

```text
The meter diagram shows one analog meter face with a visible needle, numeric tick scale, and unit label. Determine the voltmeter's integer readout from the needle position.
Annotation format: set "annotation" to the needle segment as [[x0,y0],[x1,y1]] in image pixel coordinates.
Answer format: set "answer" to the integer voltmeter reading in the displayed unit.
Example JSON:
{"annotation":[[512,482],[638,318]],"answer":11}
```

### task_physics__analog_meter__meter_readout_value / voltmeter_readout / answer_only / sample 2274850799070167

- `instance_seed`: `2274850799070167`
- `word_count`: `45`
- `body_word_count`: `27`

```text
The meter diagram shows one analog meter face with a visible needle, numeric tick scale, and unit label. Determine the voltmeter's integer readout from the needle position.
Required answer format: set "answer" to the integer voltmeter reading in the displayed unit.
Example JSON:
{"answer":11}
```

### task_physics__bridge_circuit__bridge_missing_resistance_value / single / answer_and_annotation / sample 5901447276294792

- `instance_seed`: `5901447276294792`
- `word_count`: `85`
- `body_word_count`: `44`

```text
This circuit diagram shows a balanced resistor bridge circuit with four labeled bridge resistors, one resistor marked with a question mark, and a center meter reading zero. Using the zero meter reading and the shown resistor labels, what value should replace the question mark?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel bounding box around the question-mark resistor.
Required answer format: set "answer" to the missing resistance as an integer number of ohms.
Example JSON:
{"annotation":[912,128,982,214],"answer":6}
```

### task_physics__bridge_circuit__bridge_missing_resistance_value / single / answer_only / sample 5901447276294792

- `instance_seed`: `5901447276294792`
- `word_count`: `62`
- `body_word_count`: `58`

```text
This circuit diagram shows a balanced resistor bridge circuit with four labeled bridge resistors, one resistor marked with a question mark, and a center meter reading zero. Using the zero meter reading and the shown resistor labels, what value should replace the question mark?
Answer field: set "answer" to the missing resistance as an integer number of ohms.
Example JSON:
{"answer":6}
```

### task_physics__bulb_circuit__brightness_extremum_label / brightest_bulb_label / answer_and_annotation / sample 4284097809675360

- `instance_seed`: `4284097809675360`
- `word_count`: `71`
- `body_word_count`: `22`

```text
The visual shows an ideal-battery circuit with five labeled bulbs and resistance labels. Which bulb dissipates the most power in this circuit?
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel bounding box around the selected bulb symbol and its resistance label.
Required answer format: set "answer" to the label of the brightest bulb as a string, for example "B2".
Example JSON:
{"annotation":[5,0,9,3],"answer":"B2"}
```

### task_physics__bulb_circuit__brightness_extremum_label / brightest_bulb_label / answer_only / sample 4284097809675360

- `instance_seed`: `4284097809675360`
- `word_count`: `44`
- `body_word_count`: `22`

```text
The visual shows an ideal-battery circuit with five labeled bulbs and resistance labels. Which bulb dissipates the most power in this circuit?
Required answer format: set "answer" to the label of the brightest bulb as a string, for example "B2".
Example JSON:
{"answer":"B2"}
```

### task_physics__bulb_circuit__brightness_extremum_label / dimmest_bulb_label / answer_and_annotation / sample 1929236171745811

- `instance_seed`: `1929236171745811`
- `word_count`: `73`
- `body_word_count`: `24`

```text
The figure shows an ideal-battery circuit with five labeled bulbs and resistance labels. Using the shown resistance labels, which bulb has the least brightness?
Final answer format: set "answer" to the label of the dimmest bulb as a string, for example "B2".
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel bounding box around the selected bulb symbol and its resistance label.
Example JSON:
{"annotation":[5,0,9,3],"answer":"B2"}
```

### task_physics__bulb_circuit__brightness_extremum_label / dimmest_bulb_label / answer_only / sample 1929236171745811

- `instance_seed`: `1929236171745811`
- `word_count`: `45`
- `body_word_count`: `41`

```text
The figure shows an ideal-battery circuit with five labeled bulbs and resistance labels. Using the shown resistance labels, which bulb has the least brightness?
Answer field: set "answer" to the label of the dimmest bulb as a string, for example "B2".
Example JSON:
{"answer":"B2"}
```

### task_physics__buoyancy_density__object_density_value / single / answer_and_annotation / sample 3298251435485081

- `instance_seed`: `3298251435485081`
- `word_count`: `86`
- `body_word_count`: `38`

```text
The visual shows a buoyancy diagram with a floating object divided into equal parts, a visible liquid surface, and a liquid-density label. The object is floating. Compute its density from the submerged fraction and the shown liquid density.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel bounding box around the floating object.
Required answer format: set "answer" to the object density in g/cm^3 as a number rounded to one decimal place.
Example JSON:
{"annotation":[200,180,300,360],"answer":0.8}
```

### task_physics__buoyancy_density__object_density_value / single / answer_only / sample 3298251435485081

- `instance_seed`: `3298251435485081`
- `word_count`: `66`
- `body_word_count`: `38`

```text
The visual shows a buoyancy diagram with a floating object divided into equal parts, a visible liquid surface, and a liquid-density label. The object is floating. Compute its density from the submerged fraction and the shown liquid density.
Format for the "answer" field: set "answer" to the object density in g/cm^3 as a number rounded to one decimal place.
Example JSON:
{"answer":0.8}
```

### task_physics__circuit_equivalent__total_capacitance_value / single / answer_and_annotation / sample 3550618771244141

- `instance_seed`: `3550618771244141`
- `word_count`: `103`
- `body_word_count`: `43`

```text
The circuit diagram shows one capacitor circuit between terminals A and B with at least one labeled parallel-plate capacitor in series with one or two labeled parallel capacitor blocks. Read the circuit between terminals A and B. What is its total equivalent capacitance?
Answer format: set "answer" to the total equivalent capacitance between terminals A and B as an integer number of microfarads.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the full capacitor network between terminals A and B, including the component symbols, value labels, and connecting wires.
Example JSON:
{"annotation":[90,120,760,520],"answer":8}
```

### task_physics__circuit_equivalent__total_capacitance_value / single / answer_only / sample 3550618771244141

- `instance_seed`: `3550618771244141`
- `word_count`: `68`
- `body_word_count`: `43`

```text
The circuit diagram shows one capacitor circuit between terminals A and B with at least one labeled parallel-plate capacitor in series with one or two labeled parallel capacitor blocks. Read the circuit between terminals A and B. What is its total equivalent capacitance?
Final answer format: set "answer" to the total equivalent capacitance between terminals A and B as an integer number of microfarads.
Example JSON:
{"answer":8}
```

### task_physics__circuit_equivalent__total_resistance_value / single / answer_and_annotation / sample 2605469048287086

- `instance_seed`: `2605469048287086`
- `word_count`: `100`
- `body_word_count`: `37`

```text
The figure shows one resistor circuit between terminals A and B with at least one labeled zigzag resistor in series with one or two labeled parallel resistor blocks. Determine the network's total resistance between A and B.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the full resistor network between terminals A and B, including the component symbols, value labels, and connecting wires.
Format for the "answer" field: set "answer" to the total equivalent resistance between terminals A and B as an integer number of ohms.
Example JSON:
{"annotation":[90,120,760,520],"answer":8}
```

### task_physics__circuit_equivalent__total_resistance_value / single / answer_only / sample 2605469048287086

- `instance_seed`: `2605469048287086`
- `word_count`: `62`
- `body_word_count`: `37`

```text
The figure shows one resistor circuit between terminals A and B with at least one labeled zigzag resistor in series with one or two labeled parallel resistor blocks. Determine the network's total resistance between A and B.
Required answer format: set "answer" to the total equivalent resistance between terminals A and B as an integer number of ohms.
Example JSON:
{"answer":8}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / brightens_after_switch_change / answer_and_annotation / sample 298454826081349

- `instance_seed`: `298454826081349`
- `word_count`: `127`
- `body_word_count`: `30`

```text
The image shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. After the red-boxed switch action occurs, which labeled bulb becomes brighter?
Final answer format: set "answer" to the label of the bulb that becomes brighter after the switch action as a string, for example "B2".
Annotation format: set "annotation" to an object mapping "changed_switch" and each visible bulb label B1 through B5 to one [x0,y0,x1,y1] pixel box around the switch action cue and each bulb symbol with its resistance label.
Example JSON:
{"annotation":{"changed_switch":[40,40,120,95],"B1":[130,40,210,120],"B2":[220,40,300,120],"B3":[310,40,390,120],"B4":[400,40,480,120],"B5":[490,40,570,120]},"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / brightens_after_switch_change / answer_only / sample 298454826081349

- `instance_seed`: `298454826081349`
- `word_count`: `58`
- `body_word_count`: `30`

```text
The image shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. After the red-boxed switch action occurs, which labeled bulb becomes brighter?
Required answer format: set "answer" to the label of the bulb that becomes brighter after the switch action as a string, for example "B2".
Example JSON:
{"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / dims_after_switch_change / answer_and_annotation / sample 2253101174342736

- `instance_seed`: `2253101174342736`
- `word_count`: `131`
- `body_word_count`: `32`

```text
The visual shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. Select the label of the bulb that dims after the shown switch action.
Annotation format: set "annotation" to an object mapping "changed_switch" and each visible bulb label B1 through B5 to one [x0,y0,x1,y1] pixel box around the switch action cue and each bulb symbol with its resistance label.
Format for the "answer" field: set "answer" to the label of the bulb that becomes dimmer after the switch action as a string, for example "B2".
Example JSON:
{"annotation":{"changed_switch":[40,40,120,95],"B1":[130,40,210,120],"B2":[220,40,300,120],"B3":[310,40,390,120],"B4":[400,40,480,120],"B5":[490,40,570,120]},"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / dims_after_switch_change / answer_only / sample 2253101174342736

- `instance_seed`: `2253101174342736`
- `word_count`: `59`
- `body_word_count`: `55`

```text
The visual shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. Select the label of the bulb that dims after the shown switch action.
Answer field: set "answer" to the label of the bulb that becomes dimmer after the switch action as a string, for example "B2".
Example JSON:
{"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / turns_off_after_switch_change / answer_and_annotation / sample 3205996959760868

- `instance_seed`: `3205996959760868`
- `word_count`: `136`
- `body_word_count`: `37`

```text
This circuit diagram shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. Using the bulb resistances and topology, which bulb is on before the switch action and off afterward?
Annotation format: set "annotation" to an object mapping "changed_switch" and each visible bulb label B1 through B5 to one [x0,y0,x1,y1] pixel box around the switch action cue and each bulb symbol with its resistance label.
Format for the "answer" field: set "answer" to the label of the bulb that turns off after the switch action as a string, for example "B2".
Example JSON:
{"annotation":{"changed_switch":[40,40,120,95],"B1":[130,40,210,120],"B2":[220,40,300,120],"B3":[310,40,390,120],"B4":[400,40,480,120],"B5":[490,40,570,120]},"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / turns_off_after_switch_change / answer_only / sample 3205996959760868

- `instance_seed`: `3205996959760868`
- `word_count`: `67`
- `body_word_count`: `37`

```text
This circuit diagram shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. Using the bulb resistances and topology, which bulb is on before the switch action and off afterward?
Format for the "answer" field: set "answer" to the label of the bulb that turns off after the switch action as a string, for example "B2".
Example JSON:
{"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / turns_on_after_switch_change / answer_and_annotation / sample 1196983518433529

- `instance_seed`: `1196983518433529`
- `word_count`: `126`
- `body_word_count`: `30`

```text
The image shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. After the red-boxed switch action occurs, which labeled bulb turns on?
Answer format: set "answer" to the label of the bulb that turns on after the switch action as a string, for example "B2".
Annotation format: set "annotation" to an object mapping "changed_switch" and each visible bulb label B1 through B5 to one [x0,y0,x1,y1] pixel box around the switch action cue and each bulb symbol with its resistance label.
Example JSON:
{"annotation":{"changed_switch":[40,40,120,95],"B1":[130,40,210,120],"B2":[220,40,300,120],"B3":[310,40,390,120],"B4":[400,40,480,120],"B5":[490,40,570,120]},"answer":"B2"}
```

### task_physics__circuit_state_change__bulb_brightness_change_label / turns_on_after_switch_change / answer_only / sample 1196983518433529

- `instance_seed`: `1196983518433529`
- `word_count`: `57`
- `body_word_count`: `30`

```text
The image shows a visible ideal-battery circuit with five labeled bulbs, resistance labels, and one red-boxed switch action cue. After the red-boxed switch action occurs, which labeled bulb turns on?
Answer format: set "answer" to the label of the bulb that turns on after the switch action as a string, for example "B2".
Example JSON:
{"answer":"B2"}
```

### task_physics__collision__sticky_collision_direction_choice / single / answer_and_annotation / sample 3427639663144369

- `instance_seed`: `3427639663144369`
- `word_count`: `107`
- `body_word_count`: `48`

```text
The diagram shows a collision table with puck A moving horizontally, puck B moving vertically, visible mass and speed labels, a stuck A+B puck, signed axes, and four candidate direction arrows. The pucks stick at the center. Which labeled candidate arrow shows the direction they move afterward?
Annotation format: set "annotation" to an array of two line segments, each written as [[x0,y0],[x1,y1]], for puck A's motion arrow and puck B's motion arrow.
Answer format: set "answer" to the option letter A, B, C, or D of the correct candidate arrow.
Example JSON:
{"annotation":[[[176,304],[366,304]],[[436,158],[436,254]]],"answer":"D"}
```

### task_physics__collision__sticky_collision_direction_choice / single / answer_only / sample 3427639663144369

- `instance_seed`: `3427639663144369`
- `word_count`: `71`
- `body_word_count`: `48`

```text
The diagram shows a collision table with puck A moving horizontally, puck B moving vertically, visible mass and speed labels, a stuck A+B puck, signed axes, and four candidate direction arrows. The pucks stick at the center. Which labeled candidate arrow shows the direction they move afterward?
Required answer format: set "answer" to the option letter A, B, C, or D of the correct candidate arrow.
Example JSON:
{"answer":"D"}
```

### task_physics__collision__sticky_collision_speed_value / single / answer_and_annotation / sample 5096128980181968

- `instance_seed`: `5096128980181968`
- `word_count`: `107`
- `body_word_count`: `49`

```text
This diagram shows a compact collision table with puck A moving horizontally, puck B moving vertically, visible mass and speed labels, a stuck A+B puck, and signed axes. Using the shown masses, speeds, and approach directions, what is the stuck pucks' final speed rounded to one decimal place?
Annotation format: set "annotation" to an array of two line segments, each written as [[x0,y0],[x1,y1]], for puck A's motion arrow and puck B's motion arrow.
Answer format: set "answer" to the final speed in m/s rounded to one decimal place.
Example JSON:
{"annotation":[[[176,304],[366,304]],[[436,158],[436,254]]],"answer":5.0}
```

### task_physics__collision__sticky_collision_speed_value / single / answer_only / sample 5096128980181968

- `instance_seed`: `5096128980181968`
- `word_count`: `73`
- `body_word_count`: `49`

```text
This diagram shows a compact collision table with puck A moving horizontally, puck B moving vertically, visible mass and speed labels, a stuck A+B puck, and signed axes. Using the shown masses, speeds, and approach directions, what is the stuck pucks' final speed rounded to one decimal place?
Format for the "answer" field: set "answer" to the final speed in m/s rounded to one decimal place.
Example JSON:
{"answer":5.0}
```

### task_physics__electromagnetic_induction__induced_current_direction_count / clockwise_induced_current_count / answer_and_annotation / sample 3276993429165654

- `instance_seed`: `3276993429165654`
- `word_count`: `94`
- `body_word_count`: `34`

```text
The visual shows six mini-panels showing conducting loops, into-page or out-of-page magnetic-field symbols, and visible cues for changing or unchanged magnetic flux. Using the shown flux-change cues, how many loops have clockwise induced current?
Final answer format: set "answer" to the number of mini-panels whose loop has clockwise induced current.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the full mini-panels whose loop has clockwise induced current; use an empty array [] if none match.
Example JSON:
{"annotation":[[60,70,390,420],[420,70,750,420]],"answer":2}
```

### task_physics__electromagnetic_induction__induced_current_direction_count / clockwise_induced_current_count / answer_only / sample 3276993429165654

- `instance_seed`: `3276993429165654`
- `word_count`: `56`
- `body_word_count`: `34`

```text
The visual shows six mini-panels showing conducting loops, into-page or out-of-page magnetic-field symbols, and visible cues for changing or unchanged magnetic flux. Using the shown flux-change cues, how many loops have clockwise induced current?
Format for the "answer" field: set "answer" to the number of mini-panels whose loop has clockwise induced current.
Example JSON:
{"answer":2}
```

### task_physics__electromagnetic_induction__induced_current_direction_count / counterclockwise_induced_current_count / answer_and_annotation / sample 4929633690953197

- `instance_seed`: `4929633690953197`
- `word_count`: `92`
- `body_word_count`: `33`

```text
The visual shows six mini-panels showing conducting loops, into-page or out-of-page magnetic-field symbols, and visible cues for changing or unchanged magnetic flux. How many panels have a counterclockwise induced current in the loop?
Answer format: set "answer" to the number of mini-panels whose loop has counterclockwise induced current.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the full mini-panels whose loop has counterclockwise induced current; use an empty array [] if none match.
Example JSON:
{"annotation":[[60,70,390,420],[420,70,750,420]],"answer":2}
```

### task_physics__electromagnetic_induction__induced_current_direction_count / counterclockwise_induced_current_count / answer_only / sample 4929633690953197

- `instance_seed`: `4929633690953197`
- `word_count`: `53`
- `body_word_count`: `33`

```text
The visual shows six mini-panels showing conducting loops, into-page or out-of-page magnetic-field symbols, and visible cues for changing or unchanged magnetic flux. How many panels have a counterclockwise induced current in the loop?
Required answer format: set "answer" to the number of mini-panels whose loop has counterclockwise induced current.
Example JSON:
{"answer":2}
```

### task_physics__electromagnetic_induction__induced_current_direction_count / no_induced_current_count / answer_and_annotation / sample 8652736147108104

- `instance_seed`: `8652736147108104`
- `word_count`: `96`
- `body_word_count`: `34`

```text
This figure shows six mini-panels showing conducting loops, into-page or out-of-page magnetic-field symbols, and visible cues for changing or unchanged magnetic flux. Using the shown flux-change cues, how many loops have no induced current?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the full mini-panels whose loop has no induced current; use an empty array [] if none match.
Format for the "answer" field: set "answer" to the number of mini-panels whose loop has no induced current.
Example JSON:
{"annotation":[[60,70,390,420],[420,70,750,420]],"answer":2}
```

### task_physics__electromagnetic_induction__induced_current_direction_count / no_induced_current_count / answer_only / sample 8652736147108104

- `instance_seed`: `8652736147108104`
- `word_count`: `53`
- `body_word_count`: `34`

```text
This figure shows six mini-panels showing conducting loops, into-page or out-of-page magnetic-field symbols, and visible cues for changing or unchanged magnetic flux. Using the shown flux-change cues, how many loops have no induced current?
Answer format: set "answer" to the number of mini-panels whose loop has no induced current.
Example JSON:
{"answer":2}
```

### task_physics__electrostatic_field__field_direction_choice / electric_field_direction / answer_and_annotation / sample 1511700211645757

- `instance_seed`: `1511700211645757`
- `word_count`: `96`
- `body_word_count`: `39`

```text
This figure shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. At point P, choose the option arrow that matches the net electric field direction.
Answer format: set "answer" to the option letter of the candidate arrow.
Annotation format: set "annotation" to an object with keys "Q1", "Q2", "Q3", and "P"; each value is the [x,y] pixel point at the center of that marker.
Example JSON:
{"annotation":{"Q1":[248,318],"Q2":[526,196],"Q3":[526,440],"P":[386,318]},"answer":"C"}
```

### task_physics__electrostatic_field__field_direction_choice / electric_field_direction / answer_only / sample 1511700211645757

- `instance_seed`: `1511700211645757`
- `word_count`: `56`
- `body_word_count`: `39`

```text
This figure shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. At point P, choose the option arrow that matches the net electric field direction.
Final answer format: set "answer" to the option letter of the candidate arrow.
Example JSON:
{"answer":"C"}
```

### task_physics__electrostatic_field__field_direction_choice / force_on_negative_charge / answer_and_annotation / sample 691949715568097

- `instance_seed`: `691949715568097`
- `word_count`: `97`
- `body_word_count`: `40`

```text
The image shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Infer the force on the negative test charge at P. Which candidate arrow represents it?
Annotation format: set "annotation" to an object with keys "Q1", "Q2", "Q3", and "P"; each value is the [x,y] pixel point at the center of that marker.
Answer format: set "answer" to the option letter of the candidate arrow.
Example JSON:
{"annotation":{"Q1":[248,318],"Q2":[526,196],"Q3":[526,440],"P":[386,318]},"answer":"C"}
```

### task_physics__electrostatic_field__field_direction_choice / force_on_negative_charge / answer_only / sample 691949715568097

- `instance_seed`: `691949715568097`
- `word_count`: `56`
- `body_word_count`: `40`

```text
The image shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Infer the force on the negative test charge at P. Which candidate arrow represents it?
Answer format: set "answer" to the option letter of the candidate arrow.
Example JSON:
{"answer":"C"}
```

### task_physics__electrostatic_field__field_direction_choice / force_on_positive_charge / answer_and_annotation / sample 8308414192577222

- `instance_seed`: `8308414192577222`
- `word_count`: `97`
- `body_word_count`: `40`

```text
The physics diagram shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Which candidate arrow shows the force direction on the positive test charge at P?
Answer format: set "answer" to the option letter of the candidate arrow.
Annotation format: set "annotation" to an object with keys "Q1", "Q2", "Q3", and "P"; each value is the [x,y] pixel point at the center of that marker.
Example JSON:
{"annotation":{"Q1":[248,318],"Q2":[526,196],"Q3":[526,440],"P":[386,318]},"answer":"C"}
```

### task_physics__electrostatic_field__field_direction_choice / force_on_positive_charge / answer_only / sample 8308414192577222

- `instance_seed`: `8308414192577222`
- `word_count`: `56`
- `body_word_count`: `40`

```text
The physics diagram shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Which candidate arrow shows the force direction on the positive test charge at P?
Answer format: set "answer" to the option letter of the candidate arrow.
Example JSON:
{"answer":"C"}
```

### task_physics__electrostatic_field__potential_value / single / answer_and_annotation / sample 7964932501198279

- `instance_seed`: `7964932501198279`
- `word_count`: `95`
- `body_word_count`: `38`

```text
The diagram shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Using the displayed q and r labels, determine the signed potential at P.
Answer format: set "answer" to the signed integer electric potential at P.
Annotation format: set "annotation" to an object with keys "Q1", "Q2", "Q3", and "P"; each value is the [x,y] pixel point at the center of that marker.
Example JSON:
{"annotation":{"Q1":[526,318],"Q2":[386,148],"Q3":[108,318],"P":[386,318]},"answer":-4}
```

### task_physics__electrostatic_field__potential_value / single / answer_only / sample 7964932501198279

- `instance_seed`: `7964932501198279`
- `word_count`: `55`
- `body_word_count`: `38`

```text
The diagram shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Using the displayed q and r labels, determine the signed potential at P.
Final answer format: set "answer" to the signed integer electric potential at P.
Example JSON:
{"answer":-4}
```

### task_physics__electrostatic_field__zero_field_point_label / single / answer_and_annotation / sample 1239388486350731

- `instance_seed`: `1239388486350731`
- `word_count`: `92`
- `body_word_count`: `37`

```text
The image shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Which candidate point is located where the net electric field is zero?
Annotation format: set "annotation" to an object with keys "Q1", "Q2", and "zero_point"; each value is the [x,y] pixel point at the center of that marker.
Required answer format: set "answer" to the option letter of the labeled zero-field point.
Example JSON:
{"annotation":{"Q1":[248,318],"Q2":[526,318],"zero_point":[340,318]},"answer":"D"}
```

### task_physics__electrostatic_field__zero_field_point_label / single / answer_only / sample 1239388486350731

- `instance_seed`: `1239388486350731`
- `word_count`: `55`
- `body_word_count`: `37`

```text
The image shows an electrostatic coordinate grid with fixed point charges, a marked point or labeled candidate points, and visible option arrows or distance labels. Which candidate point is located where the net electric field is zero?
Final answer format: set "answer" to the option letter of the labeled zero-field point.
Example JSON:
{"answer":"D"}
```

### task_physics__fluid_flow__continuity_speed_value / single / answer_and_annotation / sample 3429017381631065

- `instance_seed`: `3429017381631065`
- `word_count`: `92`
- `body_word_count`: `46`

```text
The diagram shows a steady-flow pipe with station 1 and station 2, visible cross-section area labels, one known speed label, one missing speed label, and a flow arrow. Read the two area labels and the known speed label. What integer speed belongs at the missing station?
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the visible missing speed label, such as "v1 = ?" or "v2 = ?".
Required answer format: set "answer" to the missing integer flow speed in m/s.
Example JSON:
{"annotation":[724,412,862,458],"answer":8}
```

### task_physics__fluid_flow__continuity_speed_value / single / answer_only / sample 3429017381631065

- `instance_seed`: `3429017381631065`
- `word_count`: `63`
- `body_word_count`: `46`

```text
The diagram shows a steady-flow pipe with station 1 and station 2, visible cross-section area labels, one known speed label, one missing speed label, and a flow arrow. Read the two area labels and the known speed label. What integer speed belongs at the missing station?
Answer format: set "answer" to the missing integer flow speed in m/s.
Example JSON:
{"answer":8}
```

### task_physics__free_body_forces__net_force_direction_choice / single / answer_and_annotation / sample 6016879397434784

- `instance_seed`: `6016879397434784`
- `word_count`: `105`
- `body_word_count`: `35`

```text
The image shows one object with several labeled applied force arrows and eight labeled candidate net-force direction arrows. From the visible force arrows and magnitude labels, choose the candidate arrow showing the net force direction.
Annotation format: set "annotation" to an object with "force_diagram" as the [x0,y0,x1,y1] pixel box around the object, applied force arrows, and magnitude labels, and "selected_candidate" as the box around the selected candidate arrow option cell.
Answer format: set "answer" to the option letter of the candidate arrow showing the net force direction.
Example JSON:
{"annotation":{"force_diagram":[90,120,520,430],"selected_candidate":[450,610,570,700]},"answer":"C"}
```

### task_physics__free_body_forces__net_force_direction_choice / single / answer_only / sample 6016879397434784

- `instance_seed`: `6016879397434784`
- `word_count`: `57`
- `body_word_count`: `35`

```text
The image shows one object with several labeled applied force arrows and eight labeled candidate net-force direction arrows. From the visible force arrows and magnitude labels, choose the candidate arrow showing the net force direction.
Required answer format: set "answer" to the option letter of the candidate arrow showing the net force direction.
Example JSON:
{"answer":"C"}
```

### task_physics__gear_train__output_direction_label / single / answer_and_annotation / sample 5848087850764168

- `instance_seed`: `5848087850764168`
- `word_count`: `81`
- `body_word_count`: `37`

```text
The visual shows four labeled gear-train panels, each with an input gear and a marked output gear. Following the gear contacts from input to output in each panel, choose the panel where the output gear rotates clockwise.
Annotation format: set "annotation" to the [x0,y0,x1,y1] pixel box around the selected labeled gear-train panel.
Required answer format: set "answer" to the selected panel letter, one of A, B, C, or D.
Example JSON:
{"annotation":[40,50,520,390],"answer":"C"}
```

### task_physics__gear_train__output_direction_label / single / answer_only / sample 5848087850764168

- `instance_seed`: `5848087850764168`
- `word_count`: `60`
- `body_word_count`: `37`

```text
The visual shows four labeled gear-train panels, each with an input gear and a marked output gear. Following the gear contacts from input to output in each panel, choose the panel where the output gear rotates clockwise.
Format for the "answer" field: set "answer" to the selected panel letter, one of A, B, C, or D.
Example JSON:
{"answer":"C"}
```

### task_physics__gear_train__output_speed_value / single / answer_and_annotation / sample 6001109211360936

- `instance_seed`: `6001109211360936`
- `word_count`: `94`
- `body_word_count`: `26`

```text
The diagram shows a meshed gear train with an input gear and a marked output gear. What rotational speed in rpm does the output gear have?
Annotation format: set "annotation" to an object mapping input_gear and output_gear to [x0,y0,x1,y1] pixel boxes around the input gear with its tooth count and speed label, and the marked output gear with its tooth count.
Format for the "answer" field: set "answer" to the integer output rotational speed in rpm.
Example JSON:
{"annotation":{"input_gear":[10,20,110,120],"output_gear":[260,30,360,130]},"answer":90}
```

### task_physics__gear_train__output_speed_value / single / answer_only / sample 6001109211360936

- `instance_seed`: `6001109211360936`
- `word_count`: `45`
- `body_word_count`: `26`

```text
The diagram shows a meshed gear train with an input gear and a marked output gear. What rotational speed in rpm does the output gear have?
Format for the "answer" field: set "answer" to the integer output rotational speed in rpm.
Example JSON:
{"answer":90}
```

### task_physics__graduated_cylinder__displacement_volume_value / single / answer_and_annotation / sample 3699966586438330

- `instance_seed`: `3699966586438330`
- `word_count`: `92`
- `body_word_count`: `32`

```text
The diagram shows a graduated-cylinder setup with visible liquid meniscus lines, tick marks, numeric scale labels, and mL units. Subtract the before reading from the after reading. What displaced volume is shown?
Annotation format: set "annotation" to an object mapping before_cylinder and after_cylinder to [x0,y0,x1,y1] pixel boxes around the corresponding graduated-cylinder readouts, including liquid levels, tick marks, numeric scale labels, and mL units.
Answer format: set "answer" to the integer displaced volume in mL.
Example JSON:
{"annotation":{"before_cylinder":[146,140,365,612],"after_cylinder":[650,140,882,612]},"answer":20}
```

### task_physics__graduated_cylinder__displacement_volume_value / single / answer_only / sample 3699966586438330

- `instance_seed`: `3699966586438330`
- `word_count`: `48`
- `body_word_count`: `32`

```text
The diagram shows a graduated-cylinder setup with visible liquid meniscus lines, tick marks, numeric scale labels, and mL units. Subtract the before reading from the after reading. What displaced volume is shown?
Final answer format: set "answer" to the integer displaced volume in mL.
Example JSON:
{"answer":20}
```

### task_physics__graduated_cylinder__volume_readout_value / single / answer_and_annotation / sample 9004624515908076

- `instance_seed`: `9004624515908076`
- `word_count`: `79`
- `body_word_count`: `31`

```text
This measurement diagram shows a graduated-cylinder setup with visible liquid meniscus lines, tick marks, numeric scale labels, and mL units. Read the shown graduated-cylinder level. What integer mL value is indicated?
Answer format: set "answer" to the integer liquid volume in mL.
Annotation format: set "annotation" to one [x0,y0,x1,y1] pixel box around the graduated-cylinder readout, including the liquid level, tick marks, numeric scale labels, and mL unit.
Example JSON:
{"annotation":[145,130,390,612],"answer":35}
```

### task_physics__graduated_cylinder__volume_readout_value / single / answer_only / sample 9004624515908076

- `instance_seed`: `9004624515908076`
- `word_count`: `46`
- `body_word_count`: `42`

```text
This measurement diagram shows a graduated-cylinder setup with visible liquid meniscus lines, tick marks, numeric scale labels, and mL units. Read the shown graduated-cylinder level. What integer mL value is indicated?
Answer field: set "answer" to the integer liquid volume in mL.
Example JSON:
{"answer":35}
```

### task_physics__hydraulic__hydraulic_missing_value / missing_input_area / answer_and_annotation / sample 2553155137309841

- `instance_seed`: `2553155137309841`
- `word_count`: `101`
- `body_word_count`: `38`

```text
The image shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. The connected fluid transmits equal pressure. What integer input piston area belongs at the marked red `?`?
Annotation format: set "annotation" to an object with keys "input_side" and "output_side"; each value is a [x0,y0,x1,y1] pixel box around the corresponding piston side, including its force label, chamber, and area label.
Answer format: set "answer" to the requested integer piston area in cm^2.
Example JSON:
{"annotation":{"input_side":[120,70,340,562],"output_side":[760,70,980,562]},"answer":6}
```

### task_physics__hydraulic__hydraulic_missing_value / missing_input_area / answer_only / sample 2553155137309841

- `instance_seed`: `2553155137309841`
- `word_count`: `55`
- `body_word_count`: `38`

```text
The image shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. The connected fluid transmits equal pressure. What integer input piston area belongs at the marked red `?`?
Answer format: set "answer" to the requested integer piston area in cm^2.
Example JSON:
{"answer":6}
```

### task_physics__hydraulic__hydraulic_missing_value / missing_input_force / answer_and_annotation / sample 8458915069719234

- `instance_seed`: `8458915069719234`
- `word_count`: `101`
- `body_word_count`: `38`

```text
The figure shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. Use the shown output force and piston areas. What input force is required at the red `?`?
Final answer format: set "answer" to the requested integer force value in newtons.
Annotation format: set "annotation" to an object with keys "input_side" and "output_side"; each value is a [x0,y0,x1,y1] pixel box around the corresponding piston side, including its force label, chamber, and area label.
Example JSON:
{"annotation":{"input_side":[120,70,340,562],"output_side":[760,70,980,562]},"answer":8}
```

### task_physics__hydraulic__hydraulic_missing_value / missing_input_force / answer_only / sample 8458915069719234

- `instance_seed`: `8458915069719234`
- `word_count`: `57`
- `body_word_count`: `38`

```text
The figure shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. Use the shown output force and piston areas. What input force is required at the red `?`?
Format for the "answer" field: set "answer" to the requested integer force value in newtons.
Example JSON:
{"answer":8}
```

### task_physics__hydraulic__hydraulic_missing_value / missing_output_force / answer_and_annotation / sample 7037654664443469

- `instance_seed`: `7037654664443469`
- `word_count`: `99`
- `body_word_count`: `37`

```text
The diagram shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. What force on the output piston corresponds to the shown input force and piston areas?
Annotation format: set "annotation" to an object with keys "input_side" and "output_side"; each value is a [x0,y0,x1,y1] pixel box around the corresponding piston side, including its force label, chamber, and area label.
Answer format: set "answer" to the requested integer force value in newtons.
Example JSON:
{"annotation":{"input_side":[120,70,340,562],"output_side":[760,70,980,562]},"answer":48}
```

### task_physics__hydraulic__hydraulic_missing_value / missing_output_force / answer_only / sample 7037654664443469

- `instance_seed`: `7037654664443469`
- `word_count`: `53`
- `body_word_count`: `37`

```text
The diagram shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. What force on the output piston corresponds to the shown input force and piston areas?
Answer format: set "answer" to the requested integer force value in newtons.
Example JSON:
{"answer":48}
```

### task_physics__hydraulic__hydraulic_missing_value / missing_piston_area / answer_and_annotation / sample 1188507802227299

- `instance_seed`: `1188507802227299`
- `word_count`: `101`
- `body_word_count`: `35`

```text
This diagram shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. Using Pascal's law, what output piston area should replace the marked red `?` label?
Annotation format: set "annotation" to an object with keys "input_side" and "output_side"; each value is a [x0,y0,x1,y1] pixel box around the corresponding piston side, including its force label, chamber, and area label.
Format for the "answer" field: set "answer" to the requested integer piston area in cm^2.
Example JSON:
{"annotation":{"input_side":[120,70,340,562],"output_side":[760,70,980,562]},"answer":30}
```

### task_physics__hydraulic__hydraulic_missing_value / missing_piston_area / answer_only / sample 1188507802227299

- `instance_seed`: `1188507802227299`
- `word_count`: `53`
- `body_word_count`: `35`

```text
This diagram shows a connected hydraulic piston diagram with three fluid chambers, piston area labels, downward force arrows, and one red `?` label. Using Pascal's law, what output piston area should replace the marked red `?` label?
Required answer format: set "answer" to the requested integer piston area in cm^2.
Example JSON:
{"answer":30}
```

### task_physics__lens_optics__image_property_choice / single / answer_and_annotation / sample 5656284987157397

- `instance_seed`: `5656284987157397`
- `word_count`: `96`
- `body_word_count`: `34`

```text
This diagram shows a converging thin-lens diagram with a principal axis, F and 2F focal marks, one object arrow, and visible image-property option cards. Which option describes the image formed by the converging lens?
Annotation format: set "annotation" to an object with keys "lens", "object_arrow", and "focal_marks"; each value is a pixel bounding box [x0,y0,x1,y1] around that visible diagram element.
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":{"lens":[392,210,468,530],"object_arrow":[120,230,190,380],"focal_marks":[180,395,680,430]},"answer":"C"}
```

### task_physics__lens_optics__image_property_choice / single / answer_only / sample 5656284987157397

- `instance_seed`: `5656284987157397`
- `word_count`: `51`
- `body_word_count`: `34`

```text
This diagram shows a converging thin-lens diagram with a principal axis, F and 2F focal marks, one object arrow, and visible image-property option cards. Which option describes the image formed by the converging lens?
Final answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_physics__lever__missing_weight_balance_value / single / answer_and_annotation / sample 7105513393750825

- `instance_seed`: `7105513393750825`
- `word_count`: `99`
- `body_word_count`: `32`

```text
The figure shows a lever setup with a fulcrum, distance marks, and weight blocks. Use the shown weights and distances. What value must the marked `?` weight have for the lever to balance?
Annotation format: set "annotation" to an object with keys "known_weights" and "target_weight"; each value is an array of [x0,y0,x1,y1] pixel boxes around the known weight blocks or the marked `?` weight block used for the balance.
Answer format: set "answer" to the integer missing weight value.
Example JSON:
{"annotation":{"known_weights":[[192,282,250,334],[760,282,818,334]],"target_weight":[[430,282,488,334]]},"answer":5}
```

### task_physics__lever__missing_weight_balance_value / single / answer_only / sample 7105513393750825

- `instance_seed`: `7105513393750825`
- `word_count`: `47`
- `body_word_count`: `32`

```text
The figure shows a lever setup with a fulcrum, distance marks, and weight blocks. Use the shown weights and distances. What value must the marked `?` weight have for the lever to balance?
Required answer format: set "answer" to the integer missing weight value.
Example JSON:
{"answer":5}
```

### task_physics__lever__side_torque_value / single / answer_and_annotation / sample 8400622153511070

- `instance_seed`: `8400622153511070`
- `word_count`: `77`
- `body_word_count`: `30`

```text
The image shows a horizontal lever beam with a fulcrum, numbered distance marks, and weight blocks. Determine the torque contributed by the weights on the right side of the lever.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around every weight block on the queried side of the fulcrum.
Answer format: set "answer" to the integer torque value.
Example JSON:
{"annotation":[[192,282,250,334],[326,282,384,334]],"answer":12}
```

### task_physics__lever__side_torque_value / single / answer_only / sample 8400622153511070

- `instance_seed`: `8400622153511070`
- `word_count`: `44`
- `body_word_count`: `30`

```text
The image shows a horizontal lever beam with a fulcrum, numbered distance marks, and weight blocks. Determine the torque contributed by the weights on the right side of the lever.
Required answer format: set "answer" to the integer torque value.
Example JSON:
{"answer":12}
```

### task_physics__magnetic_force__force_direction_choice / single / answer_and_annotation / sample 6659740248566057

- `instance_seed`: `6659740248566057`
- `word_count`: `98`
- `body_word_count`: `36`

```text
The diagram shows a magnetic-field panel with field-direction symbols, a charged particle, a velocity arrow, and eight labeled candidate force arrows. Using F=q v x B, choose the candidate arrow that matches the magnetic-force direction.
Annotation format: set "annotation" to an object mapping field_orientation, charge, and velocity to [x0,y0,x1,y1] pixel boxes around the magnetic-field label, charged particle, and velocity vector.
Required answer format: set "answer" to the option letter of the candidate force arrow.
Example JSON:
{"annotation":{"field_orientation":[86,72,216,110],"charge":[390,270,462,342],"velocity":[426,220,560,334]},"answer":"D"}
```

### task_physics__magnetic_force__force_direction_choice / single / answer_only / sample 6659740248566057

- `instance_seed`: `6659740248566057`
- `word_count`: `56`
- `body_word_count`: `36`

```text
The diagram shows a magnetic-field panel with field-direction symbols, a charged particle, a velocity arrow, and eight labeled candidate force arrows. Using F=q v x B, choose the candidate arrow that matches the magnetic-force direction.
Format for the "answer" field: set "answer" to the option letter of the candidate force arrow.
Example JSON:
{"answer":"D"}
```

### task_physics__manometer__pressure_difference_value / single / answer_and_annotation / sample 6167278258396297

- `instance_seed`: `6167278258396297`
- `word_count`: `89`
- `body_word_count`: `43`

```text
The figure shows a U-tube manometer with pressure points A and B, two visible liquid levels, a height-difference marker, and a rho g conversion label. Read the liquid-level height difference and conversion label. What is the absolute pressure difference between A and B?
Final answer format: set "answer" to the integer absolute pressure difference in kPa.
Annotation format: set "annotation" to an object mapping height_difference and fluid_density_label to [x0,y0,x1,y1] pixel boxes.
Example JSON:
{"annotation":{"height_difference":[520,260,650,390],"fluid_density_label":[410,590,710,640]},"answer":18}
```

### task_physics__manometer__pressure_difference_value / single / answer_only / sample 6167278258396297

- `instance_seed`: `6167278258396297`
- `word_count`: `59`
- `body_word_count`: `43`

```text
The figure shows a U-tube manometer with pressure points A and B, two visible liquid levels, a height-difference marker, and a rho g conversion label. Read the liquid-level height difference and conversion label. What is the absolute pressure difference between A and B?
Answer format: set "answer" to the integer absolute pressure difference in kPa.
Example JSON:
{"answer":18}
```

### task_physics__motion_graph__average_speed_value / single / answer_and_annotation / sample 4486240102467441

- `instance_seed`: `4486240102467441`
- `word_count`: `70`
- `body_word_count`: `27`

```text
The figure shows a kinematics graph with labeled axes, a piecewise-linear curve, and one marked time interval. What integer average speed is shown over the marked interval?
Use this annotation format: set "annotation" to the pixel segment [[x0,y0],[x1,y1]] for the marked distance-time graph segment.
Use this answer format: set "answer" to the integer average speed in m/s.
Example JSON:
{"annotation":[[0,0],[4,0]],"answer":8}
```

### task_physics__motion_graph__average_speed_value / single / answer_only / sample 4486240102467441

- `instance_seed`: `4486240102467441`
- `word_count`: `43`
- `body_word_count`: `27`

```text
The figure shows a kinematics graph with labeled axes, a piecewise-linear curve, and one marked time interval. What integer average speed is shown over the marked interval?
Answer format: set "answer" to the integer average speed in m/s.
Example JSON:
{"answer":8}
```

### task_physics__motion_graph__interval_displacement_value / constant_acceleration_interval_displacement / answer_and_annotation / sample 5466817950307128

- `instance_seed`: `5466817950307128`
- `word_count`: `77`
- `body_word_count`: `32`

```text
The visual shows a kinematics graph with labeled axes, a piecewise-linear curve, and one marked time interval. Using the visible endpoint velocities and interval width, determine the displacement over the marked interval.
Format for the "annotation" field: set "annotation" to the pixel segment [[x0,y0],[x1,y1]] for the marked velocity-time graph segment.
Format for the "answer" field: set "answer" to the integer displacement over the marked interval.
Example JSON:
{"annotation":[[0,0],[4,0]],"answer":8}
```

### task_physics__motion_graph__interval_displacement_value / constant_acceleration_interval_displacement / answer_only / sample 5466817950307128

- `instance_seed`: `5466817950307128`
- `word_count`: `49`
- `body_word_count`: `32`

```text
The visual shows a kinematics graph with labeled axes, a piecewise-linear curve, and one marked time interval. Using the visible endpoint velocities and interval width, determine the displacement over the marked interval.
Final answer format: set "answer" to the integer displacement over the marked interval.
Example JSON:
{"answer":8}
```

### task_physics__motion_graph__interval_displacement_value / constant_velocity_interval_displacement / answer_and_annotation / sample 6383621378460919

- `instance_seed`: `6383621378460919`
- `word_count`: `73`
- `body_word_count`: `30`

```text
The visual shows a kinematics graph with labeled axes, a piecewise-linear curve, and one marked time interval. Use the velocity-time graph. What integer displacement is shown over the highlighted interval?
Use this annotation format: set "annotation" to the pixel segment [[x0,y0],[x1,y1]] for the marked velocity-time graph segment.
Use this answer format: set "answer" to the integer displacement over the marked interval.
Example JSON:
{"annotation":[[0,0],[4,0]],"answer":8}
```

### task_physics__motion_graph__interval_displacement_value / constant_velocity_interval_displacement / answer_only / sample 6383621378460919

- `instance_seed`: `6383621378460919`
- `word_count`: `47`
- `body_word_count`: `30`

```text
The visual shows a kinematics graph with labeled axes, a piecewise-linear curve, and one marked time interval. Use the velocity-time graph. What integer displacement is shown over the highlighted interval?
Final answer format: set "answer" to the integer displacement over the marked interval.
Example JSON:
{"answer":8}
```

### task_physics__motion_graph__speed_change_state_choice / single / answer_and_annotation / sample 3698599808315339

- `instance_seed`: `3698599808315339`
- `word_count`: `87`
- `body_word_count`: `37`

```text
The figure shows a kinematics graph with labeled axes, a piecewise-linear curve, and one marked time interval. For the highlighted interval, choose the option that describes whether the object speeds up, slows down, or keeps constant speed.
Use this annotation format: set "annotation" to the pixel segment [[x0,y0],[x1,y1]] for the marked velocity-time graph segment.
Use this answer format: set "answer" to the option letter for the speed-change state shown by the marked velocity-time graph interval.
Example JSON:
{"annotation":[[0,0],[4,0]],"answer":"B"}
```

### task_physics__motion_graph__speed_change_state_choice / single / answer_only / sample 3698599808315339

- `instance_seed`: `3698599808315339`
- `word_count`: `63`
- `body_word_count`: `37`

```text
The figure shows a kinematics graph with labeled axes, a piecewise-linear curve, and one marked time interval. For the highlighted interval, choose the option that describes whether the object speeds up, slows down, or keeps constant speed.
Format for the "answer" field: set "answer" to the option letter for the speed-change state shown by the marked velocity-time graph interval.
Example JSON:
{"answer":"B"}
```

### task_physics__orbital_motion__focus_location_label / single / answer_and_annotation / sample 8686417849035717

- `instance_seed`: `8686417849035717`
- `word_count`: `65`
- `body_word_count`: `17`

```text
The image shows an elliptical orbit with labeled candidate points. Which labeled point is the focus location?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the selected focus candidate marker.
Format for the "answer" field: set "answer" to the label of the candidate point that can be the Sun at a focus.
Example JSON:
{"annotation":[120,140],"answer":"B"}
```

### task_physics__orbital_motion__focus_location_label / single / answer_only / sample 8686417849035717

- `instance_seed`: `8686417849035717`
- `word_count`: `41`
- `body_word_count`: `17`

```text
The image shows an elliptical orbit with labeled candidate points. Which labeled point is the focus location?
Final answer format: set "answer" to the label of the candidate point that can be the Sun at a focus.
Example JSON:
{"answer":"B"}
```

### task_physics__orbital_motion__orbital_speed_extremum_label / greatest_speed_position_label / answer_and_annotation / sample 5443476364904398

- `instance_seed`: `5443476364904398`
- `word_count`: `59`
- `body_word_count`: `19`

```text
This orbit diagram shows an elliptical orbit with labeled candidate points. Which labeled position has the greatest orbital speed?
Final answer format: set "answer" to the label of the planet position with greatest speed.
Annotation format: set "annotation" to one [x,y] pixel point at the center of the selected planet-position marker.
Example JSON:
{"annotation":[120,140],"answer":"B"}
```

### task_physics__orbital_motion__orbital_speed_extremum_label / greatest_speed_position_label / answer_only / sample 5443476364904398

- `instance_seed`: `5443476364904398`
- `word_count`: `38`
- `body_word_count`: `19`

```text
This orbit diagram shows an elliptical orbit with labeled candidate points. Which labeled position has the greatest orbital speed?
Required answer format: set "answer" to the label of the planet position with greatest speed.
Example JSON:
{"answer":"B"}
```

### task_physics__orbital_motion__orbital_speed_extremum_label / least_speed_position_label / answer_and_annotation / sample 779458903808380

- `instance_seed`: `779458903808380`
- `word_count`: `61`
- `body_word_count`: `21`

```text
This orbit diagram shows an elliptical orbit with labeled candidate points. At which labeled planet position is the orbital speed least?
Annotation format: set "annotation" to one [x,y] pixel point at the center of the selected planet-position marker.
Required answer format: set "answer" to the label of the planet position with least speed.
Example JSON:
{"annotation":[120,140],"answer":"B"}
```

### task_physics__orbital_motion__orbital_speed_extremum_label / least_speed_position_label / answer_only / sample 779458903808380

- `instance_seed`: `779458903808380`
- `word_count`: `40`
- `body_word_count`: `21`

```text
This orbit diagram shows an elliptical orbit with labeled candidate points. At which labeled planet position is the orbital speed least?
Required answer format: set "answer" to the label of the planet position with least speed.
Example JSON:
{"answer":"B"}
```

### task_physics__piston_cylinder__boundary_work_value / single / answer_and_annotation / sample 318230679367448

- `instance_seed`: `318230679367448`
- `word_count`: `123`
- `body_word_count`: `51`

```text
The piston-cylinder diagram shows a piston-cylinder apparatus shown in initial and final states, with constant pressure in MPa, initial and final volumes in liters, and a process arrow. Compute the signed boundary work for the constant-pressure piston process. Use W = P x (V_final - V_initial) and 1 MPa x L = 1 kJ.
Annotation format: set "annotation" to an object with keys "pressure_readout", "initial_cylinder", and "final_cylinder", each mapped to one [x0,y0,x1,y1] pixel box.
Format for the "answer" field: set "answer" to the signed integer boundary work in kJ, using work done by the gas as positive.
Example JSON:
{"annotation":{"pressure_readout":[2.5,3,4.5,5],"initial_cylinder":[3,4.5,5,6],"final_cylinder":[4.5,5.5,6.5,7]},"answer":8}
```

### task_physics__piston_cylinder__boundary_work_value / single / answer_only / sample 318230679367448

- `instance_seed`: `318230679367448`
- `word_count`: `76`
- `body_word_count`: `51`

```text
The piston-cylinder diagram shows a piston-cylinder apparatus shown in initial and final states, with constant pressure in MPa, initial and final volumes in liters, and a process arrow. Compute the signed boundary work for the constant-pressure piston process. Use W = P x (V_final - V_initial) and 1 MPa x L = 1 kJ.
Final answer format: set "answer" to the signed integer boundary work in kJ, using work done by the gas as positive.
Example JSON:
{"answer":8}
```

### task_physics__pulley__pulley_mechanical_advantage / missing_effort_force_value / answer_and_annotation / sample 8392343379776275

- `instance_seed`: `8392343379776275`
- `word_count`: `89`
- `body_word_count`: `33`

```text
The visual shows one ideal pulley setup where full vertical strands support the moving lower block. Using the shown load force and the full supporting rope strands, what is the missing effort force?
Annotation format: set "annotation" to an object with keys "supporting_strands_region", "known_force_label", and "unknown_force_label", each mapped to one [x0, y0, x1, y1] pixel box.
Format for the "answer" field: set "answer" to the requested integer force value.
Example JSON:
{"annotation":{"supporting_strands_region":[2,3,4,5],"known_force_label":[3,4,5,6],"unknown_force_label":[4,5,6,7]},"answer":8}
```

### task_physics__pulley__pulley_mechanical_advantage / missing_effort_force_value / answer_only / sample 8392343379776275

- `instance_seed`: `8392343379776275`
- `word_count`: `50`
- `body_word_count`: `33`

```text
The visual shows one ideal pulley setup where full vertical strands support the moving lower block. Using the shown load force and the full supporting rope strands, what is the missing effort force?
Format for the "answer" field: set "answer" to the requested integer force value.
Example JSON:
{"answer":8}
```

### task_physics__pulley__pulley_mechanical_advantage / missing_load_force_value / answer_and_annotation / sample 1959271984883814

- `instance_seed`: `1959271984883814`
- `word_count`: `81`
- `body_word_count`: `27`

```text
The visual shows one ideal pulley setup where full vertical strands support the moving lower block. What load force corresponds to the shown effort and supporting strands?
Final answer format: set "answer" to the requested integer force value.
Annotation format: set "annotation" to an object with keys "supporting_strands_region", "known_force_label", and "unknown_force_label", each mapped to one [x0, y0, x1, y1] pixel box.
Example JSON:
{"annotation":{"supporting_strands_region":[2,3,4,5],"known_force_label":[3,4,5,6],"unknown_force_label":[4,5,6,7]},"answer":8}
```

### task_physics__pulley__pulley_mechanical_advantage / missing_load_force_value / answer_only / sample 1959271984883814

- `instance_seed`: `1959271984883814`
- `word_count`: `42`
- `body_word_count`: `27`

```text
The visual shows one ideal pulley setup where full vertical strands support the moving lower block. What load force corresponds to the shown effort and supporting strands?
Required answer format: set "answer" to the requested integer force value.
Example JSON:
{"answer":8}
```

### task_physics__pv_diagram__pv_process_sign_choice / single / answer_and_annotation / sample 1664764848762730

- `instance_seed`: `1664764848762730`
- `word_count`: `75`
- `body_word_count`: `28`

```text
The image shows pressure-volume diagrams with pressure on the vertical axis and volume on the horizontal axis. Which labeled process A-H has negative work done by the gas?
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel box around the process arrow in the correct mini diagram.
Answer format: set "answer" to the option letter of the labeled process with the requested work sign.
Example JSON:
{"annotation":[2,3,4,5],"answer":"B"}
```

### task_physics__pv_diagram__pv_process_sign_choice / single / answer_only / sample 1664764848762730

- `instance_seed`: `1664764848762730`
- `word_count`: `50`
- `body_word_count`: `28`

```text
The image shows pressure-volume diagrams with pressure on the vertical axis and volume on the horizontal axis. Which labeled process A-H has negative work done by the gas?
Required answer format: set "answer" to the option letter of the labeled process with the requested work sign.
Example JSON:
{"answer":"B"}
```

### task_physics__pv_diagram__pv_work_value / single / answer_and_annotation / sample 7531384692707561

- `instance_seed`: `7531384692707561`
- `word_count`: `77`
- `body_word_count`: `35`

```text
The image shows pressure-volume diagrams with pressure on the vertical axis and volume on the horizontal axis. What integer value gives the gas work for the highlighted PV path, using pressure times change in volume?
Final answer format: set "answer" to the signed integer work in joules.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel box around the highlighted PV path and shaded work region.
Example JSON:
{"annotation":[2,3,4,5],"answer":8}
```

### task_physics__pv_diagram__pv_work_value / single / answer_only / sample 7531384692707561

- `instance_seed`: `7531384692707561`
- `word_count`: `50`
- `body_word_count`: `35`

```text
The image shows pressure-volume diagrams with pressure on the vertical axis and volume on the horizontal axis. What integer value gives the gas work for the highlighted PV path, using pressure times change in volume?
Answer format: set "answer" to the signed integer work in joules.
Example JSON:
{"answer":8}
```

### task_physics__ray_optics__ray_bounce_count / single / answer_and_annotation / sample 1409680050036112

- `instance_seed`: `1409680050036112`
- `word_count`: `57`
- `body_word_count`: `21`

```text
The visual shows a grid-based mirror ray diagram. What is the total number of mirror bounces in the implied ray path?
Answer format: set "answer" to the mirror-bounce count as an integer.
Annotation format: set "annotation" to an array of [x, y] pixel points at each mirror-bounce point.
Example JSON:
{"annotation":[[0,0],[4,0]],"answer":8}
```

### task_physics__ray_optics__ray_bounce_count / single / answer_only / sample 1409680050036112

- `instance_seed`: `1409680050036112`
- `word_count`: `39`
- `body_word_count`: `21`

```text
The visual shows a grid-based mirror ray diagram. What is the total number of mirror bounces in the implied ray path?
Format for the "answer" field: set "answer" to the mirror-bounce count as an integer.
Example JSON:
{"answer":8}
```

### task_physics__ray_optics__ray_target_hit_count / single / answer_and_annotation / sample 6721942148553542

- `instance_seed`: `6721942148553542`
- `word_count`: `70`
- `body_word_count`: `29`

```text
The image shows a graph-paper ray diagram with an incoming ray and diagonal mirrors. Count the target points touched by the ray path before the ray leaves the grid.
Final answer format: set "answer" to the target-hit count as an integer.
Annotation format: set "annotation" to an array of [x, y] pixel points at each target point touched by the ray.
Example JSON:
{"annotation":[[0,0],[4,0]],"answer":8}
```

### task_physics__ray_optics__ray_target_hit_count / single / answer_only / sample 6721942148553542

- `instance_seed`: `6721942148553542`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The image shows a graph-paper ray diagram with an incoming ray and diagonal mirrors. Count the target points touched by the ray path before the ray leaves the grid.
Answer field: set "answer" to the target-hit count as an integer.
Example JSON:
{"answer":8}
```

### task_physics__refraction_layers__medium_speed_order_label / single / answer_and_annotation / sample 8595730158958516

- `instance_seed`: `8595730158958516`
- `word_count`: `86`
- `body_word_count`: `33`

```text
The diagram shows a ray passing through three labeled media with normals at each interface and visible speed-order options. Choose the option that orders the three media by light speed, fastest to slowest.
Annotation format: set "annotation" to an array of two pixel boxes [x0,y0,x1,y1] around the two ray-bend regions where the ray crosses the media interfaces.
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":[[250,180,390,350],[380,350,520,520]],"answer":"C"}
```

### task_physics__refraction_layers__medium_speed_order_label / single / answer_only / sample 8595730158958516

- `instance_seed`: `8595730158958516`
- `word_count`: `52`
- `body_word_count`: `33`

```text
The diagram shows a ray passing through three labeled media with normals at each interface and visible speed-order options. Choose the option that orders the three media by light speed, fastest to slowest.
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_physics__shadow_cause__light_source_label / single / answer_and_annotation / sample 3148448863752657

- `instance_seed`: `3148448863752657`
- `word_count`: `69`
- `body_word_count`: `26`

```text
The diagram shows a shadow-casting object, a visible shadow, and labeled light-source choices. Select the labeled light source that would produce the shadow from this object.
Annotation format: set "annotation" to one pixel box [x0,y0,x1,y1] around the selected labeled light-source option.
Format for the "answer" field: set "answer" to the selected light-source option letter as a string.
Example JSON:
{"annotation":[720,140,810,230],"answer":"D"}
```

### task_physics__shadow_cause__light_source_label / single / answer_only / sample 3148448863752657

- `instance_seed`: `3148448863752657`
- `word_count`: `43`
- `body_word_count`: `26`

```text
The diagram shows a shadow-casting object, a visible shadow, and labeled light-source choices. Select the labeled light source that would produce the shadow from this object.
Answer format: set "answer" to the selected light-source option letter as a string.
Example JSON:
{"answer":"D"}
```

### task_physics__signal_transform__periodic_harmonic_spectrum_match_label / single / answer_and_annotation / sample 1171429282298171

- `instance_seed`: `1171429282298171`
- `word_count`: `84`
- `body_word_count`: `22`

```text
The image contains one waveform panel with four visual frequency-spectrum options. Which spectrum panel is the correct match for the input signal?
Annotation format: set "annotation" to an object with keys "input_waveform" and "selected_spectrum"; each value is a pixel bounding box [x0,y0,x1,y1] around the input waveform panel or the matching spectrum option panel.
Answer format: set "answer" to the matching spectrum option letter as a string.
Example JSON:
{"annotation":{"input_waveform":[92,112,1188,306],"selected_spectrum":[465,346,803,544]},"answer":"B"}
```

### task_physics__signal_transform__periodic_harmonic_spectrum_match_label / single / answer_only / sample 1171429282298171

- `instance_seed`: `1171429282298171`
- `word_count`: `39`
- `body_word_count`: `35`

```text
The image contains one waveform panel with four visual frequency-spectrum options. Which spectrum panel is the correct match for the input signal?
Answer field: set "answer" to the matching spectrum option letter as a string.
Example JSON:
{"answer":"B"}
```

### task_physics__spring__spring_extension_difference / single / answer_and_annotation / sample 6977739497089455

- `instance_seed`: `6977739497089455`
- `word_count`: `71`
- `body_word_count`: `28`

```text
The figure shows a pair of identical springs with weight blocks and ruler markers. Using the two ruler markers, what integer difference in extension do the springs show?
Answer format: set "answer" to the integer extension difference.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around the two extension markers being compared.
Example JSON:
{"annotation":[[210,217,260,249],[620,269,670,301]],"answer":4}
```

### task_physics__spring__spring_extension_difference / single / answer_only / sample 6977739497089455

- `instance_seed`: `6977739497089455`
- `word_count`: `44`
- `body_word_count`: `28`

```text
The figure shows a pair of identical springs with weight blocks and ruler markers. Using the two ruler markers, what integer difference in extension do the springs show?
Format for the "answer" field: set "answer" to the integer extension difference.
Example JSON:
{"answer":4}
```

### task_physics__spring__spring_missing_value / missing_extension_for_weight / answer_and_annotation / sample 1040194442546001

- `instance_seed`: `1040194442546001`
- `word_count`: `95`
- `body_word_count`: `23`

```text
The figure shows a pair of identical springs with weight blocks and ruler markers. Determine the missing right-side extension from the identical-spring diagram.
Annotation format: set "annotation" to an object with keys "reference_weight", "reference_extension", "query_weight", and "query_extension"; each value is a [x0,y0,x1,y1] pixel box around the corresponding weight block or extension marker.
Format for the "answer" field: set "answer" to the integer missing weight or extension value.
Example JSON:
{"annotation":{"reference_weight":[170,342,248,396],"reference_extension":[204,241,256,273],"query_weight":[595,226,647,260],"query_extension":[598,293,650,325]},"answer":4}
```

### task_physics__spring__spring_missing_value / missing_extension_for_weight / answer_only / sample 1040194442546001

- `instance_seed`: `1040194442546001`
- `word_count`: `40`
- `body_word_count`: `23`

```text
The figure shows a pair of identical springs with weight blocks and ruler markers. Determine the missing right-side extension from the identical-spring diagram.
Final answer format: set "answer" to the integer missing weight or extension value.
Example JSON:
{"answer":4}
```

### task_physics__spring__spring_missing_value / missing_weight_for_extension / answer_and_annotation / sample 2957435647730391

- `instance_seed`: `2957435647730391`
- `word_count`: `96`
- `body_word_count`: `26`

```text
The visual shows two matching spring setups with extension rulers. The two springs are identical. What integer weight belongs at the marked `?` on the right spring?
Final answer format: set "answer" to the integer missing weight or extension value.
Annotation format: set "annotation" to an object with keys "reference_weight", "reference_extension", "query_weight", and "query_extension"; each value is a [x0,y0,x1,y1] pixel box around the corresponding weight block or extension marker.
Example JSON:
{"annotation":{"reference_weight":[170,342,248,396],"reference_extension":[204,241,256,273],"query_weight":[595,226,647,260],"query_extension":[598,293,650,325]},"answer":4}
```

### task_physics__spring__spring_missing_value / missing_weight_for_extension / answer_only / sample 2957435647730391

- `instance_seed`: `2957435647730391`
- `word_count`: `42`
- `body_word_count`: `38`

```text
The visual shows two matching spring setups with extension rulers. The two springs are identical. What integer weight belongs at the marked `?` on the right spring?
Answer field: set "answer" to the integer missing weight or extension value.
Example JSON:
{"answer":4}
```

### task_physics__stack_stability__stability_status_label / stable_stack_label / answer_and_annotation / sample 2070844570073822

- `instance_seed`: `2070844570073822`
- `word_count`: `70`
- `body_word_count`: `23`

```text
The visual shows labeled brick stacks with red COM markers and support-footprint brackets. Which option shows a stack that will not tip over?
Annotation format: set "annotation" to a [x0,y0,x1,y1] pixel box around the selected stack, including its COM marker, projection line, and support bracket.
Required answer format: set "answer" to the selected stack letter as a string.
Example JSON:
{"annotation":[196,214,276,382],"answer":"D"}
```

### task_physics__stack_stability__stability_status_label / stable_stack_label / answer_only / sample 2070844570073822

- `instance_seed`: `2070844570073822`
- `word_count`: `39`
- `body_word_count`: `23`

```text
The visual shows labeled brick stacks with red COM markers and support-footprint brackets. Which option shows a stack that will not tip over?
Answer format: set "answer" to the selected stack letter as a string.
Example JSON:
{"answer":"D"}
```

### task_physics__stack_stability__stability_status_label / tipping_stack_label / answer_and_annotation / sample 5937420712532074

- `instance_seed`: `5937420712532074`
- `word_count`: `75`
- `body_word_count`: `28`

```text
The visual shows labeled brick stacks with red COM markers and support-footprint brackets. Which labeled stack will tip over because its center-of-mass projection falls outside its support base?
Final answer format: set "answer" to the selected stack letter as a string.
Annotation format: set "annotation" to a [x0,y0,x1,y1] pixel box around the selected stack, including its COM marker, projection line, and support bracket.
Example JSON:
{"annotation":[196,214,276,382],"answer":"D"}
```

### task_physics__stack_stability__stability_status_label / tipping_stack_label / answer_only / sample 5937420712532074

- `instance_seed`: `5937420712532074`
- `word_count`: `45`
- `body_word_count`: `28`

```text
The visual shows labeled brick stacks with red COM markers and support-footprint brackets. Which labeled stack will tip over because its center-of-mass projection falls outside its support base?
Final answer format: set "answer" to the selected stack letter as a string.
Example JSON:
{"answer":"D"}
```

### task_physics__switch_circuit__lit_bulb_count / single / answer_and_annotation / sample 2621975561873355

- `instance_seed`: `2621975561873355`
- `word_count`: `90`
- `body_word_count`: `32`

```text
This circuit diagram shows a mixed branch battery circuit with five labeled bulbs and visibly open or closed switches. Determine the number of bulbs that will be on in this switch circuit.
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around every bulb symbol that will be on; use [] if no bulbs will be on.
Answer format: set "answer" to the number of bulbs that will be on as an integer.
Example JSON:
{"annotation":[[120,140,180,200],[240,140,300,200]],"answer":2}
```

### task_physics__switch_circuit__lit_bulb_count / single / answer_only / sample 2621975561873355

- `instance_seed`: `2621975561873355`
- `word_count`: `52`
- `body_word_count`: `48`

```text
This circuit diagram shows a mixed branch battery circuit with five labeled bulbs and visibly open or closed switches. Determine the number of bulbs that will be on in this switch circuit.
Answer field: set "answer" to the number of bulbs that will be on as an integer.
Example JSON:
{"answer":2}
```

### task_physics__thermal_mixing__final_temperature_value / single / answer_and_annotation / sample 8825707600064752

- `instance_seed`: `8825707600064752`
- `word_count`: `96`
- `body_word_count`: `43`

```text
The diagram shows separate liquid cups with visible Celsius temperature labels being poured into one insulated mixing container. The cups contain equal amounts of the same liquid and are mixed in the insulated container. What is the final equilibrium temperature in degrees Celsius?
Annotation format: set "annotation" to an array of [x0,y0,x1,y1] pixel boxes around each visible initial temperature label used to compute the final temperature.
Required answer format: set "answer" to the integer final equilibrium temperature in degrees Celsius.
Example JSON:
{"annotation":[[130,230,190,270],[310,230,370,270]],"answer":45}
```

### task_physics__thermal_mixing__final_temperature_value / single / answer_only / sample 8825707600064752

- `instance_seed`: `8825707600064752`
- `word_count`: `61`
- `body_word_count`: `43`

```text
The diagram shows separate liquid cups with visible Celsius temperature labels being poured into one insulated mixing container. The cups contain equal amounts of the same liquid and are mixed in the insulated container. What is the final equilibrium temperature in degrees Celsius?
Final answer format: set "answer" to the integer final equilibrium temperature in degrees Celsius.
Example JSON:
{"answer":45}
```

### task_physics__thermometer__temperature_conversion_value / celsius_to_fahrenheit_value / answer_and_annotation / sample 1425701902311176

- `instance_seed`: `1425701902311176`
- `word_count`: `80`
- `body_word_count`: `39`

```text
The thermometer diagram shows a vertical thermometer with a visible liquid level, numeric tick scale, and source temperature unit label. What is the displayed thermometer temperature in degrees Fahrenheit? Read the Celsius scale and use F = 9C/5 + 32.
Use this annotation format: set "annotation" to a segment [[x0,y0],[x1,y1]] along the visible liquid level.
Use this answer format: set "answer" to the integer equivalent temperature in degrees Fahrenheit.
Example JSON:
{"annotation":[[522,280],[578,280]],"answer":77}
```

### task_physics__thermometer__temperature_conversion_value / celsius_to_fahrenheit_value / answer_only / sample 1425701902311176

- `instance_seed`: `1425701902311176`
- `word_count`: `55`
- `body_word_count`: `51`

```text
The thermometer diagram shows a vertical thermometer with a visible liquid level, numeric tick scale, and source temperature unit label. What is the displayed thermometer temperature in degrees Fahrenheit? Read the Celsius scale and use F = 9C/5 + 32.
Answer field: set "answer" to the integer equivalent temperature in degrees Fahrenheit.
Example JSON:
{"answer":77}
```

### task_physics__thermometer__temperature_conversion_value / fahrenheit_to_celsius_value / answer_and_annotation / sample 2597323194375825

- `instance_seed`: `2597323194375825`
- `word_count`: `80`
- `body_word_count`: `43`

```text
This figure shows a vertical thermometer with a visible liquid level, numeric tick scale, and source temperature unit label. Read the Fahrenheit temperature from the thermometer and convert it to Celsius using C = 5(F - 32)/9. What integer Celsius temperature is equivalent?
Annotation format: set "annotation" to a segment [[x0,y0],[x1,y1]] along the visible liquid level.
Answer format: set "answer" to the integer equivalent temperature in degrees Celsius.
Example JSON:
{"annotation":[[522,350],[578,350]],"answer":20}
```

### task_physics__thermometer__temperature_conversion_value / fahrenheit_to_celsius_value / answer_only / sample 2597323194375825

- `instance_seed`: `2597323194375825`
- `word_count`: `62`
- `body_word_count`: `43`

```text
This figure shows a vertical thermometer with a visible liquid level, numeric tick scale, and source temperature unit label. Read the Fahrenheit temperature from the thermometer and convert it to Celsius using C = 5(F - 32)/9. What integer Celsius temperature is equivalent?
Format for the "answer" field: set "answer" to the integer equivalent temperature in degrees Celsius.
Example JSON:
{"answer":20}
```

### task_physics__vernier_caliper__length_readout_value / single / answer_and_annotation / sample 4548728908108208

- `instance_seed`: `4548728908108208`
- `word_count`: `111`
- `body_word_count`: `46`

```text
The figure shows a Vernier caliper measuring an object, with a main scale in millimeters, a sliding vernier scale, and a 0.1 mm vernier resolution. Use the main millimeter scale and the aligned vernier tick to read the caliper. What length is shown in mm?
Format for the "annotation" field: set "annotation" to an object with keys "vernier_zero_tick" and "aligned_vernier_tick", each mapped to one [x,y] pixel point at the center of that tick mark.
Format for the "answer" field: set "answer" to the measured length in millimeters as a number with one decimal place and no unit.
Example JSON:
{"annotation":{"vernier_zero_tick":[410,356],"aligned_vernier_tick":[456,358]},"answer":23.4}
```

### task_physics__vernier_caliper__length_readout_value / single / answer_only / sample 4548728908108208

- `instance_seed`: `4548728908108208`
- `word_count`: `71`
- `body_word_count`: `66`

```text
The figure shows a Vernier caliper measuring an object, with a main scale in millimeters, a sliding vernier scale, and a 0.1 mm vernier resolution. Use the main millimeter scale and the aligned vernier tick to read the caliper. What length is shown in mm?
Answer field: set "answer" to the measured length in millimeters as a number with one decimal place and no unit.
Example JSON:
{"answer":23.4}
```

### task_physics__wave_interference__interference_point_choice / constructive_interference_point_choice / answer_and_annotation / sample 2682866947769061

- `instance_seed`: `2682866947769061`
- `word_count`: `76`
- `body_word_count`: `33`

```text
The image shows a two-source ripple-tank interference diagram with circular crest and trough wavefronts. Select the labeled candidate point where the wavefronts produce constructive interference. Use the diagram's visible wavefront spacing and labels.
Annotation format: set "annotation" to one pixel point [x,y] at the center of the labeled candidate point matching the requested interference condition.
Answer format: set "answer" to the matching candidate point letter as a string.
Example JSON:
{"annotation":[247,225],"answer":"B"}
```

### task_physics__wave_interference__interference_point_choice / constructive_interference_point_choice / answer_only / sample 2682866947769061

- `instance_seed`: `2682866947769061`
- `word_count`: `51`
- `body_word_count`: `33`

```text
The image shows a two-source ripple-tank interference diagram with circular crest and trough wavefronts. Select the labeled candidate point where the wavefronts produce constructive interference. Use the diagram's visible wavefront spacing and labels.
Final answer format: set "answer" to the matching candidate point letter as a string.
Example JSON:
{"answer":"B"}
```

### task_physics__wave_interference__interference_point_choice / destructive_interference_point_choice / answer_and_annotation / sample 3925902700163581

- `instance_seed`: `3925902700163581`
- `word_count`: `82`
- `body_word_count`: `38`

```text
The image shows a two-source ripple-tank interference diagram with circular crest and trough wavefronts. Compare the two source phases at each candidate. Which point gives destructive interference? Base the answer on the shown source phase and ring spacing.
Final answer format: set "answer" to the matching candidate point letter as a string.
Annotation format: set "annotation" to one pixel point [x,y] at the center of the labeled candidate point matching the requested interference condition.
Example JSON:
{"annotation":[247,225],"answer":"B"}
```

### task_physics__wave_interference__interference_point_choice / destructive_interference_point_choice / answer_only / sample 3925902700163581

- `instance_seed`: `3925902700163581`
- `word_count`: `56`
- `body_word_count`: `38`

```text
The image shows a two-source ripple-tank interference diagram with circular crest and trough wavefronts. Compare the two source phases at each candidate. Which point gives destructive interference? Base the answer on the shown source phase and ring spacing.
Final answer format: set "answer" to the matching candidate point letter as a string.
Example JSON:
{"answer":"B"}
```

### task_physics__wave_interference__path_difference_value / single / answer_and_annotation / sample 3175647975572170

- `instance_seed`: `3175647975572170`
- `word_count`: `98`
- `body_word_count`: `41`

```text
This figure shows a ripple-tank wave-interference pattern from two labeled sources. Read the two labeled guided paths to P. What integer path difference do they show in lambda/2 steps? Base the answer on the shown source phase and ring spacing.
Use this annotation format: set "annotation" to an array of two source-to-P pixel segments; each segment is [[x0,y0],[x1,y1]] and endpoint order does not matter.
Use this answer format: set "answer" to the integer absolute path difference counted in lambda/2 steps.
Example JSON:
{"annotation":[[[212,164],[486,356]],[[754,184],[486,356]]],"answer":3}
```

### task_physics__wave_interference__path_difference_value / single / answer_only / sample 3175647975572170

- `instance_seed`: `3175647975572170`
- `word_count`: `63`
- `body_word_count`: `41`

```text
This figure shows a ripple-tank wave-interference pattern from two labeled sources. Read the two labeled guided paths to P. What integer path difference do they show in lambda/2 steps? Base the answer on the shown source phase and ring spacing.
Format for the "answer" field: set "answer" to the integer absolute path difference counted in lambda/2 steps.
Example JSON:
{"answer":3}
```

### task_physics__waveform_panel__wave_property_extremum_label / highest_amplitude_label / answer_and_annotation / sample 1672561260925687

- `instance_seed`: `1672561260925687`
- `word_count`: `71`
- `body_word_count`: `30`

```text
This figure shows several labeled sinusoidal waveforms arranged in panels. Select the panel that matches the requested wave comparison. Choose the panel with the tallest wave from midline to crest.
Required annotation format: set "annotation" to one pixel bounding box [x0,y0,x1,y1] around the selected waveform panel.
Required answer format: set "answer" to the selected panel letter as a string.
Example JSON:
{"annotation":[112,120,1010,230],"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / highest_amplitude_label / answer_only / sample 1672561260925687

- `instance_seed`: `1672561260925687`
- `word_count`: `49`
- `body_word_count`: `30`

```text
This figure shows several labeled sinusoidal waveforms arranged in panels. Select the panel that matches the requested wave comparison. Choose the panel with the tallest wave from midline to crest.
Format for the "answer" field: set "answer" to the selected panel letter as a string.
Example JSON:
{"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / highest_frequency_label / answer_and_annotation / sample 7402748236030217

- `instance_seed`: `7402748236030217`
- `word_count`: `74`
- `body_word_count`: `35`

```text
The image shows stacked labeled sinusoidal waveform panels on a shared horizontal scale. Use the labeled waveform panels to answer the comparison question. Which labeled panel packs the most cycles into the same horizontal span?
Answer format: set "answer" to the selected panel letter as a string.
Annotation format: set "annotation" to one pixel bounding box [x0,y0,x1,y1] around the selected waveform panel.
Example JSON:
{"annotation":[112,120,1010,230],"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / highest_frequency_label / answer_only / sample 7402748236030217

- `instance_seed`: `7402748236030217`
- `word_count`: `52`
- `body_word_count`: `35`

```text
The image shows stacked labeled sinusoidal waveform panels on a shared horizontal scale. Use the labeled waveform panels to answer the comparison question. Which labeled panel packs the most cycles into the same horizontal span?
Final answer format: set "answer" to the selected panel letter as a string.
Example JSON:
{"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / longest_wavelength_label / answer_and_annotation / sample 4434726902090747

- `instance_seed`: `4434726902090747`
- `word_count`: `74`
- `body_word_count`: `31`

```text
The image shows stacked labeled sinusoidal waveform panels on a shared horizontal scale. Select the panel that matches the requested wave comparison. Which labeled panel has the widest spacing between cycles?
Use this annotation format: set "annotation" to one pixel bounding box [x0,y0,x1,y1] around the selected waveform panel.
Use this answer format: set "answer" to the selected panel letter as a string.
Example JSON:
{"annotation":[112,120,1010,230],"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / longest_wavelength_label / answer_only / sample 4434726902090747

- `instance_seed`: `4434726902090747`
- `word_count`: `48`
- `body_word_count`: `31`

```text
The image shows stacked labeled sinusoidal waveform panels on a shared horizontal scale. Select the panel that matches the requested wave comparison. Which labeled panel has the widest spacing between cycles?
Final answer format: set "answer" to the selected panel letter as a string.
Example JSON:
{"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / lowest_amplitude_label / answer_and_annotation / sample 1201463234991844

- `instance_seed`: `1201463234991844`
- `word_count`: `74`
- `body_word_count`: `34`

```text
The diagram shows labeled waveform panels with visible midlines and shared horizontal span. Compare the displayed waveforms and choose the correct panel label. Choose the panel with the shortest wave from midline to crest.
Final answer format: set "answer" to the selected panel letter as a string.
Annotation format: set "annotation" to one pixel bounding box [x0,y0,x1,y1] around the selected waveform panel.
Example JSON:
{"annotation":[112,120,1010,230],"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / lowest_amplitude_label / answer_only / sample 1201463234991844

- `instance_seed`: `1201463234991844`
- `word_count`: `53`
- `body_word_count`: `34`

```text
The diagram shows labeled waveform panels with visible midlines and shared horizontal span. Compare the displayed waveforms and choose the correct panel label. Choose the panel with the shortest wave from midline to crest.
Format for the "answer" field: set "answer" to the selected panel letter as a string.
Example JSON:
{"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / lowest_frequency_label / answer_and_annotation / sample 8288663193516749

- `instance_seed`: `8288663193516749`
- `word_count`: `68`
- `body_word_count`: `29`

```text
The waveform diagram shows labeled panels drawn on the same horizontal scale. Use the labeled waveform panels to answer the comparison question. Choose the waveform with the lowest frequency.
Answer format: set "answer" to the selected panel letter as a string.
Annotation format: set "annotation" to one pixel bounding box [x0,y0,x1,y1] around the selected waveform panel.
Example JSON:
{"annotation":[112,120,1010,230],"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / lowest_frequency_label / answer_only / sample 8288663193516749

- `instance_seed`: `8288663193516749`
- `word_count`: `48`
- `body_word_count`: `29`

```text
The waveform diagram shows labeled panels drawn on the same horizontal scale. Use the labeled waveform panels to answer the comparison question. Choose the waveform with the lowest frequency.
Format for the "answer" field: set "answer" to the selected panel letter as a string.
Example JSON:
{"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / shortest_wavelength_label / answer_and_annotation / sample 6121371226344948

- `instance_seed`: `6121371226344948`
- `word_count`: `69`
- `body_word_count`: `26`

```text
This figure shows several labeled sinusoidal waveforms arranged in panels. Identify the waveform panel that satisfies the requested property. Choose the waveform with the shortest wavelength.
Use this annotation format: set "annotation" to one pixel bounding box [x0,y0,x1,y1] around the selected waveform panel.
Use this answer format: set "answer" to the selected panel letter as a string.
Example JSON:
{"annotation":[112,120,1010,230],"answer":"C"}
```

### task_physics__waveform_panel__wave_property_extremum_label / shortest_wavelength_label / answer_only / sample 6121371226344948

- `instance_seed`: `6121371226344948`
- `word_count`: `43`
- `body_word_count`: `26`

```text
This figure shows several labeled sinusoidal waveforms arranged in panels. Identify the waveform panel that satisfies the requested property. Choose the waveform with the shortest wavelength.
Required answer format: set "answer" to the selected panel letter as a string.
Example JSON:
{"answer":"C"}
```

### task_physics__wire_magnetism__wire_field_direction_choice / single / answer_and_annotation / sample 254546326579789

- `instance_seed`: `254546326579789`
- `word_count`: `95`
- `body_word_count`: `41`

```text
The image shows a current-carrying wire with a marked point P and labeled direction options. Use the current arrow and the position of point P to select the field-direction option. Which option gives the magnetic-field direction around the wire at P?
Annotation format: set "annotation" to an object with keys "wire_current" and "point_p"; each value is a pixel bounding box [x0,y0,x1,y1] around that visual witness.
Answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":{"wire_current":[170,310,610,390],"point_p":[360,165,420,238]},"answer":"C"}
```

### task_physics__wire_magnetism__wire_field_direction_choice / single / answer_only / sample 254546326579789

- `instance_seed`: `254546326579789`
- `word_count`: `60`
- `body_word_count`: `41`

```text
The image shows a current-carrying wire with a marked point P and labeled direction options. Use the current arrow and the position of point P to select the field-direction option. Which option gives the magnetic-field direction around the wire at P?
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

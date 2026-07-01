# Annotation Projection Validation

- sampled instances: `148`
- query ids covered: `74`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 40, 'bbox_map': 42, 'bbox_set': 16, 'bbox_set_map': 2, 'point': 10, 'point_map': 12, 'point_set': 4, 'segment': 16, 'segment_set': 6}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_physics__analog_meter__meter_readout_value | `ammeter_readout, voltmeter_readout` | `{'ammeter_readout': 2, 'voltmeter_readout': 2}` | 4 | `` |
| task_physics__bridge_circuit__bridge_missing_resistance_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__bulb_circuit__brightness_extremum_label | `brightest_bulb_label, dimmest_bulb_label` | `{'brightest_bulb_label': 2, 'dimmest_bulb_label': 2}` | 4 | `` |
| task_physics__buoyancy_density__object_density_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__circuit_equivalent__total_capacitance_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__circuit_equivalent__total_resistance_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__circuit_state_change__bulb_brightness_change_label | `brightens_after_switch_change, dims_after_switch_change, turns_off_after_switch_change, turns_on_after_switch_change` | `{'brightens_after_switch_change': 2, 'dims_after_switch_change': 2, 'turns_off_after_switch_change': 2, 'turns_on_after_switch_change': 2}` | 8 | `` |
| task_physics__collision__sticky_collision_direction_choice | `single` | `{'single': 2}` | 3 | `` |
| task_physics__collision__sticky_collision_speed_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__electromagnetic_induction__induced_current_direction_count | `clockwise_induced_current_count, counterclockwise_induced_current_count, no_induced_current_count` | `{'clockwise_induced_current_count': 2, 'counterclockwise_induced_current_count': 2, 'no_induced_current_count': 2}` | 6 | `` |
| task_physics__electrostatic_field__field_direction_choice | `electric_field_direction, force_on_negative_charge, force_on_positive_charge` | `{'electric_field_direction': 2, 'force_on_negative_charge': 2, 'force_on_positive_charge': 2}` | 6 | `` |
| task_physics__electrostatic_field__potential_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__electrostatic_field__zero_field_point_label | `single` | `{'single': 2}` | 3 | `` |
| task_physics__fluid_flow__continuity_speed_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__free_body_forces__net_force_direction_choice | `single` | `{'single': 2}` | 3 | `` |
| task_physics__gear_train__output_direction_label | `single` | `{'single': 2}` | 3 | `` |
| task_physics__gear_train__output_speed_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__graduated_cylinder__displacement_volume_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__graduated_cylinder__volume_readout_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__hydraulic__hydraulic_missing_value | `missing_input_area, missing_input_force, missing_output_force, missing_piston_area` | `{'missing_input_area': 2, 'missing_input_force': 2, 'missing_output_force': 2, 'missing_piston_area': 2}` | 8 | `` |
| task_physics__lens_optics__image_property_choice | `single` | `{'single': 2}` | 3 | `` |
| task_physics__lever__missing_weight_balance_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__lever__side_torque_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__magnetic_force__force_direction_choice | `single` | `{'single': 2}` | 3 | `` |
| task_physics__manometer__pressure_difference_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__motion_graph__average_speed_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__motion_graph__interval_displacement_value | `constant_acceleration_interval_displacement, constant_velocity_interval_displacement` | `{'constant_acceleration_interval_displacement': 2, 'constant_velocity_interval_displacement': 2}` | 4 | `` |
| task_physics__motion_graph__speed_change_state_choice | `single` | `{'single': 2}` | 3 | `` |
| task_physics__orbital_motion__focus_location_label | `single` | `{'single': 2}` | 3 | `` |
| task_physics__orbital_motion__orbital_speed_extremum_label | `greatest_speed_position_label, least_speed_position_label` | `{'greatest_speed_position_label': 2, 'least_speed_position_label': 2}` | 4 | `` |
| task_physics__piston_cylinder__boundary_work_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__pulley__pulley_mechanical_advantage | `missing_effort_force_value, missing_load_force_value` | `{'missing_effort_force_value': 2, 'missing_load_force_value': 2}` | 4 | `` |
| task_physics__pv_diagram__pv_process_sign_choice | `single` | `{'single': 2}` | 3 | `` |
| task_physics__pv_diagram__pv_work_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__ray_optics__ray_bounce_count | `single` | `{'single': 2}` | 3 | `` |
| task_physics__ray_optics__ray_target_hit_count | `single` | `{'single': 2}` | 3 | `` |
| task_physics__refraction_layers__medium_speed_order_label | `single` | `{'single': 2}` | 3 | `` |
| task_physics__shadow_cause__light_source_label | `single` | `{'single': 2}` | 3 | `` |
| task_physics__signal_transform__periodic_harmonic_spectrum_match_label | `single` | `{'single': 2}` | 3 | `` |
| task_physics__spring__spring_extension_difference | `single` | `{'single': 2}` | 3 | `` |
| task_physics__spring__spring_missing_value | `missing_extension_for_weight, missing_weight_for_extension` | `{'missing_extension_for_weight': 2, 'missing_weight_for_extension': 2}` | 4 | `` |
| task_physics__stack_stability__stability_status_label | `stable_stack_label, tipping_stack_label` | `{'stable_stack_label': 2, 'tipping_stack_label': 2}` | 4 | `` |
| task_physics__switch_circuit__lit_bulb_count | `single` | `{'single': 2}` | 3 | `` |
| task_physics__thermal_mixing__final_temperature_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__thermometer__temperature_conversion_value | `celsius_to_fahrenheit_value, fahrenheit_to_celsius_value` | `{'celsius_to_fahrenheit_value': 2, 'fahrenheit_to_celsius_value': 2}` | 4 | `` |
| task_physics__vernier_caliper__length_readout_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__wave_interference__interference_point_choice | `constructive_interference_point_choice, destructive_interference_point_choice` | `{'constructive_interference_point_choice': 2, 'destructive_interference_point_choice': 2}` | 4 | `` |
| task_physics__wave_interference__path_difference_value | `single` | `{'single': 2}` | 3 | `` |
| task_physics__waveform_panel__wave_property_extremum_label | `highest_amplitude_label, highest_frequency_label, longest_wavelength_label, lowest_amplitude_label, lowest_frequency_label, shortest_wavelength_label` | `{'highest_amplitude_label': 2, 'highest_frequency_label': 2, 'longest_wavelength_label': 2, 'lowest_amplitude_label': 2, 'lowest_frequency_label': 2, 'shortest_wavelength_label': 2}` | 12 | `` |
| task_physics__wire_magnetism__wire_field_direction_choice | `single` | `{'single': 2}` | 3 | `` |

## Issues

No issues found.

# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-07-01T02:15:24Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `36`
- Tasks: `50`
- Bbox-family runtime tasks: `33`
- Samples inspected: `5000`
- Bboxes inspected: `6711`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| physics | bridge_circuit | `task_physics__bridge_circuit__bridge_missing_resistance_value` | ['bbox'] | 100 | 100 | 158 | 128 | 128 | pass |
| physics | bulb_circuit | `task_physics__bulb_circuit__brightness_extremum_label` | ['bbox'] | 100 | 100 | 72 | 75 | 72 | pass |
| physics | buoyancy_density | `task_physics__buoyancy_density__object_density_value` | ['bbox'] | 100 | 100 | 118 | 88 | 88 | pass |
| physics | circuit_equivalent | `task_physics__circuit_equivalent__total_capacitance_value` | ['bbox'] | 100 | 100 | 1164 | 420 | 420 | pass |
| physics | circuit_equivalent | `task_physics__circuit_equivalent__total_resistance_value` | ['bbox'] | 100 | 100 | 1164 | 420 | 420 | pass |
| physics | circuit_state_change | `task_physics__circuit_state_change__bulb_brightness_change_label` | ['bbox_map'] | 100 | 600 | 68 | 95.5 | 68 | pass |
| physics | electromagnetic_induction | `task_physics__electromagnetic_induction__induced_current_direction_count` | ['bbox_set'] | 100 | 274 | 340 | 336 | 336 | pass |
| physics | fluid_flow | `task_physics__fluid_flow__continuity_speed_value` | ['bbox'] | 100 | 100 | 64 | 31 | 31 | pass |
| physics | free_body_forces | `task_physics__free_body_forces__net_force_direction_choice` | ['bbox_map'] | 100 | 200 | 120 | 92 | 92 | pass |
| physics | gear_train | `task_physics__gear_train__output_direction_label` | ['bbox'] | 100 | 100 | 533 | 378 | 378 | pass |
| physics | gear_train | `task_physics__gear_train__output_speed_value` | ['bbox_map'] | 100 | 200 | 112.924 | 169.102 | 112.924 | pass |
| physics | graduated_cylinder | `task_physics__graduated_cylinder__displacement_volume_value` | ['bbox_map'] | 100 | 200 | 217 | 451 | 217 | pass |
| physics | graduated_cylinder | `task_physics__graduated_cylinder__volume_readout_value` | ['bbox'] | 100 | 100 | 232 | 447 | 232 | pass |
| physics | hydraulic | `task_physics__hydraulic__hydraulic_missing_value` | ['bbox_map'] | 100 | 200 | 173.5 | 430 | 173.5 | pass |
| physics | lens_optics | `task_physics__lens_optics__image_property_choice` | ['bbox_map'] | 100 | 300 | 68 | 70 | 68 | pass |
| physics | lever | `task_physics__lever__missing_weight_balance_value` | ['bbox_set_map'] | 100 | 326 | 58 | 52 | 52 | pass |
| physics | lever | `task_physics__lever__side_torque_value` | ['bbox_set'] | 100 | 260 | 58 | 52 | 52 | pass |
| physics | magnetic_force | `task_physics__magnetic_force__force_direction_choice` | ['bbox_map'] | 100 | 300 | 36 | 36 | 36 | pass |
| physics | manometer | `task_physics__manometer__pressure_difference_value` | ['bbox_map'] | 100 | 200 | 125 | 44 | 44 | pass |
| physics | piston_cylinder | `task_physics__piston_cylinder__boundary_work_value` | ['bbox_map'] | 100 | 300 | 250 | 84 | 84 | pass |
| physics | pulley | `task_physics__pulley__pulley_mechanical_advantage` | ['bbox_map'] | 100 | 300 | 66 | 74 | 66 | pass |
| physics | pv_diagram | `task_physics__pv_diagram__pv_process_sign_choice` | ['bbox'] | 100 | 100 | 48 | 48 | 48 | pass |
| physics | pv_diagram | `task_physics__pv_diagram__pv_work_value` | ['bbox'] | 100 | 100 | 186.666 | 162.5 | 162.5 | pass |
| physics | refraction_layers | `task_physics__refraction_layers__medium_speed_order_label` | ['bbox_set'] | 100 | 200 | 144 | 144 | 144 | pass |
| physics | shadow_cause | `task_physics__shadow_cause__light_source_label` | ['bbox'] | 100 | 100 | 69.56 | 69.56 | 69.56 | pass |
| physics | signal_transform | `task_physics__signal_transform__periodic_harmonic_spectrum_match_label` | ['bbox_map'] | 100 | 200 | 530 | 194 | 194 | pass |
| physics | spring | `task_physics__spring__spring_extension_difference` | ['bbox_set'] | 100 | 200 | 54 | 32 | 32 | pass |
| physics | spring | `task_physics__spring__spring_missing_value` | ['bbox_map'] | 100 | 400 | 54 | 32 | 32 | pass |
| physics | stack_stability | `task_physics__stack_stability__stability_status_label` | ['bbox'] | 100 | 100 | 105.64 | 156 | 105.64 | pass |
| physics | switch_circuit | `task_physics__switch_circuit__lit_bulb_count` | ['bbox_set'] | 100 | 247 | 54 | 54 | 54 | pass |
| physics | thermal_mixing | `task_physics__thermal_mixing__final_temperature_value` | ['bbox_set'] | 100 | 304 | 41 | 32 | 32 | pass |
| physics | waveform_panel | `task_physics__waveform_panel__wave_property_extremum_label` | ['bbox'] | 100 | 100 | 988 | 86.666 | 86.666 | pass |
| physics | wire_magnetism | `task_physics__wire_magnetism__wire_field_direction_choice` | ['bbox_map'] | 100 | 200 | 52 | 72 | 52 | pass |

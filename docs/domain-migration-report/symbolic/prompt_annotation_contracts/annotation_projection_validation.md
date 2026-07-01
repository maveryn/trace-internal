# Annotation Projection Validation

- sampled instances: `69`
- query ids covered: `69`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 24, 'bbox_map': 28, 'bbox_set': 9, 'point': 1, 'point_map': 2, 'point_set_map': 1, 'segment_set': 4}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_symbolic__abacus__displayed_value_readout | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__abacus__target_value_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__agent_automaton__agent_final_pose_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__agent_automaton__future_grid_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__braille_cell__braille_word_read_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__braille_cell__matching_pattern_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__braille_cell__word_braille_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__clock__elapsed_time_value | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__clock__equivalent_time_label | `analog_reference_digital_options, digital_reference_analog_options` | `{'analog_reference_digital_options': 1, 'digital_reference_analog_options': 1}` | 2 | `` |
| task_symbolic__clock__hand_angle_value | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__clock__offset_readout | `minutes_after, minutes_before` | `{'minutes_after': 1, 'minutes_before': 1}` | 2 | `` |
| task_symbolic__clock__sequence_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__clock__time_extremum_label | `earliest_time_label, latest_time_label` | `{'earliest_time_label': 1, 'latest_time_label': 1}` | 2 | `` |
| task_symbolic__dice__dice_conditional_event_value | `conditional_color_given_value_property_probability, conditional_color_given_value_set_probability, conditional_value_property_given_color_probability` | `{'conditional_color_given_value_property_probability': 1, 'conditional_color_given_value_set_probability': 1, 'conditional_value_property_given_color_probability': 1}` | 3 | `` |
| task_symbolic__dice__pair_attribute_combo_probability | `pair_color_value_combo_probability, pair_parity_combo_probability` | `{'pair_color_value_combo_probability': 1, 'pair_parity_combo_probability': 1}` | 2 | `` |
| task_symbolic__dice__pair_difference_probability | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__dice__pair_sum_probability | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__dice__pair_sum_threshold_probability | `pair_sum_at_least_probability, pair_sum_at_most_probability` | `{'pair_sum_at_least_probability': 1, 'pair_sum_at_most_probability': 1}` | 2 | `` |
| task_symbolic__dice__single_attribute_probability | `single_color_and_value_probability, single_color_or_value_probability, single_parity_probability, single_value_set_probability` | `{'single_color_and_value_probability': 1, 'single_color_or_value_probability': 1, 'single_parity_probability': 1, 'single_value_set_probability': 1}` | 4 | `` |
| task_symbolic__dice__single_threshold_probability | `single_value_at_least_probability, single_value_at_most_probability` | `{'single_value_at_least_probability': 1, 'single_value_at_most_probability': 1}` | 2 | `` |
| task_symbolic__life_automaton__life_future_grid_label | `one_step_future_grid, two_step_future_grid` | `{'one_step_future_grid': 1, 'two_step_future_grid': 1}` | 2 | `` |
| task_symbolic__life_automaton__one_step_cell_state_count | `one_step_alive_cell_count, one_step_dead_cell_count` | `{'one_step_alive_cell_count': 1, 'one_step_dead_cell_count': 1}` | 2 | `` |
| task_symbolic__logic_gate_circuit__gate_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__logic_gate_circuit__internal_output_count | `internal_output_one_count, internal_output_zero_count` | `{'internal_output_one_count': 1, 'internal_output_zero_count': 1}` | 2 | `` |
| task_symbolic__logic_gate_circuit__output_value_label | `output_one_label, output_zero_label` | `{'output_one_label': 1, 'output_zero_label': 1}` | 2 | `` |
| task_symbolic__logic_gate_circuit__satisfying_assignment_label | `assignment_outputs_one_label, assignment_outputs_zero_label` | `{'assignment_outputs_one_label': 1, 'assignment_outputs_zero_label': 1}` | 2 | `` |
| task_symbolic__morse_code__morse_word_read_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__morse_code__word_morse_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__articulation_symbol_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__chord_inversion_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__chord_quality_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__duration_equivalence_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__interval_name_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__key_signature_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__meter_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__note_name_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__roman_numeral_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__scale_degree_function_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__scale_validation_count | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__music_staff__transposed_pitch_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__organic_structure__bond_order_count | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__organic_structure__ring_size_count | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__radial_code_wheel__code_output_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__radial_code_wheel__output_code_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__spinner__multi_attribute_and_probability | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__spinner__multi_attribute_or_probability | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__spinner__single_attribute_probability | `single_color_probability, single_shape_probability` | `{'single_color_probability': 1, 'single_shape_probability': 1}` | 2 | `` |
| task_symbolic__spinner__spinner_pair_event_value | `pair_at_least_one_target_color_probability, pair_both_target_color_probability, pair_same_color_probability` | `{'pair_at_least_one_target_color_probability': 1, 'pair_both_target_color_probability': 1, 'pair_same_color_probability': 1}` | 3 | `` |
| task_symbolic__turing_tape__final_head_position_value | `single` | `{'single': 1}` | 2 | `` |
| task_symbolic__turing_tape__turing_written_symbol_count | `single` | `{'single': 1}` | 2 | `` |

## Issues

No issues found.

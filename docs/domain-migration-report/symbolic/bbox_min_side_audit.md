# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-06-29T16:41:32Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `13`
- Tasks: `50`
- Bbox-family runtime tasks: `43`
- Samples inspected: `5000`
- Bboxes inspected: `7926`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| symbolic | abacus | `task_symbolic__abacus__target_value_match_label` | ['bbox'] | 100 | 100 | 340 | 280 | 280 | pass |
| symbolic | agent_automaton | `task_symbolic__agent_automaton__agent_final_pose_label` | ['bbox_map'] | 100 | 200 | 28 | 28 | 28 | pass |
| symbolic | agent_automaton | `task_symbolic__agent_automaton__future_grid_label` | ['bbox_map'] | 100 | 200 | 86 | 92 | 86 | pass |
| symbolic | braille_cell | `task_symbolic__braille_cell__braille_word_read_label` | ['bbox_map'] | 100 | 200 | 260 | 70 | 70 | pass |
| symbolic | braille_cell | `task_symbolic__braille_cell__matching_pattern_label` | ['bbox_map'] | 100 | 200 | 132 | 184 | 132 | pass |
| symbolic | braille_cell | `task_symbolic__braille_cell__word_braille_match_label` | ['bbox_map'] | 100 | 200 | 280 | 80 | 80 | pass |
| symbolic | clock | `task_symbolic__clock__elapsed_time_value` | ['bbox_map'] | 100 | 200 | 236 | 236 | 236 | pass |
| symbolic | clock | `task_symbolic__clock__equivalent_time_label` | ['bbox_map'] | 100 | 200 | 152 | 78 | 78 | pass |
| symbolic | clock | `task_symbolic__clock__sequence_completion_label` | ['bbox_map'] | 100 | 200 | 205 | 220 | 205 | pass |
| symbolic | clock | `task_symbolic__clock__time_extremum_label` | ['bbox'] | 100 | 100 | 168 | 168 | 168 | pass |
| symbolic | dice | `task_symbolic__dice__dice_conditional_event_value` | ['bbox'] | 100 | 100 | 810 | 538 | 538 | pass |
| symbolic | dice | `task_symbolic__dice__pair_attribute_combo_probability` | ['bbox_map'] | 100 | 200 | 454 | 486 | 454 | pass |
| symbolic | dice | `task_symbolic__dice__pair_difference_probability` | ['bbox_map'] | 100 | 200 | 454 | 486 | 454 | pass |
| symbolic | dice | `task_symbolic__dice__pair_sum_probability` | ['bbox_map'] | 100 | 200 | 454 | 486 | 454 | pass |
| symbolic | dice | `task_symbolic__dice__pair_sum_threshold_probability` | ['bbox_map'] | 100 | 200 | 454 | 486 | 454 | pass |
| symbolic | dice | `task_symbolic__dice__single_attribute_probability` | ['bbox'] | 100 | 100 | 810 | 538 | 538 | pass |
| symbolic | dice | `task_symbolic__dice__single_threshold_probability` | ['bbox'] | 100 | 100 | 810 | 538 | 538 | pass |
| symbolic | life_automaton | `task_symbolic__life_automaton__life_future_grid_label` | ['bbox_map'] | 100 | 200 | 86 | 86 | 86 | pass |
| symbolic | life_automaton | `task_symbolic__life_automaton__one_step_cell_state_count` | ['bbox_set'] | 100 | 904 | 28 | 28 | 28 | pass |
| symbolic | logic_gate_circuit | `task_symbolic__logic_gate_circuit__gate_type_count` | ['bbox_set'] | 100 | 192 | 72 | 46 | 46 | pass |
| symbolic | logic_gate_circuit | `task_symbolic__logic_gate_circuit__internal_output_count` | ['bbox_set'] | 100 | 208 | 72 | 46 | 46 | pass |
| symbolic | logic_gate_circuit | `task_symbolic__logic_gate_circuit__output_value_label` | ['bbox'] | 100 | 100 | 525 | 344 | 344 | pass |
| symbolic | logic_gate_circuit | `task_symbolic__logic_gate_circuit__satisfying_assignment_label` | ['bbox_map'] | 100 | 200 | 321 | 93.5 | 93.5 | pass |
| symbolic | morse_code | `task_symbolic__morse_code__morse_word_read_label` | ['bbox_map'] | 100 | 200 | 240 | 70 | 70 | pass |
| symbolic | morse_code | `task_symbolic__morse_code__word_morse_match_label` | ['bbox_map'] | 100 | 200 | 300 | 80 | 80 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__chord_inversion_label` | ['bbox'] | 100 | 100 | 24 | 46 | 24 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__chord_quality_label` | ['bbox'] | 100 | 100 | 25 | 46 | 25 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__duration_equivalence_label` | ['bbox'] | 100 | 100 | 24 | 24 | 24 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__interval_name_label` | ['bbox'] | 100 | 100 | 48 | 86 | 48 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__key_signature_label` | ['bbox'] | 100 | 100 | 24 | 25 | 24 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__meter_type_count` | ['bbox_set'] | 100 | 213 | 66 | 86 | 66 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__note_name_label` | ['bbox'] | 100 | 100 | 25 | 34 | 25 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__roman_numeral_label` | ['bbox_map'] | 100 | 200 | 24 | 25 | 24 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__scale_degree_function_label` | ['bbox_map'] | 100 | 200 | 24 | 25 | 24 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__scale_validation_count` | ['bbox_set'] | 100 | 212 | 119 | 86 | 86 | pass |
| symbolic | music_staff | `task_symbolic__music_staff__transposed_pitch_pair_count` | ['bbox_set'] | 100 | 199 | 96 | 96 | 96 | pass |
| symbolic | organic_structure | `task_symbolic__organic_structure__ring_size_count` | ['bbox_set'] | 100 | 298 | 95.084 | 97.106 | 95.084 | pass |
| symbolic | spinner | `task_symbolic__spinner__multi_attribute_and_probability` | ['bbox'] | 100 | 100 | 538 | 582 | 538 | pass |
| symbolic | spinner | `task_symbolic__spinner__multi_attribute_or_probability` | ['bbox'] | 100 | 100 | 538 | 582 | 538 | pass |
| symbolic | spinner | `task_symbolic__spinner__single_attribute_probability` | ['bbox'] | 100 | 100 | 538 | 582 | 538 | pass |
| symbolic | spinner | `task_symbolic__spinner__spinner_pair_event_value` | ['bbox_map'] | 100 | 200 | 428 | 472 | 428 | pass |
| symbolic | turing_tape | `task_symbolic__turing_tape__final_head_position_value` | ['bbox_map'] | 100 | 200 | 352 | 174 | 174 | pass |
| symbolic | turing_tape | `task_symbolic__turing_tape__turing_written_symbol_count` | ['bbox_map'] | 100 | 200 | 346 | 174 | 174 | pass |

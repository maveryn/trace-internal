# Prompt Concision Audit

- rendered prompts: `138`
- tasks covered: `50`
- observed query ids covered: `69`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
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

## Longest Prompts

### task_symbolic__life_automaton__one_step_cell_state_count / answer_and_annotation / sample 5085608709631324

- `query_id`: `one_step_alive_cell_count`
- `instance_seed`: `5085608709631324`
- `word_count`: `137`
- `body_word_count`: `73`

```text
The visual shows a notebook-style cellular-automaton source grid marked START where dark cells are alive and light cells are empty. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Using the grid marked START as the source grid, how many cells are alive in the next grid?
Required annotation format: set "annotation" to an array of pixel-space bounding boxes [x0, y0, x1, y1], one for each visible source-grid cell that has the requested state after one update; use an empty array if there are none.
Required answer format: set "answer" to the integer count.
Example JSON:
{"annotation":[[322,104,376,158],[380,104,434,158],[322,162,376,216]],"answer":3}
```

### task_symbolic__life_automaton__one_step_cell_state_count / answer_and_annotation / sample 8841333106155841

- `query_id`: `one_step_dead_cell_count`
- `instance_seed`: `8841333106155841`
- `word_count`: `135`
- `body_word_count`: `71`

```text
The Life automaton diagram shows a cellular-automaton source grid marked START where dark cells are alive and light cells are empty. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Starting from the grid marked START, after one update, how many cells will be empty?
Required annotation format: set "annotation" to an array of pixel-space bounding boxes [x0, y0, x1, y1], one for each visible source-grid cell that has the requested state after one update; use an empty array if there are none.
Required answer format: set "answer" to the integer count.
Example JSON:
{"annotation":[[322,104,376,158],[380,104,434,158],[322,162,376,216]],"answer":3}
```

### task_symbolic__agent_automaton__agent_final_pose_label / answer_and_annotation / sample 1847099799238581

- `query_id`: `single`
- `instance_seed`: `1847099799238581`
- `word_count`: `128`
- `body_word_count`: `76`

```text
The automaton panel shows a notebook-style turning-agent automaton grid with an arrow marker showing the starting cell and direction. Three-state rule: before moving, state 0 turns the agent right and advances to 1; state 1 keeps the direction and advances to 2; state 2 turns the agent left and advances to 0; then the agent moves one cell forward, wrapping around the grid edge. After 4 steps. Which option shows the agent's final cell and direction?
Required annotation format: set "annotation" to an object/dictionary with keys "start_marker" and "selected_option"; each key maps to a pixel bounding box [x0,y0,x1,y1].
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"start_marker":[322,136,376,190],"selected_option":[624,512,774,628]},"answer":"C"}
```

### task_symbolic__turing_tape__final_head_position_value / answer_and_annotation / sample 7704511493626341

- `query_id`: `single`
- `instance_seed`: `7704511493626341`
- `word_count`: `128`
- `body_word_count`: `79`

```text
The symbolic machine panel shows a tape-machine automaton with a starting tape, head marker, state label, step count, symbol alphabet, and transition table. Use the diagrammed tape machine and transition table to answer. At each step, find the row with the current state and the symbol under the head, write the new symbol, move the head L or R, and switch to the next state. Follow the tape machine for 5 steps and report the final head cell number.
Final answer format: set "answer" to the 1-based integer tape cell number.
Annotation format: set "annotation" to an object with keys "machine_panel" and "transition_table", each mapped to a bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":{"machine_panel":[248,96,792,238],"transition_table":[316,282,724,536]},"answer":5}
```

### task_symbolic__life_automaton__life_future_grid_label / answer_and_annotation / sample 6311297904959301

- `query_id`: `one_step_future_grid`
- `instance_seed`: `6311297904959301`
- `word_count`: `124`
- `body_word_count`: `73`

```text
The visual shows a cellular-automaton source grid marked START where dark cells are alive and light cells are empty, with labeled future-grid options below. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Starting from the grid marked START, choose the option that matches the next grid.
Required annotation format: set "annotation" to an object/dictionary with keys "source_grid" and "selected_option", each mapped to that pixel bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the single selected option letter.
Example JSON:
{"annotation":{"source_grid":[322,104,718,500],"selected_option":[624,552,774,706]},"answer":"D"}
```

### task_symbolic__turing_tape__turing_written_symbol_count / answer_and_annotation / sample 4473877317529143

- `query_id`: `single`
- `instance_seed`: `4473877317529143`
- `word_count`: `124`
- `body_word_count`: `73`

```text
The visual shows a tape-machine automaton with a starting tape, head marker, state label, step count, symbol alphabet, and transition table. Follow the displayed machine rules exactly. At each step, find the row with the current state and the symbol under the head, write the new symbol, move the head L or R, and switch to the next state. Simulate exactly 6 steps. What is the count of tape cells showing 0 afterward?
Format for the "annotation" field: set "annotation" to an object with keys "machine_panel" and "transition_table", each mapped to a bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the integer count.
Example JSON:
{"annotation":{"machine_panel":[248,96,792,238],"transition_table":[316,282,724,536]},"answer":4}
```

### task_symbolic__dice__pair_attribute_combo_probability / answer_and_annotation / sample 384962803780726

- `query_id`: `pair_parity_combo_probability`
- `instance_seed`: `384962803780726`
- `word_count`: `123`
- `body_word_count`: `69`

```text
The dice tray diagram shows two dice trays labeled Tray A and Tray B. Each die shows a visible top value. Use the two dice trays to compute the requested probability. If one die is chosen from each tray with equal chance among dice in that tray, what is the probability that the Tray A die shows an even value and the Tray B die shows an odd value?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"1/4"}
```

### task_symbolic__agent_automaton__future_grid_label / answer_and_annotation / sample 1811596061539532

- `query_id`: `single`
- `instance_seed`: `1811596061539532`
- `word_count`: `119`
- `body_word_count`: `68`

```text
The visual shows a notebook-style turning-agent automaton grid with an arrow marker showing the starting cell and direction. Binary rule: before moving, a light cell turns the agent right and changes to colored; a colored cell turns the agent left and changes to light; then the agent moves one cell forward, wrapping around the grid edge. Simulate 4 steps. Which option shows the full grid after the updates?
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to an object/dictionary with keys "source_grid" and "selected_option"; each key maps to a pixel bounding box [x0,y0,x1,y1].
Example JSON:
{"annotation":{"source_grid":[322,136,490,304],"selected_option":[624,512,794,682]},"answer":"C"}
```

### task_symbolic__dice__pair_attribute_combo_probability / answer_and_annotation / sample 5551575820267229

- `query_id`: `pair_color_value_combo_probability`
- `instance_seed`: `5551575820267229`
- `word_count`: `116`
- `body_word_count`: `62`

```text
The dice tray diagram shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Answer using the product space formed by one visible die from each tray. Select one die uniformly from each tray. What is the probability that the Tray A die is purple and the Tray B die shows a prime value?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"1/8"}
```

### task_symbolic__dice__pair_sum_threshold_probability / answer_and_annotation / sample 8874693704106542

- `query_id`: `pair_sum_at_most_probability`
- `instance_seed`: `8874693704106542`
- `word_count`: `116`
- `body_word_count`: `60`

```text
The figure shows two notebook-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Compute the probability from the visible top faces in both trays. If one die is chosen from each tray with equal chance among dice in that tray, what is the probability that the selected values sum to at most 8?
Required annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"5/12"}
```

### task_symbolic__dice__pair_sum_probability / answer_and_annotation / sample 6445890409518238

- `query_id`: `single`
- `instance_seed`: `6445890409518238`
- `word_count`: `113`
- `body_word_count`: `56`

```text
The dice tray diagram shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Treat one die from Tray A and one die from Tray B as independent uniform selections. Select one die uniformly from each tray. What is the probability that the selected values sum to 9?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"1/6"}
```

### task_symbolic__spinner__spinner_pair_event_value / answer_and_annotation / sample 1293263682602839

- `query_id`: `pair_both_target_color_probability`
- `instance_seed`: `1293263682602839`
- `word_count`: `113`
- `body_word_count`: `56`

```text
The spinner diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Answer using one independent spin of each shown spinner. For one spin of Spinner A and one spin of Spinner B, what is the probability that Spinner A lands on blue and Spinner B lands on blue?
Required annotation format: set "annotation" to an object with keys "spinner_a" and "spinner_b", each mapped to that spinner panel bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"spinner_a":[136,102,564,574],"spinner_b":[536,102,964,574]},"answer":"1/12"}
```

### task_symbolic__dice__pair_sum_threshold_probability / answer_and_annotation / sample 1707063197292319

- `query_id`: `pair_sum_at_least_probability`
- `instance_seed`: `1707063197292319`
- `word_count`: `112`
- `body_word_count`: `58`

```text
The visual shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Use Tray A and Tray B as the two independent sources for the probability question. For independent uniform selections from Tray A and Tray B, what is the probability that the selected values sum to at least 7?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"5/12"}
```

### task_symbolic__radial_code_wheel__code_output_label / answer_and_annotation / sample 3633523631165592

- `query_id`: `single`
- `instance_seed`: `3633523631165592`
- `word_count`: `112`
- `body_word_count`: `52`

```text
This radial code wheel shows an exam-scan-style three-ring code wheel, a source code card, and six labeled output options. Read codes from center to edge: first symbol in the inner ring, second in the middle ring, third in the outer ring. Which labeled option matches the output reached by this three-symbol code?
Format for the "annotation" field: set "annotation" to an object with keys "inner_ring_symbol", "middle_ring_symbol", and "outer_ring_symbol", each mapped to the pixel-space center point [x, y] of the matching code symbol on that ring.
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"inner_ring_symbol":[408,327],"middle_ring_symbol":[481,405],"outer_ring_symbol":[568,461]},"answer":"D"}
```

### task_symbolic__dice__pair_difference_probability / answer_and_annotation / sample 4119004237825429

- `query_id`: `single`
- `instance_seed`: `4119004237825429`
- `word_count`: `110`
- `body_word_count`: `53`

```text
The puzzle diagram shows two notebook-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Compute the probability from the visible top faces in both trays. Select one die uniformly from each tray. What is the probability that the absolute difference between the selected values is 1?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"1/4"}
```

### task_symbolic__clock__hand_angle_value / answer_and_annotation / sample 635516394752396

- `query_id`: `single`
- `instance_seed`: `635516394752396`
- `word_count`: `107`
- `body_word_count`: `40`

```text
The visual shows one clean analog clock with hour numerals and two visible hands. Use the hour hand and minute hand shown on the clock. What is the smaller angle in degrees between the hour hand and the minute hand?
Format for the "annotation" field: set "annotation" to an array of two hand segments; each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel-space point from the clock center to a hand tip.
Format for the "answer" field: set "answer" to the smaller angle in degrees as an integer.
Example JSON:
{"annotation":[[[320,320],[430,350]],[[320,320],[484,461]]],"answer":45}
```

### task_symbolic__spinner__spinner_pair_event_value / answer_and_annotation / sample 7795220381451524

- `query_id`: `pair_same_color_probability`
- `instance_seed`: `7795220381451524`
- `word_count`: `106`
- `body_word_count`: `48`

```text
The probability diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Use the product space formed by one equal-likelihood sector from each spinner. If each spinner is spun once, what is the probability that both spinners show the same color?
Annotation format: set "annotation" to an object with keys "spinner_a" and "spinner_b", each mapped to that spinner panel bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"spinner_a":[136,102,564,574],"spinner_b":[536,102,964,574]},"answer":"5/24"}
```

### task_symbolic__radial_code_wheel__output_code_match_label / answer_and_annotation / sample 7889254353767031

- `query_id`: `single`
- `instance_seed`: `7889254353767031`
- `word_count`: `102`
- `body_word_count`: `46`

```text
A synthetic radial lookup wheel presents an exam-scan-style three-ring code wheel, a target output card, and six labeled code options. Each three-symbol code is read center-to-edge through the three rings. Find the shown output label on the wheel. Which option gives the code that reaches it?
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to an object with keys "inner_ring_symbol", "middle_ring_symbol", and "outer_ring_symbol", each mapped to the pixel-space center point [x, y] of the code path that reaches the target output.
Example JSON:
{"annotation":{"inner_ring_symbol":[408,327],"middle_ring_symbol":[481,405],"outer_ring_symbol":[568,461]},"answer":"E"}
```

### task_symbolic__clock__offset_readout / answer_and_annotation / sample 7220985769865365

- `query_id`: `minutes_after`
- `instance_seed`: `7220985769865365`
- `word_count`: `101`
- `body_word_count`: `35`

```text
The clock display shows one clean analog clock with hour numerals and two visible hands. Start from the time shown on the clock. Use a 250-minute offset after the displayed time. What time is it?
Final answer format: set "answer" to the exact time in HH:MM 12-hour format with leading zeros.
Annotation format: set "annotation" to an array of two hand segments; each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel-space point from the clock center to a hand tip.
Example JSON:
{"annotation":[[[320,320],[430,350]],[[320,320],[484,461]]],"answer":"07:35"}
```

### task_symbolic__clock__offset_readout / answer_and_annotation / sample 8342662029204133

- `query_id`: `minutes_before`
- `instance_seed`: `8342662029204133`
- `word_count`: `100`
- `body_word_count`: `35`

```text
This clock display shows one analog clock with all hour numerals, minute ticks, and two visible hands. Base the calculation on the clock face. Starting from the displayed time, what time is 245 minutes earlier?
Annotation format: set "annotation" to an array of two hand segments; each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel-space point from the clock center to a hand tip.
Answer field: set "answer" to the exact time in HH:MM 12-hour format with leading zeros.
Example JSON:
{"annotation":[[[320,320],[430,350]],[[320,320],[484,461]]],"answer":"11:20"}
```

### task_symbolic__dice__dice_conditional_event_value / answer_and_annotation / sample 1997437615682244

- `query_id`: `conditional_color_given_value_property_probability`
- `instance_seed`: `1997437615682244`
- `word_count`: `100`
- `body_word_count`: `58`

```text
The probability panel shows one felt-style tray of colored dice. Each die shows a visible top value. Use only the visible dice matching the given condition as the conditional sample space. Choose one shown die uniformly at random. Conditional on the fact that the selected die shows an odd value, what is the probability that it is blue?
Required annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[145,112,955,650],"answer":"1/4"}
```

### task_symbolic__spinner__spinner_pair_event_value / answer_and_annotation / sample 2787037005924570

- `query_id`: `pair_at_least_one_target_color_probability`
- `instance_seed`: `2787037005924570`
- `word_count`: `99`
- `body_word_count`: `44`

```text
The probability diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Compute the requested probability from the two visible spinners. Find the probability that at least one spinner lands on yellow after spinning both spinners once.
Annotation format: set "annotation" to an object with keys "spinner_a" and "spinner_b", each mapped to that spinner panel bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"spinner_a":[136,102,564,574],"spinner_b":[536,102,964,574]},"answer":"5/12"}
```

### task_symbolic__dice__single_attribute_probability / answer_and_annotation / sample 4072640996020094

- `query_id`: `single_color_or_value_probability`
- `instance_seed`: `4072640996020094`
- `word_count`: `97`
- `body_word_count`: `56`

```text
The puzzle diagram shows one notebook-style tray of colored dice. Each die shows a visible top value. Compute the requested probability from the visible top faces in the dice tray. One die is selected uniformly at random from the shown dice. What is the probability that the selected die is blue or shows an odd value?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":[145,112,955,650],"answer":"7/12"}
```

### task_symbolic__life_automaton__life_future_grid_label / answer_and_annotation / sample 2849119685506143

- `query_id`: `two_step_future_grid`
- `instance_seed`: `2849119685506143`
- `word_count`: `97`
- `body_word_count`: `48`

```text
The figure shows a notebook-style cellular-automaton source grid marked START where dark cells are alive and light cells are empty, with labeled future-grid options below. Apply the same alive-neighbor rule for two updates in sequence. Starting from the grid marked START, after two updates, which option is correct?
Annotation format: set "annotation" to an object/dictionary with keys "source_grid" and "selected_option", each mapped to that pixel bounding box [x0, y0, x1, y1].
Answer field: set "answer" to the single selected option letter.
Example JSON:
{"annotation":{"source_grid":[322,104,718,500],"selected_option":[624,552,774,706]},"answer":"D"}
```

### task_symbolic__dice__single_attribute_probability / answer_and_annotation / sample 2041427766148843

- `query_id`: `single_value_set_probability`
- `instance_seed`: `2041427766148843`
- `word_count`: `95`
- `body_word_count`: `52`

```text
The figure shows one notebook-style tray of colored dice. Each die shows a visible top value. Answer the probability question using only the visible dice in the tray. One die is selected uniformly at random from the shown dice. What is the probability that the selected die shows either 2 or 5?
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[145,112,955,650],"answer":"1/3"}
```

## Repeated Scaffolding Terms

### task_symbolic__dice__dice_conditional_event_value / answer_only / sample 2611783931970638

- `query_id`: `conditional_value_property_given_color_probability`
- `instance_seed`: `2611783931970638`
- `word_count`: `74`
- `body_word_count`: `69`
- `repeated_terms`: `{'answer': 3}`

```text
The visual shows one felt-style tray of colored dice. Each die shows a visible top value. Answer the conditional probability question using the shown dice tray. Choose one shown die uniformly at random. Conditional on the fact that the selected die is green, what is the probability that it shows either 3 or 4?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"2/5"}
```

### task_symbolic__dice__single_attribute_probability / answer_only / sample 2041427766148843

- `query_id`: `single_value_set_probability`
- `instance_seed`: `2041427766148843`
- `word_count`: `72`
- `body_word_count`: `67`
- `repeated_terms`: `{'answer': 3}`

```text
The figure shows one notebook-style tray of colored dice. Each die shows a visible top value. Answer the probability question using only the visible dice in the tray. One die is selected uniformly at random from the shown dice. What is the probability that the selected die shows either 2 or 5?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/3"}
```

### task_symbolic__spinner__single_attribute_probability / answer_only / sample 6410096499497899

- `query_id`: `single_color_probability`
- `instance_seed`: `6410096499497899`
- `word_count`: `60`
- `body_word_count`: `55`
- `repeated_terms`: `{'answer': 3}`

```text
The probability panel shows one notebook-style equal-sector spinner. Each sector has a color and a shape marker. Answer from the visible sector colors and shape markers. For a random spin, what is the probability that the selected sector is yellow?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"2/7"}
```

## All Prompt Samples

### task_symbolic__abacus__displayed_value_readout / single / answer_and_annotation / sample 7712353973239599

- `instance_seed`: `7712353973239599`
- `word_count`: `93`
- `body_word_count`: `23`

```text
The abacus panel shows a wood-framed three-column soroban-style abacus with place-value labels 100, 10, and 1. What number is shown on the abacus?
Annotation format: set "annotation" to an object/dictionary keyed by "hundreds_active_beads", "tens_active_beads", and "ones_active_beads"; each key maps to an array of active bead center points in pixel space [x,y], with an empty array when that column has no active beads.
Answer field: set "answer" to the integer shown by the abacus.
Example JSON:
{"annotation":{"hundreds_active_beads":[[239,292],[239,362]],"tens_active_beads":[],"ones_active_beads":[[739,362],[739,400],[739,438]]},"answer":603}
```

### task_symbolic__abacus__displayed_value_readout / single / answer_only / sample 7712353973239599

- `instance_seed`: `7712353973239599`
- `word_count`: `39`
- `body_word_count`: `23`

```text
The abacus panel shows a wood-framed three-column soroban-style abacus with place-value labels 100, 10, and 1. What number is shown on the abacus?
Final answer format: set "answer" to the integer shown by the abacus.
Example JSON:
{"answer":603}
```

### task_symbolic__abacus__target_value_match_label / single / answer_and_annotation / sample 5393088440609074

- `instance_seed`: `5393088440609074`
- `word_count`: `54`
- `body_word_count`: `15`

```text
The image shows six labeled wood-framed three-column soroban-style abacus option boards. Which option shows 68?
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to the pixel-space bounding box [x0,y0,x1,y1] around the selected abacus option card.
Example JSON:
{"annotation":[430,74,770,354],"answer":"B"}
```

### task_symbolic__abacus__target_value_match_label / single / answer_only / sample 5393088440609074

- `instance_seed`: `5393088440609074`
- `word_count`: `32`
- `body_word_count`: `15`

```text
The image shows six labeled wood-framed three-column soroban-style abacus option boards. Which option shows 68?
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"B"}
```

### task_symbolic__agent_automaton__agent_final_pose_label / single / answer_and_annotation / sample 1847099799238581

- `instance_seed`: `1847099799238581`
- `word_count`: `128`
- `body_word_count`: `76`

```text
The automaton panel shows a notebook-style turning-agent automaton grid with an arrow marker showing the starting cell and direction. Three-state rule: before moving, state 0 turns the agent right and advances to 1; state 1 keeps the direction and advances to 2; state 2 turns the agent left and advances to 0; then the agent moves one cell forward, wrapping around the grid edge. After 4 steps. Which option shows the agent's final cell and direction?
Required annotation format: set "annotation" to an object/dictionary with keys "start_marker" and "selected_option"; each key maps to a pixel bounding box [x0,y0,x1,y1].
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"start_marker":[322,136,376,190],"selected_option":[624,512,774,628]},"answer":"C"}
```

### task_symbolic__agent_automaton__agent_final_pose_label / single / answer_only / sample 1847099799238581

- `instance_seed`: `1847099799238581`
- `word_count`: `90`
- `body_word_count`: `86`

```text
The automaton panel shows a notebook-style turning-agent automaton grid with an arrow marker showing the starting cell and direction. Three-state rule: before moving, state 0 turns the agent right and advances to 1; state 1 keeps the direction and advances to 2; state 2 turns the agent left and advances to 0; then the agent moves one cell forward, wrapping around the grid edge. After 4 steps. Which option shows the agent's final cell and direction?
Answer field: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"C"}
```

### task_symbolic__agent_automaton__future_grid_label / single / answer_and_annotation / sample 1811596061539532

- `instance_seed`: `1811596061539532`
- `word_count`: `119`
- `body_word_count`: `68`

```text
The visual shows a notebook-style turning-agent automaton grid with an arrow marker showing the starting cell and direction. Binary rule: before moving, a light cell turns the agent right and changes to colored; a colored cell turns the agent left and changes to light; then the agent moves one cell forward, wrapping around the grid edge. Simulate 4 steps. Which option shows the full grid after the updates?
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to an object/dictionary with keys "source_grid" and "selected_option"; each key maps to a pixel bounding box [x0,y0,x1,y1].
Example JSON:
{"annotation":{"source_grid":[322,136,490,304],"selected_option":[624,512,794,682]},"answer":"C"}
```

### task_symbolic__agent_automaton__future_grid_label / single / answer_only / sample 1811596061539532

- `instance_seed`: `1811596061539532`
- `word_count`: `83`
- `body_word_count`: `68`

```text
The visual shows a notebook-style turning-agent automaton grid with an arrow marker showing the starting cell and direction. Binary rule: before moving, a light cell turns the agent right and changes to colored; a colored cell turns the agent left and changes to light; then the agent moves one cell forward, wrapping around the grid edge. Simulate 4 steps. Which option shows the full grid after the updates?
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"C"}
```

### task_symbolic__braille_cell__braille_word_read_label / single / answer_and_annotation / sample 2796213836365564

- `instance_seed`: `2796213836365564`
- `word_count`: `73`
- `body_word_count`: `25`

```text
A Braille-cell notation panel shows a clean Braille word plate above four labeled word options. Which labeled word option matches the Braille plate shown above?
Annotation format: set "annotation" to an object with keys "source_plate" and "selected_option", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Answer field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"source_plate":[172,88,808,248],"selected_option":[560,492,820,562]},"answer":"D"}
```

### task_symbolic__braille_cell__braille_word_read_label / single / answer_only / sample 2796213836365564

- `instance_seed`: `2796213836365564`
- `word_count`: `40`
- `body_word_count`: `25`

```text
A Braille-cell notation panel shows a clean Braille word plate above four labeled word options. Which labeled word option matches the Braille plate shown above?
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"D"}
```

### task_symbolic__braille_cell__matching_pattern_label / single / answer_and_annotation / sample 7534397033407124

- `instance_seed`: `7534397033407124`
- `word_count`: `77`
- `body_word_count`: `28`

```text
A Braille-cell notation panel shows a notebook-style Braille reference cell and six labeled Braille option cells. Which option shows the same raised dots as the REF Braille cell?
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to an object with keys "reference_cell" and "selected_option", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":{"reference_cell":[90,248,222,432],"selected_option":[548,110,680,294]},"answer":"C"}
```

### task_symbolic__braille_cell__matching_pattern_label / single / answer_only / sample 7534397033407124

- `instance_seed`: `7534397033407124`
- `word_count`: `42`
- `body_word_count`: `38`

```text
A Braille-cell notation panel shows a notebook-style Braille reference cell and six labeled Braille option cells. Which option shows the same raised dots as the REF Braille cell?
Answer field: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"C"}
```

### task_symbolic__braille_cell__word_braille_match_label / single / answer_and_annotation / sample 2397613005645365

- `instance_seed`: `2397613005645365`
- `word_count`: `74`
- `body_word_count`: `26`

```text
A visual Braille panel presents a notebook-style source word above four labeled Braille word-plate options. Choose the option whose Braille cells spell the word shown above.
Annotation format: set "annotation" to an object with keys "source_word" and "selected_option", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"source_word":[312,56,668,136],"selected_option":[350,422,630,576]},"answer":"D"}
```

### task_symbolic__braille_cell__word_braille_match_label / single / answer_only / sample 2397613005645365

- `instance_seed`: `2397613005645365`
- `word_count`: `41`
- `body_word_count`: `26`

```text
A visual Braille panel presents a notebook-style source word above four labeled Braille word-plate options. Choose the option whose Braille cells spell the word shown above.
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"D"}
```

### task_symbolic__clock__elapsed_time_value / single / answer_and_annotation / sample 8645504145049835

- `instance_seed`: `8645504145049835`
- `word_count`: `90`
- `body_word_count`: `37`

```text
The visual shows two clean labeled analog clocks, A and B, shown side by side with hour numerals and two visible hands. Moving forward around the clock, how many minutes later is clock B than clock A?
Required annotation format: set "annotation" to an object/dictionary with keys "start_clock" and "end_clock", each containing a clock-face bounding box [x0,y0,x1,y1].
Required answer format: set "answer" to the elapsed time in minutes as an integer.
Example JSON:
{"annotation":{"start_clock":[136,186,372,422],"end_clock":[508,186,744,422]},"answer":45}
```

### task_symbolic__clock__elapsed_time_value / single / answer_only / sample 8645504145049835

- `instance_seed`: `8645504145049835`
- `word_count`: `54`
- `body_word_count`: `37`

```text
The visual shows two clean labeled analog clocks, A and B, shown side by side with hour numerals and two visible hands. Moving forward around the clock, how many minutes later is clock B than clock A?
Answer format: set "answer" to the elapsed time in minutes as an integer.
Example JSON:
{"answer":45}
```

### task_symbolic__clock__equivalent_time_label / analog_reference_digital_options / answer_and_annotation / sample 6362550386809564

- `instance_seed`: `6362550386809564`
- `word_count`: `76`
- `body_word_count`: `24`

```text
This clock display shows one analog reference clock above six labeled digital-display options. Which digital option matches the time shown by the reference clock?
Final answer format: set "answer" to the single matching option label as a string.
Annotation format: set "annotation" to an object/dictionary with keys "reference" and "correct_option", each containing a visual bounding box [x0,y0,x1,y1].
Example JSON:
{"annotation":{"reference":[315,74,587,346],"correct_option":[382,442,652,602]},"answer":"B"}
```

### task_symbolic__clock__equivalent_time_label / analog_reference_digital_options / answer_only / sample 6362550386809564

- `instance_seed`: `6362550386809564`
- `word_count`: `44`
- `body_word_count`: `24`

```text
This clock display shows one analog reference clock above six labeled digital-display options. Which digital option matches the time shown by the reference clock?
Format for the "answer" field: set "answer" to the single matching option label as a string.
Example JSON:
{"answer":"B"}
```

### task_symbolic__clock__equivalent_time_label / digital_reference_analog_options / answer_and_annotation / sample 4842126216302487

- `instance_seed`: `4842126216302487`
- `word_count`: `80`
- `body_word_count`: `23`

```text
The image shows one digital reference display above six labeled analog-clock options. Which labeled analog option is equivalent to the reference digital display?
Format for the "annotation" field: set "annotation" to an object/dictionary with keys "reference" and "correct_option", each containing a visual bounding box [x0,y0,x1,y1].
Format for the "answer" field: set "answer" to the single matching option label as a string.
Example JSON:
{"annotation":{"reference":[315,74,587,346],"correct_option":[382,442,652,602]},"answer":"B"}
```

### task_symbolic__clock__equivalent_time_label / digital_reference_analog_options / answer_only / sample 4842126216302487

- `instance_seed`: `4842126216302487`
- `word_count`: `40`
- `body_word_count`: `23`

```text
The image shows one digital reference display above six labeled analog-clock options. Which labeled analog option is equivalent to the reference digital display?
Answer format: set "answer" to the single matching option label as a string.
Example JSON:
{"answer":"B"}
```

### task_symbolic__clock__hand_angle_value / single / answer_and_annotation / sample 635516394752396

- `instance_seed`: `635516394752396`
- `word_count`: `107`
- `body_word_count`: `40`

```text
The visual shows one clean analog clock with hour numerals and two visible hands. Use the hour hand and minute hand shown on the clock. What is the smaller angle in degrees between the hour hand and the minute hand?
Format for the "annotation" field: set "annotation" to an array of two hand segments; each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel-space point from the clock center to a hand tip.
Format for the "answer" field: set "answer" to the smaller angle in degrees as an integer.
Example JSON:
{"annotation":[[[320,320],[430,350]],[[320,320],[484,461]]],"answer":45}
```

### task_symbolic__clock__hand_angle_value / single / answer_only / sample 635516394752396

- `instance_seed`: `635516394752396`
- `word_count`: `60`
- `body_word_count`: `40`

```text
The visual shows one clean analog clock with hour numerals and two visible hands. Use the hour hand and minute hand shown on the clock. What is the smaller angle in degrees between the hour hand and the minute hand?
Format for the "answer" field: set "answer" to the smaller angle in degrees as an integer.
Example JSON:
{"answer":45}
```

### task_symbolic__clock__offset_readout / minutes_after / answer_and_annotation / sample 7220985769865365

- `instance_seed`: `7220985769865365`
- `word_count`: `101`
- `body_word_count`: `35`

```text
The clock display shows one clean analog clock with hour numerals and two visible hands. Start from the time shown on the clock. Use a 250-minute offset after the displayed time. What time is it?
Final answer format: set "answer" to the exact time in HH:MM 12-hour format with leading zeros.
Annotation format: set "annotation" to an array of two hand segments; each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel-space point from the clock center to a hand tip.
Example JSON:
{"annotation":[[[320,320],[430,350]],[[320,320],[484,461]]],"answer":"07:35"}
```

### task_symbolic__clock__offset_readout / minutes_after / answer_only / sample 7220985769865365

- `instance_seed`: `7220985769865365`
- `word_count`: `56`
- `body_word_count`: `51`

```text
The clock display shows one clean analog clock with hour numerals and two visible hands. Start from the time shown on the clock. Use a 250-minute offset after the displayed time. What time is it?
Answer field: set "answer" to the exact time in HH:MM 12-hour format with leading zeros.
Example JSON:
{"answer":"07:35"}
```

### task_symbolic__clock__offset_readout / minutes_before / answer_and_annotation / sample 8342662029204133

- `instance_seed`: `8342662029204133`
- `word_count`: `100`
- `body_word_count`: `35`

```text
This clock display shows one analog clock with all hour numerals, minute ticks, and two visible hands. Base the calculation on the clock face. Starting from the displayed time, what time is 245 minutes earlier?
Annotation format: set "annotation" to an array of two hand segments; each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel-space point from the clock center to a hand tip.
Answer field: set "answer" to the exact time in HH:MM 12-hour format with leading zeros.
Example JSON:
{"annotation":[[[320,320],[430,350]],[[320,320],[484,461]]],"answer":"11:20"}
```

### task_symbolic__clock__offset_readout / minutes_before / answer_only / sample 8342662029204133

- `instance_seed`: `8342662029204133`
- `word_count`: `57`
- `body_word_count`: `35`

```text
This clock display shows one analog clock with all hour numerals, minute ticks, and two visible hands. Base the calculation on the clock face. Starting from the displayed time, what time is 245 minutes earlier?
Required answer format: set "answer" to the exact time in HH:MM 12-hour format with leading zeros.
Example JSON:
{"answer":"11:20"}
```

### task_symbolic__clock__sequence_completion_label / single / answer_and_annotation / sample 6988154751225466

- `instance_seed`: `6988154751225466`
- `word_count`: `86`
- `body_word_count`: `36`

```text
The clock display shows an outline-style top row of four clock boxes with one empty box, and a bottom row of four labeled option clocks. Choose the option clock that belongs in the missing sequence slot.
Annotation format: set "annotation" to an object/dictionary with keys "sequence_panel" and "correct_option", each containing a bounding box [x0,y0,x1,y1].
Answer field: set "answer" to the single selected option label as a string.
Example JSON:
{"annotation":{"sequence_panel":[50,70,930,290],"correct_option":[275,430,480,650]},"answer":"B"}
```

### task_symbolic__clock__sequence_completion_label / single / answer_only / sample 6988154751225466

- `instance_seed`: `6988154751225466`
- `word_count`: `56`
- `body_word_count`: `36`

```text
The clock display shows an outline-style top row of four clock boxes with one empty box, and a bottom row of four labeled option clocks. Choose the option clock that belongs in the missing sequence slot.
Format for the "answer" field: set "answer" to the single selected option label as a string.
Example JSON:
{"answer":"B"}
```

### task_symbolic__clock__time_extremum_label / earliest_time_label / answer_and_annotation / sample 3514303424616976

- `instance_seed`: `3514303424616976`
- `word_count`: `78`
- `body_word_count`: `37`

```text
The figure shows six to twelve labeled outline-style analog clocks arranged in a centered grid with at most four clocks per row, each with hour numerals and two visible hands. Which labeled clock shows the earliest time?
Required annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the selected clock face.
Required answer format: set "answer" to the single selected clock label as a string.
Example JSON:
{"annotation":[368,94,552,278],"answer":"B"}
```

### task_symbolic__clock__time_extremum_label / earliest_time_label / answer_only / sample 3514303424616976

- `instance_seed`: `3514303424616976`
- `word_count`: `54`
- `body_word_count`: `50`

```text
The figure shows six to twelve labeled outline-style analog clocks arranged in a centered grid with at most four clocks per row, each with hour numerals and two visible hands. Which labeled clock shows the earliest time?
Answer field: set "answer" to the single selected clock label as a string.
Example JSON:
{"answer":"B"}
```

### task_symbolic__clock__time_extremum_label / latest_time_label / answer_and_annotation / sample 2087149406837313

- `instance_seed`: `2087149406837313`
- `word_count`: `81`
- `body_word_count`: `41`

```text
The figure shows six to twelve labeled analog clocks arranged in a clean centered grid with at most four clocks per row, each with hour numerals and two visible hands. Which labeled clock shows the latest time among the clocks shown?
Final answer format: set "answer" to the single selected clock label as a string.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] for the selected clock face.
Example JSON:
{"annotation":[368,94,552,278],"answer":"B"}
```

### task_symbolic__clock__time_extremum_label / latest_time_label / answer_only / sample 2087149406837313

- `instance_seed`: `2087149406837313`
- `word_count`: `59`
- `body_word_count`: `41`

```text
The figure shows six to twelve labeled analog clocks arranged in a clean centered grid with at most four clocks per row, each with hour numerals and two visible hands. Which labeled clock shows the latest time among the clocks shown?
Required answer format: set "answer" to the single selected clock label as a string.
Example JSON:
{"answer":"B"}
```

### task_symbolic__dice__dice_conditional_event_value / conditional_color_given_value_property_probability / answer_and_annotation / sample 1997437615682244

- `instance_seed`: `1997437615682244`
- `word_count`: `100`
- `body_word_count`: `58`

```text
The probability panel shows one felt-style tray of colored dice. Each die shows a visible top value. Use only the visible dice matching the given condition as the conditional sample space. Choose one shown die uniformly at random. Conditional on the fact that the selected die shows an odd value, what is the probability that it is blue?
Required annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[145,112,955,650],"answer":"1/4"}
```

### task_symbolic__dice__dice_conditional_event_value / conditional_color_given_value_property_probability / answer_only / sample 1997437615682244

- `instance_seed`: `1997437615682244`
- `word_count`: `78`
- `body_word_count`: `73`

```text
The probability panel shows one felt-style tray of colored dice. Each die shows a visible top value. Use only the visible dice matching the given condition as the conditional sample space. Choose one shown die uniformly at random. Conditional on the fact that the selected die shows an odd value, what is the probability that it is blue?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/4"}
```

### task_symbolic__dice__dice_conditional_event_value / conditional_color_given_value_set_probability / answer_and_annotation / sample 3458053390776292

- `instance_seed`: `3458053390776292`
- `word_count`: `94`
- `body_word_count`: `54`

```text
The visual shows one notebook-style tray of colored dice. Each die shows a visible top value. Use the shown dice tray to compute the requested conditional probability. Choose one shown die uniformly at random. Conditional on the fact that shows one of 1, 5, or 6, what is the probability that it is yellow?
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[145,112,955,650],"answer":"1/3"}
```

### task_symbolic__dice__dice_conditional_event_value / conditional_color_given_value_set_probability / answer_only / sample 3458053390776292

- `instance_seed`: `3458053390776292`
- `word_count`: `74`
- `body_word_count`: `69`

```text
The visual shows one notebook-style tray of colored dice. Each die shows a visible top value. Use the shown dice tray to compute the requested conditional probability. Choose one shown die uniformly at random. Conditional on the fact that shows one of 1, 5, or 6, what is the probability that it is yellow?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/3"}
```

### task_symbolic__dice__dice_conditional_event_value / conditional_value_property_given_color_probability / answer_and_annotation / sample 2611783931970638

- `instance_seed`: `2611783931970638`
- `word_count`: `94`
- `body_word_count`: `54`

```text
The visual shows one felt-style tray of colored dice. Each die shows a visible top value. Answer the conditional probability question using the shown dice tray. Choose one shown die uniformly at random. Conditional on the fact that the selected die is green, what is the probability that it shows either 3 or 4?
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[145,112,955,650],"answer":"2/5"}
```

### task_symbolic__dice__dice_conditional_event_value / conditional_value_property_given_color_probability / answer_only / sample 2611783931970638

- `instance_seed`: `2611783931970638`
- `word_count`: `74`
- `body_word_count`: `69`

```text
The visual shows one felt-style tray of colored dice. Each die shows a visible top value. Answer the conditional probability question using the shown dice tray. Choose one shown die uniformly at random. Conditional on the fact that the selected die is green, what is the probability that it shows either 3 or 4?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"2/5"}
```

### task_symbolic__dice__pair_attribute_combo_probability / pair_color_value_combo_probability / answer_and_annotation / sample 5551575820267229

- `instance_seed`: `5551575820267229`
- `word_count`: `116`
- `body_word_count`: `62`

```text
The dice tray diagram shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Answer using the product space formed by one visible die from each tray. Select one die uniformly from each tray. What is the probability that the Tray A die is purple and the Tray B die shows a prime value?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"1/8"}
```

### task_symbolic__dice__pair_attribute_combo_probability / pair_color_value_combo_probability / answer_only / sample 5551575820267229

- `instance_seed`: `5551575820267229`
- `word_count`: `85`
- `body_word_count`: `62`

```text
The dice tray diagram shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Answer using the product space formed by one visible die from each tray. Select one die uniformly from each tray. What is the probability that the Tray A die is purple and the Tray B die shows a prime value?
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/8"}
```

### task_symbolic__dice__pair_attribute_combo_probability / pair_parity_combo_probability / answer_and_annotation / sample 384962803780726

- `instance_seed`: `384962803780726`
- `word_count`: `123`
- `body_word_count`: `69`

```text
The dice tray diagram shows two dice trays labeled Tray A and Tray B. Each die shows a visible top value. Use the two dice trays to compute the requested probability. If one die is chosen from each tray with equal chance among dice in that tray, what is the probability that the Tray A die shows an even value and the Tray B die shows an odd value?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"1/4"}
```

### task_symbolic__dice__pair_attribute_combo_probability / pair_parity_combo_probability / answer_only / sample 384962803780726

- `instance_seed`: `384962803780726`
- `word_count`: `90`
- `body_word_count`: `69`

```text
The dice tray diagram shows two dice trays labeled Tray A and Tray B. Each die shows a visible top value. Use the two dice trays to compute the requested probability. If one die is chosen from each tray with equal chance among dice in that tray, what is the probability that the Tray A die shows an even value and the Tray B die shows an odd value?
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/4"}
```

### task_symbolic__dice__pair_difference_probability / single / answer_and_annotation / sample 4119004237825429

- `instance_seed`: `4119004237825429`
- `word_count`: `110`
- `body_word_count`: `53`

```text
The puzzle diagram shows two notebook-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Compute the probability from the visible top faces in both trays. Select one die uniformly from each tray. What is the probability that the absolute difference between the selected values is 1?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"1/4"}
```

### task_symbolic__dice__pair_difference_probability / single / answer_only / sample 4119004237825429

- `instance_seed`: `4119004237825429`
- `word_count`: `76`
- `body_word_count`: `53`

```text
The puzzle diagram shows two notebook-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Compute the probability from the visible top faces in both trays. Select one die uniformly from each tray. What is the probability that the absolute difference between the selected values is 1?
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/4"}
```

### task_symbolic__dice__pair_sum_probability / single / answer_and_annotation / sample 6445890409518238

- `instance_seed`: `6445890409518238`
- `word_count`: `113`
- `body_word_count`: `56`

```text
The dice tray diagram shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Treat one die from Tray A and one die from Tray B as independent uniform selections. Select one die uniformly from each tray. What is the probability that the selected values sum to 9?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"1/6"}
```

### task_symbolic__dice__pair_sum_probability / single / answer_only / sample 6445890409518238

- `instance_seed`: `6445890409518238`
- `word_count`: `77`
- `body_word_count`: `56`

```text
The dice tray diagram shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Treat one die from Tray A and one die from Tray B as independent uniform selections. Select one die uniformly from each tray. What is the probability that the selected values sum to 9?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/6"}
```

### task_symbolic__dice__pair_sum_threshold_probability / pair_sum_at_least_probability / answer_and_annotation / sample 1707063197292319

- `instance_seed`: `1707063197292319`
- `word_count`: `112`
- `body_word_count`: `58`

```text
The visual shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Use Tray A and Tray B as the two independent sources for the probability question. For independent uniform selections from Tray A and Tray B, what is the probability that the selected values sum to at least 7?
Annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"5/12"}
```

### task_symbolic__dice__pair_sum_threshold_probability / pair_sum_at_least_probability / answer_only / sample 1707063197292319

- `instance_seed`: `1707063197292319`
- `word_count`: `78`
- `body_word_count`: `73`

```text
The visual shows two felt-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Use Tray A and Tray B as the two independent sources for the probability question. For independent uniform selections from Tray A and Tray B, what is the probability that the selected values sum to at least 7?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"5/12"}
```

### task_symbolic__dice__pair_sum_threshold_probability / pair_sum_at_most_probability / answer_and_annotation / sample 8874693704106542

- `instance_seed`: `8874693704106542`
- `word_count`: `116`
- `body_word_count`: `60`

```text
The figure shows two notebook-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Compute the probability from the visible top faces in both trays. If one die is chosen from each tray with equal chance among dice in that tray, what is the probability that the selected values sum to at most 8?
Required annotation format: set "annotation" to an object with keys "tray_a" and "tray_b", each mapped to that tray bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"tray_a":[68,142,522,628],"tray_b":[578,142,1032,628]},"answer":"5/12"}
```

### task_symbolic__dice__pair_sum_threshold_probability / pair_sum_at_most_probability / answer_only / sample 8874693704106542

- `instance_seed`: `8874693704106542`
- `word_count`: `80`
- `body_word_count`: `75`

```text
The figure shows two notebook-style dice trays labeled Tray A and Tray B. Each die shows a visible top value. Compute the probability from the visible top faces in both trays. If one die is chosen from each tray with equal chance among dice in that tray, what is the probability that the selected values sum to at most 8?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"5/12"}
```

### task_symbolic__dice__single_attribute_probability / single_color_and_value_probability / answer_and_annotation / sample 4266995249650116

- `instance_seed`: `4266995249650116`
- `word_count`: `90`
- `body_word_count`: `49`

```text
The puzzle diagram shows one felt-style tray of colored dice. Each die shows a visible top value. Use the shown dice tray to compute the requested probability. For a uniformly selected die from this tray, what is the probability that the die is red and shows a prime value?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":[145,112,955,650],"answer":"1/6"}
```

### task_symbolic__dice__single_attribute_probability / single_color_and_value_probability / answer_only / sample 4266995249650116

- `instance_seed`: `4266995249650116`
- `word_count`: `70`
- `body_word_count`: `49`

```text
The puzzle diagram shows one felt-style tray of colored dice. Each die shows a visible top value. Use the shown dice tray to compute the requested probability. For a uniformly selected die from this tray, what is the probability that the die is red and shows a prime value?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/6"}
```

### task_symbolic__dice__single_attribute_probability / single_color_or_value_probability / answer_and_annotation / sample 4072640996020094

- `instance_seed`: `4072640996020094`
- `word_count`: `97`
- `body_word_count`: `56`

```text
The puzzle diagram shows one notebook-style tray of colored dice. Each die shows a visible top value. Compute the requested probability from the visible top faces in the dice tray. One die is selected uniformly at random from the shown dice. What is the probability that the selected die is blue or shows an odd value?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":[145,112,955,650],"answer":"7/12"}
```

### task_symbolic__dice__single_attribute_probability / single_color_or_value_probability / answer_only / sample 4072640996020094

- `instance_seed`: `4072640996020094`
- `word_count`: `77`
- `body_word_count`: `56`

```text
The puzzle diagram shows one notebook-style tray of colored dice. Each die shows a visible top value. Compute the requested probability from the visible top faces in the dice tray. One die is selected uniformly at random from the shown dice. What is the probability that the selected die is blue or shows an odd value?
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"7/12"}
```

### task_symbolic__dice__single_attribute_probability / single_parity_probability / answer_and_annotation / sample 4518872152841640

- `instance_seed`: `4518872152841640`
- `word_count`: `87`
- `body_word_count`: `44`

```text
The puzzle diagram shows one tray of colored dice. Each die shows a visible top value. Answer the probability question using only the visible dice in the tray. What probability corresponds to selecting one shown die whose visible top face shows an even value?
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[145,112,955,650],"answer":"3/8"}
```

### task_symbolic__dice__single_attribute_probability / single_parity_probability / answer_only / sample 4518872152841640

- `instance_seed`: `4518872152841640`
- `word_count`: `65`
- `body_word_count`: `44`

```text
The puzzle diagram shows one tray of colored dice. Each die shows a visible top value. Answer the probability question using only the visible dice in the tray. What probability corresponds to selecting one shown die whose visible top face shows an even value?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"3/8"}
```

### task_symbolic__dice__single_attribute_probability / single_value_set_probability / answer_and_annotation / sample 2041427766148843

- `instance_seed`: `2041427766148843`
- `word_count`: `95`
- `body_word_count`: `52`

```text
The figure shows one notebook-style tray of colored dice. Each die shows a visible top value. Answer the probability question using only the visible dice in the tray. One die is selected uniformly at random from the shown dice. What is the probability that the selected die shows either 2 or 5?
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[145,112,955,650],"answer":"1/3"}
```

### task_symbolic__dice__single_attribute_probability / single_value_set_probability / answer_only / sample 2041427766148843

- `instance_seed`: `2041427766148843`
- `word_count`: `72`
- `body_word_count`: `67`

```text
The figure shows one notebook-style tray of colored dice. Each die shows a visible top value. Answer the probability question using only the visible dice in the tray. One die is selected uniformly at random from the shown dice. What is the probability that the selected die shows either 2 or 5?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/3"}
```

### task_symbolic__dice__single_threshold_probability / single_value_at_least_probability / answer_and_annotation / sample 1128119487198585

- `instance_seed`: `1128119487198585`
- `word_count`: `94`
- `body_word_count`: `53`

```text
The probability panel shows one notebook-style tray of colored dice. Each die shows a visible top value. Use the visible dice colors and top values to determine the probability. If one die is chosen uniformly from the dice in the tray, what is the probability that it shows a value at least 4?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":[145,112,955,650],"answer":"5/12"}
```

### task_symbolic__dice__single_threshold_probability / single_value_at_least_probability / answer_only / sample 1128119487198585

- `instance_seed`: `1128119487198585`
- `word_count`: `73`
- `body_word_count`: `53`

```text
The probability panel shows one notebook-style tray of colored dice. Each die shows a visible top value. Use the visible dice colors and top values to determine the probability. If one die is chosen uniformly from the dice in the tray, what is the probability that it shows a value at least 4?
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"5/12"}
```

### task_symbolic__dice__single_threshold_probability / single_value_at_most_probability / answer_and_annotation / sample 5604175876062631

- `instance_seed`: `5604175876062631`
- `word_count`: `89`
- `body_word_count`: `49`

```text
The visual shows one tray of colored dice. Each die shows a visible top value. Use the shown dice tray to compute the requested probability. If one die is chosen uniformly from the dice in the tray, what is the probability that it shows a value at most 2?
Annotation format: set "annotation" to the full dice tray bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[145,112,955,650],"answer":"5/12"}
```

### task_symbolic__dice__single_threshold_probability / single_value_at_most_probability / answer_only / sample 5604175876062631

- `instance_seed`: `5604175876062631`
- `word_count`: `72`
- `body_word_count`: `49`

```text
The visual shows one tray of colored dice. Each die shows a visible top value. Use the shown dice tray to compute the requested probability. If one die is chosen uniformly from the dice in the tray, what is the probability that it shows a value at most 2?
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"5/12"}
```

### task_symbolic__life_automaton__life_future_grid_label / one_step_future_grid / answer_and_annotation / sample 6311297904959301

- `instance_seed`: `6311297904959301`
- `word_count`: `124`
- `body_word_count`: `73`

```text
The visual shows a cellular-automaton source grid marked START where dark cells are alive and light cells are empty, with labeled future-grid options below. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Starting from the grid marked START, choose the option that matches the next grid.
Required annotation format: set "annotation" to an object/dictionary with keys "source_grid" and "selected_option", each mapped to that pixel bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the single selected option letter.
Example JSON:
{"annotation":{"source_grid":[322,104,718,500],"selected_option":[624,552,774,706]},"answer":"D"}
```

### task_symbolic__life_automaton__life_future_grid_label / one_step_future_grid / answer_only / sample 6311297904959301

- `instance_seed`: `6311297904959301`
- `word_count`: `90`
- `body_word_count`: `73`

```text
The visual shows a cellular-automaton source grid marked START where dark cells are alive and light cells are empty, with labeled future-grid options below. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Starting from the grid marked START, choose the option that matches the next grid.
Format for the "answer" field: set "answer" to the single selected option letter.
Example JSON:
{"answer":"D"}
```

### task_symbolic__life_automaton__life_future_grid_label / two_step_future_grid / answer_and_annotation / sample 2849119685506143

- `instance_seed`: `2849119685506143`
- `word_count`: `97`
- `body_word_count`: `48`

```text
The figure shows a notebook-style cellular-automaton source grid marked START where dark cells are alive and light cells are empty, with labeled future-grid options below. Apply the same alive-neighbor rule for two updates in sequence. Starting from the grid marked START, after two updates, which option is correct?
Annotation format: set "annotation" to an object/dictionary with keys "source_grid" and "selected_option", each mapped to that pixel bounding box [x0, y0, x1, y1].
Answer field: set "answer" to the single selected option letter.
Example JSON:
{"annotation":{"source_grid":[322,104,718,500],"selected_option":[624,552,774,706]},"answer":"D"}
```

### task_symbolic__life_automaton__life_future_grid_label / two_step_future_grid / answer_only / sample 2849119685506143

- `instance_seed`: `2849119685506143`
- `word_count`: `62`
- `body_word_count`: `48`

```text
The figure shows a notebook-style cellular-automaton source grid marked START where dark cells are alive and light cells are empty, with labeled future-grid options below. Apply the same alive-neighbor rule for two updates in sequence. Starting from the grid marked START, after two updates, which option is correct?
Answer format: set "answer" to the single selected option letter.
Example JSON:
{"answer":"D"}
```

### task_symbolic__life_automaton__one_step_cell_state_count / one_step_alive_cell_count / answer_and_annotation / sample 5085608709631324

- `instance_seed`: `5085608709631324`
- `word_count`: `137`
- `body_word_count`: `73`

```text
The visual shows a notebook-style cellular-automaton source grid marked START where dark cells are alive and light cells are empty. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Using the grid marked START as the source grid, how many cells are alive in the next grid?
Required annotation format: set "annotation" to an array of pixel-space bounding boxes [x0, y0, x1, y1], one for each visible source-grid cell that has the requested state after one update; use an empty array if there are none.
Required answer format: set "answer" to the integer count.
Example JSON:
{"annotation":[[322,104,376,158],[380,104,434,158],[322,162,376,216]],"answer":3}
```

### task_symbolic__life_automaton__one_step_cell_state_count / one_step_alive_cell_count / answer_only / sample 5085608709631324

- `instance_seed`: `5085608709631324`
- `word_count`: `86`
- `body_word_count`: `73`

```text
The visual shows a notebook-style cellular-automaton source grid marked START where dark cells are alive and light cells are empty. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Using the grid marked START as the source grid, how many cells are alive in the next grid?
Required answer format: set "answer" to the integer count.
Example JSON:
{"answer":3}
```

### task_symbolic__life_automaton__one_step_cell_state_count / one_step_dead_cell_count / answer_and_annotation / sample 8841333106155841

- `instance_seed`: `8841333106155841`
- `word_count`: `135`
- `body_word_count`: `71`

```text
The Life automaton diagram shows a cellular-automaton source grid marked START where dark cells are alive and light cells are empty. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Starting from the grid marked START, after one update, how many cells will be empty?
Required annotation format: set "annotation" to an array of pixel-space bounding boxes [x0, y0, x1, y1], one for each visible source-grid cell that has the requested state after one update; use an empty array if there are none.
Required answer format: set "answer" to the integer count.
Example JSON:
{"annotation":[[322,104,376,158],[380,104,434,158],[322,162,376,216]],"answer":3}
```

### task_symbolic__life_automaton__one_step_cell_state_count / one_step_dead_cell_count / answer_only / sample 8841333106155841

- `instance_seed`: `8841333106155841`
- `word_count`: `83`
- `body_word_count`: `71`

```text
The Life automaton diagram shows a cellular-automaton source grid marked START where dark cells are alive and light cells are empty. Use the rule that an alive cell survives with exactly 2 or 3 alive neighbors, an empty cell becomes alive with exactly 3 alive neighbors, and all other cells are empty in the next grid. Starting from the grid marked START, after one update, how many cells will be empty?
Answer format: set "answer" to the integer count.
Example JSON:
{"answer":3}
```

### task_symbolic__logic_gate_circuit__gate_type_count / single / answer_and_annotation / sample 2527977315694220

- `instance_seed`: `2527977315694220`
- `word_count`: `87`
- `body_word_count`: `30`

```text
The visual panel contains an exam-scan-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. How many NOR gate symbols are in the circuit?
Format for the "annotation" field: set "annotation" to a JSON array of pixel-space gate-symbol bounding boxes [x0, y0, x1, y1], one for each counted gate; use [] if no gate matches.
Format for the "answer" field: set "answer" to the integer number of matching gates.
Example JSON:
{"annotation":[[320,210,392,256],[560,380,632,426]],"answer":2}
```

### task_symbolic__logic_gate_circuit__gate_type_count / single / answer_only / sample 2527977315694220

- `instance_seed`: `2527977315694220`
- `word_count`: `45`
- `body_word_count`: `41`

```text
The visual panel contains an exam-scan-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. How many NOR gate symbols are in the circuit?
Answer field: set "answer" to the integer number of matching gates.
Example JSON:
{"answer":2}
```

### task_symbolic__logic_gate_circuit__internal_output_count / internal_output_one_count / answer_and_annotation / sample 8560699504503482

- `instance_seed`: `8560699504503482`
- `word_count`: `86`
- `body_word_count`: `27`

```text
A circuit worksheet presents an exam-scan-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. How many intermediate gates produce 1?
Annotation format: set "annotation" to a JSON array of pixel-space gate bounding boxes [x0, y0, x1, y1], one for each gate whose computed output is 1; use [] if no gate matches.
Answer field: set "answer" to the integer number of gates whose computed output is 1.
Example JSON:
{"annotation":[[320,210,392,256],[560,380,632,426]],"answer":2}
```

### task_symbolic__logic_gate_circuit__internal_output_count / internal_output_one_count / answer_only / sample 8560699504503482

- `instance_seed`: `8560699504503482`
- `word_count`: `49`
- `body_word_count`: `27`

```text
A circuit worksheet presents an exam-scan-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. How many intermediate gates produce 1?
Format for the "answer" field: set "answer" to the integer number of gates whose computed output is 1.
Example JSON:
{"answer":2}
```

### task_symbolic__logic_gate_circuit__internal_output_count / internal_output_zero_count / answer_and_annotation / sample 4303770276245129

- `instance_seed`: `4303770276245129`
- `word_count`: `84`
- `body_word_count`: `28`

```text
This logic-gate diagram shows an exam-scan-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. How many visible gates evaluate to 0?
Final answer format: set "answer" to the integer number of gates whose computed output is 0.
Annotation format: set "annotation" to a JSON array of pixel-space gate bounding boxes [x0, y0, x1, y1], one for each gate whose computed output is 0; use [] if no gate matches.
Example JSON:
{"annotation":[[410,250,482,296]],"answer":1}
```

### task_symbolic__logic_gate_circuit__internal_output_count / internal_output_zero_count / answer_only / sample 4303770276245129

- `instance_seed`: `4303770276245129`
- `word_count`: `47`
- `body_word_count`: `43`

```text
This logic-gate diagram shows an exam-scan-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. How many visible gates evaluate to 0?
Answer field: set "answer" to the integer number of gates whose computed output is 0.
Example JSON:
{"answer":1}
```

### task_symbolic__logic_gate_circuit__output_value_label / output_one_label / answer_and_annotation / sample 1427417516864550

- `instance_seed`: `1427417516864550`
- `word_count`: `78`
- `body_word_count`: `32`

```text
A circuit worksheet presents a clean worksheet-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. Select the circuit whose final OUT node evaluates to 1.
Required annotation format: set "annotation" to the pixel-space bounding box [x0, y0, x1, y1] of the selected circuit panel whose final OUT value is 1.
Required answer format: set "answer" to the single capital-letter circuit option label.
Example JSON:
{"annotation":[48,50,573,394],"answer":"C"}
```

### task_symbolic__logic_gate_circuit__output_value_label / output_one_label / answer_only / sample 1427417516864550

- `instance_seed`: `1427417516864550`
- `word_count`: `50`
- `body_word_count`: `32`

```text
A circuit worksheet presents a clean worksheet-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. Select the circuit whose final OUT node evaluates to 1.
Format for the "answer" field: set "answer" to the single capital-letter circuit option label.
Example JSON:
{"answer":"C"}
```

### task_symbolic__logic_gate_circuit__output_value_label / output_zero_label / answer_and_annotation / sample 7703892570528682

- `instance_seed`: `7703892570528682`
- `word_count`: `79`
- `body_word_count`: `29`

```text
The circuit-notation panel shows a notebook-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. Which circuit option has final OUT value 0?
Format for the "annotation" field: set "annotation" to the pixel-space bounding box [x0, y0, x1, y1] of the selected circuit panel whose final OUT value is 0.
Format for the "answer" field: set "answer" to the single capital-letter circuit option label.
Example JSON:
{"annotation":[607,426,1132,770],"answer":"D"}
```

### task_symbolic__logic_gate_circuit__output_value_label / output_zero_label / answer_only / sample 7703892570528682

- `instance_seed`: `7703892570528682`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The circuit-notation panel shows a notebook-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. Which circuit option has final OUT value 0?
Answer field: set "answer" to the single capital-letter circuit option label.
Example JSON:
{"answer":"D"}
```

### task_symbolic__logic_gate_circuit__satisfying_assignment_label / assignment_outputs_one_label / answer_and_annotation / sample 8679479721154722

- `instance_seed`: `8679479721154722`
- `word_count`: `81`
- `body_word_count`: `31`

```text
A Boolean logic-gate panel shows an exam-scan-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. Which option assignment makes the source circuit output 1?
Required annotation format: set "annotation" to an object with keys "source_circuit" and "selected_option", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"source_circuit":[48,120,730,690],"selected_option":[793,302,1132,358]},"answer":"D"}
```

### task_symbolic__logic_gate_circuit__satisfying_assignment_label / assignment_outputs_one_label / answer_only / sample 8679479721154722

- `instance_seed`: `8679479721154722`
- `word_count`: `46`
- `body_word_count`: `31`

```text
A Boolean logic-gate panel shows an exam-scan-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. Which option assignment makes the source circuit output 1?
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"D"}
```

### task_symbolic__logic_gate_circuit__satisfying_assignment_label / assignment_outputs_zero_label / answer_and_annotation / sample 2945379813055713

- `instance_seed`: `2945379813055713`
- `word_count`: `83`
- `body_word_count`: `34`

```text
A Boolean logic-gate panel shows a notebook-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. Which labeled assignment sets the source circuit's final OUT value to 0?
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to an object with keys "source_circuit" and "selected_option", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":{"source_circuit":[48,120,730,690],"selected_option":[793,386,1132,470]},"answer":"B"}
```

### task_symbolic__logic_gate_circuit__satisfying_assignment_label / assignment_outputs_zero_label / answer_only / sample 2945379813055713

- `instance_seed`: `2945379813055713`
- `word_count`: `51`
- `body_word_count`: `34`

```text
A Boolean logic-gate panel shows a notebook-style Boolean logic-gate circuit diagram with labeled inputs, standard gate symbols, wires, and final OUT nodes. Which labeled assignment sets the source circuit's final OUT value to 0?
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"B"}
```

### task_symbolic__morse_code__morse_word_read_label / single / answer_and_annotation / sample 7768420476338673

- `instance_seed`: `7768420476338673`
- `word_count`: `79`
- `body_word_count`: `25`

```text
A visual Morse-code panel presents a notebook-style Morse-code word card above four labeled word options. Which option shows the word written by the Morse code?
Format for the "annotation" field: set "annotation" to an object with keys "source_code" and "selected_option", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"source_code":[172,88,808,230],"selected_option":[523,489,763,559]},"answer":"D"}
```

### task_symbolic__morse_code__morse_word_read_label / single / answer_only / sample 7768420476338673

- `instance_seed`: `7768420476338673`
- `word_count`: `39`
- `body_word_count`: `35`

```text
A visual Morse-code panel presents a notebook-style Morse-code word card above four labeled word options. Which option shows the word written by the Morse code?
Answer field: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"D"}
```

### task_symbolic__morse_code__word_morse_match_label / single / answer_and_annotation / sample 5156690499742184

- `instance_seed`: `5156690499742184`
- `word_count`: `75`
- `body_word_count`: `25`

```text
A Morse-code notation panel shows a clean source word above four labeled Morse-code options. Choose the option whose Morse-code symbols spell the word shown above.
Required annotation format: set "annotation" to an object with keys "source_word" and "selected_option", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"source_word":[312,56,668,136],"selected_option":[350,400,630,532]},"answer":"D"}
```

### task_symbolic__morse_code__word_morse_match_label / single / answer_only / sample 5156690499742184

- `instance_seed`: `5156690499742184`
- `word_count`: `39`
- `body_word_count`: `35`

```text
A Morse-code notation panel shows a clean source word above four labeled Morse-code options. Choose the option whose Morse-code symbols spell the word shown above.
Answer field: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"D"}
```

### task_symbolic__music_staff__articulation_symbol_label / single / answer_and_annotation / sample 946346901730870

- `instance_seed`: `946346901730870`
- `word_count`: `56`
- `body_word_count`: `20`

```text
The image shows a clean engraved-style sheet-music staff panel with marked notation items. Read mark 5 and choose its name.
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to the pixel-space point [x, y] at the center of the target articulation symbol.
Example JSON:
{"annotation":[302,149],"answer":"A"}
```

### task_symbolic__music_staff__articulation_symbol_label / single / answer_only / sample 946346901730870

- `instance_seed`: `946346901730870`
- `word_count`: `35`
- `body_word_count`: `20`

```text
The image shows a clean engraved-style sheet-music staff panel with marked notation items. Read mark 5 and choose its name.
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"A"}
```

### task_symbolic__music_staff__chord_inversion_label / single / answer_and_annotation / sample 4757349937076131

- `instance_seed`: `4757349937076131`
- `word_count`: `57`
- `body_word_count`: `20`

```text
The visual shows an exam-scan-style sheet-music staff panel with marked notation items. Which option gives the inversion of chord 4?
Required annotation format: set "annotation" to the target numbered chord pixel-space bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":[300,145,354,248],"answer":"B"}
```

### task_symbolic__music_staff__chord_inversion_label / single / answer_only / sample 4757349937076131

- `instance_seed`: `4757349937076131`
- `word_count`: `34`
- `body_word_count`: `20`

```text
The visual shows an exam-scan-style sheet-music staff panel with marked notation items. Which option gives the inversion of chord 4?
Answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"B"}
```

### task_symbolic__music_staff__chord_quality_label / single / answer_and_annotation / sample 1966872261128852

- `instance_seed`: `1966872261128852`
- `word_count`: `63`
- `body_word_count`: `22`

```text
The image shows a notebook-style sheet-music staff panel with marked notation items. Which visible option gives the chord-quality name for chord 2?
Format for the "annotation" field: set "annotation" to the target numbered chord pixel-space bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":[300,145,354,248],"answer":"A"}
```

### task_symbolic__music_staff__chord_quality_label / single / answer_only / sample 1966872261128852

- `instance_seed`: `1966872261128852`
- `word_count`: `37`
- `body_word_count`: `22`

```text
The image shows a notebook-style sheet-music staff panel with marked notation items. Which visible option gives the chord-quality name for chord 2?
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"A"}
```

### task_symbolic__music_staff__duration_equivalence_label / single / answer_and_annotation / sample 1933762480883165

- `instance_seed`: `1933762480883165`
- `word_count`: `65`
- `body_word_count`: `22`

```text
The sheet-music panel shows a notebook-style sheet-music staff panel with marked notation items. Which option names the duration of numbered note 5?
Format for the "annotation" field: set "annotation" to the pixel-space bounding box [x0, y0, x1, y1] around the target numbered note.
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":[280,188,324,250],"answer":"C"}
```

### task_symbolic__music_staff__duration_equivalence_label / single / answer_only / sample 1933762480883165

- `instance_seed`: `1933762480883165`
- `word_count`: `37`
- `body_word_count`: `22`

```text
The sheet-music panel shows a notebook-style sheet-music staff panel with marked notation items. Which option names the duration of numbered note 5?
Required answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"C"}
```

### task_symbolic__music_staff__interval_name_label / single / answer_and_annotation / sample 4314701971012783

- `instance_seed`: `4314701971012783`
- `word_count`: `69`
- `body_word_count`: `26`

```text
The image shows a clean engraved-style sheet-music staff panel with marked notation items. Which option gives the interval formed by the two notes in range 2?
Format for the "annotation" field: set "annotation" to the pixel-space bounding box [x0, y0, x1, y1] for the marked interval region.
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":[242,154,383,253],"answer":"D"}
```

### task_symbolic__music_staff__interval_name_label / single / answer_only / sample 4314701971012783

- `instance_seed`: `4314701971012783`
- `word_count`: `43`
- `body_word_count`: `26`

```text
The image shows a clean engraved-style sheet-music staff panel with marked notation items. Which option gives the interval formed by the two notes in range 2?
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"D"}
```

### task_symbolic__music_staff__key_signature_label / single / answer_and_annotation / sample 2826891142921793

- `instance_seed`: `2826891142921793`
- `word_count`: `56`
- `body_word_count`: `23`

```text
The image shows an exam-scan-style sheet-music staff panel with marked notation items. Which option gives the key represented by the visible key signature?
Annotation format: set "annotation" to the key-signature pixel-space bounding box [x0, y0, x1, y1].
Answer field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":[190,178,250,222],"answer":"B"}
```

### task_symbolic__music_staff__key_signature_label / single / answer_only / sample 2826891142921793

- `instance_seed`: `2826891142921793`
- `word_count`: `37`
- `body_word_count`: `23`

```text
The image shows an exam-scan-style sheet-music staff panel with marked notation items. Which option gives the key represented by the visible key signature?
Answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"B"}
```

### task_symbolic__music_staff__meter_type_count / single / answer_and_annotation / sample 1317605100986400

- `instance_seed`: `1317605100986400`
- `word_count`: `84`
- `body_word_count`: `24`

```text
This music-notation item shows a notebook-style sheet-music staff panel with marked notation items. How many of the four shown measures are in compound meter?
Final answer format: set "answer" to the integer count of measures with the requested meter type.
Annotation format: set "annotation" to an array containing every counted measure pixel-space bounding box [x0, y0, x1, y1]; use an empty array when no shown measures have the requested meter type.
Example JSON:
{"annotation":[[240,160,330,245],[420,160,510,245]],"answer":2}
```

### task_symbolic__music_staff__meter_type_count / single / answer_only / sample 1317605100986400

- `instance_seed`: `1317605100986400`
- `word_count`: `44`
- `body_word_count`: `24`

```text
This music-notation item shows a notebook-style sheet-music staff panel with marked notation items. How many of the four shown measures are in compound meter?
Final answer format: set "answer" to the integer count of measures with the requested meter type.
Example JSON:
{"answer":2}
```

### task_symbolic__music_staff__note_name_label / single / answer_and_annotation / sample 8197849110983597

- `instance_seed`: `8197849110983597`
- `word_count`: `59`
- `body_word_count`: `22`

```text
This music-notation item shows a notebook-style sheet-music staff panel with marked notation items. Select the option that names the note marked 2.
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to the pixel-space bounding box [x0, y0, x1, y1] for the marked note.
Example JSON:
{"annotation":[270,188,315,252],"answer":"C"}
```

### task_symbolic__music_staff__note_name_label / single / answer_only / sample 8197849110983597

- `instance_seed`: `8197849110983597`
- `word_count`: `37`
- `body_word_count`: `22`

```text
This music-notation item shows a notebook-style sheet-music staff panel with marked notation items. Select the option that names the note marked 2.
Final answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"C"}
```

### task_symbolic__music_staff__roman_numeral_label / single / answer_and_annotation / sample 7425584569773669

- `instance_seed`: `7425584569773669`
- `word_count`: `72`
- `body_word_count`: `24`

```text
The visual shows an exam-scan-style sheet-music staff panel with marked notation items. Read chord 1 relative to G major and choose its roman numeral.
Annotation format: set "annotation" to an object with keys "key_signature" and "target_chord", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Answer field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"key_signature":[190,178,250,222],"target_chord":[300,145,354,248]},"answer":"F"}
```

### task_symbolic__music_staff__roman_numeral_label / single / answer_only / sample 7425584569773669

- `instance_seed`: `7425584569773669`
- `word_count`: `39`
- `body_word_count`: `24`

```text
The visual shows an exam-scan-style sheet-music staff panel with marked notation items. Read chord 1 relative to G major and choose its roman numeral.
Final answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"F"}
```

### task_symbolic__music_staff__scale_degree_function_label / single / answer_and_annotation / sample 592353288016591

- `instance_seed`: `592353288016591`
- `word_count`: `79`
- `body_word_count`: `25`

```text
The figure shows an exam-scan-style sheet-music staff panel with marked notation items. Read note 2 relative to D major. Which option gives its scale-degree function?
Format for the "annotation" field: set "annotation" to an object with keys "key_signature" and "target_note", each mapped to a pixel-space bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"key_signature":[190,178,250,222],"target_note":[330,188,374,250]},"answer":"E"}
```

### task_symbolic__music_staff__scale_degree_function_label / single / answer_only / sample 592353288016591

- `instance_seed`: `592353288016591`
- `word_count`: `42`
- `body_word_count`: `25`

```text
The figure shows an exam-scan-style sheet-music staff panel with marked notation items. Read note 2 relative to D major. Which option gives its scale-degree function?
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"E"}
```

### task_symbolic__music_staff__scale_validation_count / single / answer_and_annotation / sample 326502266525275

- `instance_seed`: `326502266525275`
- `word_count`: `90`
- `body_word_count`: `22`

```text
The visual shows an exam-scan-style sheet-music staff panel with marked notation items. How many shown scale fragments fit the key Bb major?
Format for the "annotation" field: set "annotation" to an array containing every counted scale-fragment range pixel-space bounding box [x0, y0, x1, y1]; use an empty array when no shown fragments correctly fit the requested key.
Format for the "answer" field: set "answer" to the integer count of scale fragments that correctly fit the requested key.
Example JSON:
{"annotation":[[240,160,330,245],[420,160,510,245]],"answer":2}
```

### task_symbolic__music_staff__scale_validation_count / single / answer_only / sample 326502266525275

- `instance_seed`: `326502266525275`
- `word_count`: `43`
- `body_word_count`: `39`

```text
The visual shows an exam-scan-style sheet-music staff panel with marked notation items. How many shown scale fragments fit the key Bb major?
Answer field: set "answer" to the integer count of scale fragments that correctly fit the requested key.
Example JSON:
{"answer":2}
```

### task_symbolic__music_staff__transposed_pitch_pair_count / single / answer_and_annotation / sample 5880458295669042

- `instance_seed`: `5880458295669042`
- `word_count`: `90`
- `body_word_count`: `23`

```text
The visual shows an exam-scan-style sheet-music staff panel with marked notation items. How many marked pairs show the requested upward perfect 5th transposition?
Format for the "annotation" field: set "annotation" to an array containing every counted transposition-pair range pixel-space bounding box [x0, y0, x1, y1]; use an empty array when no shown pairs match the requested transposition.
Format for the "answer" field: set "answer" to the integer count of note pairs that match the requested upward interval.
Example JSON:
{"annotation":[[240,160,330,245],[420,160,510,245]],"answer":2}
```

### task_symbolic__music_staff__transposed_pitch_pair_count / single / answer_only / sample 5880458295669042

- `instance_seed`: `5880458295669042`
- `word_count`: `45`
- `body_word_count`: `23`

```text
The visual shows an exam-scan-style sheet-music staff panel with marked notation items. How many marked pairs show the requested upward perfect 5th transposition?
Final answer format: set "answer" to the integer count of note pairs that match the requested upward interval.
Example JSON:
{"answer":2}
```

### task_symbolic__organic_structure__bond_order_count / single / answer_and_annotation / sample 4877344764467391

- `instance_seed`: `4877344764467391`
- `word_count`: `86`
- `body_word_count`: `25`

```text
The panel contains a clean worksheet-style organic skeletal structure with line-angle bonds, rings, and occasional atom or substituent labels. How many bonds have double-bond notation?
Format for the "annotation" field: set "annotation" to a list of bond segments; each segment is [[x0, y0], [x1, y1]], where each endpoint is an [x, y] pixel-space point at a semantic bond endpoint.
Format for the "answer" field: set "answer" to the integer count of matching bonds.
Example JSON:
{"annotation":[[[420,260],[512,310]],[[610,340],[704,388]]],"answer":2}
```

### task_symbolic__organic_structure__bond_order_count / single / answer_only / sample 4877344764467391

- `instance_seed`: `4877344764467391`
- `word_count`: `41`
- `body_word_count`: `25`

```text
The panel contains a clean worksheet-style organic skeletal structure with line-angle bonds, rings, and occasional atom or substituent labels. How many bonds have double-bond notation?
Final answer format: set "answer" to the integer count of matching bonds.
Example JSON:
{"answer":2}
```

### task_symbolic__organic_structure__ring_size_count / single / answer_and_annotation / sample 2402383998819320

- `instance_seed`: `2402383998819320`
- `word_count`: `69`
- `body_word_count`: `25`

```text
The panel contains a clean worksheet-style organic skeletal structure with line-angle bonds, rings, and occasional atom or substituent labels. How many hexagonal rings are shown?
Annotation format: set "annotation" to an array containing the pixel-space bounding box [x0, y0, x1, y1] around every matching ring.
Answer format: set "answer" to the integer count of matching rings.
Example JSON:
{"annotation":[[220,250,340,370],[520,250,640,370]],"answer":2}
```

### task_symbolic__organic_structure__ring_size_count / single / answer_only / sample 2402383998819320

- `instance_seed`: `2402383998819320`
- `word_count`: `40`
- `body_word_count`: `36`

```text
The panel contains a clean worksheet-style organic skeletal structure with line-angle bonds, rings, and occasional atom or substituent labels. How many hexagonal rings are shown?
Answer field: set "answer" to the integer count of matching rings.
Example JSON:
{"answer":2}
```

### task_symbolic__radial_code_wheel__code_output_label / single / answer_and_annotation / sample 3633523631165592

- `instance_seed`: `3633523631165592`
- `word_count`: `112`
- `body_word_count`: `52`

```text
This radial code wheel shows an exam-scan-style three-ring code wheel, a source code card, and six labeled output options. Read codes from center to edge: first symbol in the inner ring, second in the middle ring, third in the outer ring. Which labeled option matches the output reached by this three-symbol code?
Format for the "annotation" field: set "annotation" to an object with keys "inner_ring_symbol", "middle_ring_symbol", and "outer_ring_symbol", each mapped to the pixel-space center point [x, y] of the matching code symbol on that ring.
Format for the "answer" field: set "answer" to the single capital-letter option label.
Example JSON:
{"annotation":{"inner_ring_symbol":[408,327],"middle_ring_symbol":[481,405],"outer_ring_symbol":[568,461]},"answer":"D"}
```

### task_symbolic__radial_code_wheel__code_output_label / single / answer_only / sample 3633523631165592

- `instance_seed`: `3633523631165592`
- `word_count`: `66`
- `body_word_count`: `52`

```text
This radial code wheel shows an exam-scan-style three-ring code wheel, a source code card, and six labeled output options. Read codes from center to edge: first symbol in the inner ring, second in the middle ring, third in the outer ring. Which labeled option matches the output reached by this three-symbol code?
Answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"D"}
```

### task_symbolic__radial_code_wheel__output_code_match_label / single / answer_and_annotation / sample 7889254353767031

- `instance_seed`: `7889254353767031`
- `word_count`: `102`
- `body_word_count`: `46`

```text
A synthetic radial lookup wheel presents an exam-scan-style three-ring code wheel, a target output card, and six labeled code options. Each three-symbol code is read center-to-edge through the three rings. Find the shown output label on the wheel. Which option gives the code that reaches it?
Final answer format: set "answer" to the single capital-letter option label.
Annotation format: set "annotation" to an object with keys "inner_ring_symbol", "middle_ring_symbol", and "outer_ring_symbol", each mapped to the pixel-space center point [x, y] of the code path that reaches the target output.
Example JSON:
{"annotation":{"inner_ring_symbol":[408,327],"middle_ring_symbol":[481,405],"outer_ring_symbol":[568,461]},"answer":"E"}
```

### task_symbolic__radial_code_wheel__output_code_match_label / single / answer_only / sample 7889254353767031

- `instance_seed`: `7889254353767031`
- `word_count`: `60`
- `body_word_count`: `46`

```text
A synthetic radial lookup wheel presents an exam-scan-style three-ring code wheel, a target output card, and six labeled code options. Each three-symbol code is read center-to-edge through the three rings. Find the shown output label on the wheel. Which option gives the code that reaches it?
Answer format: set "answer" to the single capital-letter option label.
Example JSON:
{"answer":"E"}
```

### task_symbolic__spinner__multi_attribute_and_probability / single / answer_and_annotation / sample 7924856202488524

- `instance_seed`: `7924856202488524`
- `word_count`: `85`
- `body_word_count`: `45`

```text
The probability diagram shows one notebook-style equal-sector spinner. Each sector has a color and a shape marker. Answer from the visible sector colors and shape markers. For a random spin, what is the probability that the selected sector is purple and marked with a diamond?
Annotation format: set "annotation" to the full spinner panel bounding box [x0, y0, x1, y1].
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[281,47,819,629],"answer":"1/8"}
```

### task_symbolic__spinner__multi_attribute_and_probability / single / answer_only / sample 7924856202488524

- `instance_seed`: `7924856202488524`
- `word_count`: `68`
- `body_word_count`: `45`

```text
The probability diagram shows one notebook-style equal-sector spinner. Each sector has a color and a shape marker. Answer from the visible sector colors and shape markers. For a random spin, what is the probability that the selected sector is purple and marked with a diamond?
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/8"}
```

### task_symbolic__spinner__multi_attribute_or_probability / single / answer_and_annotation / sample 1731064506771686

- `instance_seed`: `1731064506771686`
- `word_count`: `87`
- `body_word_count`: `44`

```text
The probability diagram shows one equal-sector spinner. Each sector has a color and a shape marker. Answer from the visible sector colors and shape markers. For a random spin, what is the probability that the selected sector is purple or marked with a triangle?
Annotation format: set "annotation" to the full spinner panel bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[281,47,819,629],"answer":"1/3"}
```

### task_symbolic__spinner__multi_attribute_or_probability / single / answer_only / sample 1731064506771686

- `instance_seed`: `1731064506771686`
- `word_count`: `65`
- `body_word_count`: `44`

```text
The probability diagram shows one equal-sector spinner. Each sector has a color and a shape marker. Answer from the visible sector colors and shape markers. For a random spin, what is the probability that the selected sector is purple or marked with a triangle?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/3"}
```

### task_symbolic__spinner__single_attribute_probability / single_color_probability / answer_and_annotation / sample 6410096499497899

- `instance_seed`: `6410096499497899`
- `word_count`: `80`
- `body_word_count`: `40`

```text
The probability panel shows one notebook-style equal-sector spinner. Each sector has a color and a shape marker. Answer from the visible sector colors and shape markers. For a random spin, what is the probability that the selected sector is yellow?
Annotation format: set "annotation" to the full spinner panel bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[281,47,819,629],"answer":"2/7"}
```

### task_symbolic__spinner__single_attribute_probability / single_color_probability / answer_only / sample 6410096499497899

- `instance_seed`: `6410096499497899`
- `word_count`: `60`
- `body_word_count`: `55`

```text
The probability panel shows one notebook-style equal-sector spinner. Each sector has a color and a shape marker. Answer from the visible sector colors and shape markers. For a random spin, what is the probability that the selected sector is yellow?
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"2/7"}
```

### task_symbolic__spinner__single_attribute_probability / single_shape_probability / answer_and_annotation / sample 4433888036705808

- `instance_seed`: `4433888036705808`
- `word_count`: `82`
- `body_word_count`: `42`

```text
The probability panel shows one notebook-style equal-sector spinner. Each sector has a color and a shape marker. Treat each sector as equally likely for one spin. Find the probability that the pointer lands on a sector that is marked with a square.
Annotation format: set "annotation" to the full spinner panel bounding box [x0, y0, x1, y1].
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":[281,47,819,629],"answer":"3/8"}
```

### task_symbolic__spinner__single_attribute_probability / single_shape_probability / answer_only / sample 4433888036705808

- `instance_seed`: `4433888036705808`
- `word_count`: `63`
- `body_word_count`: `42`

```text
The probability panel shows one notebook-style equal-sector spinner. Each sector has a color and a shape marker. Treat each sector as equally likely for one spin. Find the probability that the pointer lands on a sector that is marked with a square.
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"3/8"}
```

### task_symbolic__spinner__spinner_pair_event_value / pair_at_least_one_target_color_probability / answer_and_annotation / sample 2787037005924570

- `instance_seed`: `2787037005924570`
- `word_count`: `99`
- `body_word_count`: `44`

```text
The probability diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Compute the requested probability from the two visible spinners. Find the probability that at least one spinner lands on yellow after spinning both spinners once.
Annotation format: set "annotation" to an object with keys "spinner_a" and "spinner_b", each mapped to that spinner panel bounding box [x0, y0, x1, y1].
Answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"spinner_a":[136,102,564,574],"spinner_b":[536,102,964,574]},"answer":"5/12"}
```

### task_symbolic__spinner__spinner_pair_event_value / pair_at_least_one_target_color_probability / answer_only / sample 2787037005924570

- `instance_seed`: `2787037005924570`
- `word_count`: `64`
- `body_word_count`: `59`

```text
The probability diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Compute the requested probability from the two visible spinners. Find the probability that at least one spinner lands on yellow after spinning both spinners once.
Answer field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"5/12"}
```

### task_symbolic__spinner__spinner_pair_event_value / pair_both_target_color_probability / answer_and_annotation / sample 1293263682602839

- `instance_seed`: `1293263682602839`
- `word_count`: `113`
- `body_word_count`: `56`

```text
The spinner diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Answer using one independent spin of each shown spinner. For one spin of Spinner A and one spin of Spinner B, what is the probability that Spinner A lands on blue and Spinner B lands on blue?
Required annotation format: set "annotation" to an object with keys "spinner_a" and "spinner_b", each mapped to that spinner panel bounding box [x0, y0, x1, y1].
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"spinner_a":[136,102,564,574],"spinner_b":[536,102,964,574]},"answer":"1/12"}
```

### task_symbolic__spinner__spinner_pair_event_value / pair_both_target_color_probability / answer_only / sample 1293263682602839

- `instance_seed`: `1293263682602839`
- `word_count`: `77`
- `body_word_count`: `56`

```text
The spinner diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Answer using one independent spin of each shown spinner. For one spin of Spinner A and one spin of Spinner B, what is the probability that Spinner A lands on blue and Spinner B lands on blue?
Required answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"1/12"}
```

### task_symbolic__spinner__spinner_pair_event_value / pair_same_color_probability / answer_and_annotation / sample 7795220381451524

- `instance_seed`: `7795220381451524`
- `word_count`: `106`
- `body_word_count`: `48`

```text
The probability diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Use the product space formed by one equal-likelihood sector from each spinner. If each spinner is spun once, what is the probability that both spinners show the same color?
Annotation format: set "annotation" to an object with keys "spinner_a" and "spinner_b", each mapped to that spinner panel bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"annotation":{"spinner_a":[136,102,564,574],"spinner_b":[536,102,964,574]},"answer":"5/24"}
```

### task_symbolic__spinner__spinner_pair_event_value / pair_same_color_probability / answer_only / sample 7795220381451524

- `instance_seed`: `7795220381451524`
- `word_count`: `69`
- `body_word_count`: `48`

```text
The probability diagram shows two independent equal-sector spinners labeled Spinner A and Spinner B. Each sector has a color. Use the product space formed by one equal-likelihood sector from each spinner. If each spinner is spun once, what is the probability that both spinners show the same color?
Final answer format: set "answer" to the probability as a reduced fraction string like "3/8".
Example JSON:
{"answer":"5/24"}
```

### task_symbolic__turing_tape__final_head_position_value / single / answer_and_annotation / sample 7704511493626341

- `instance_seed`: `7704511493626341`
- `word_count`: `128`
- `body_word_count`: `79`

```text
The symbolic machine panel shows a tape-machine automaton with a starting tape, head marker, state label, step count, symbol alphabet, and transition table. Use the diagrammed tape machine and transition table to answer. At each step, find the row with the current state and the symbol under the head, write the new symbol, move the head L or R, and switch to the next state. Follow the tape machine for 5 steps and report the final head cell number.
Final answer format: set "answer" to the 1-based integer tape cell number.
Annotation format: set "annotation" to an object with keys "machine_panel" and "transition_table", each mapped to a bounding box [x0, y0, x1, y1].
Example JSON:
{"annotation":{"machine_panel":[248,96,792,238],"transition_table":[316,282,724,536]},"answer":5}
```

### task_symbolic__turing_tape__final_head_position_value / single / answer_only / sample 7704511493626341

- `instance_seed`: `7704511493626341`
- `word_count`: `95`
- `body_word_count`: `79`

```text
The symbolic machine panel shows a tape-machine automaton with a starting tape, head marker, state label, step count, symbol alphabet, and transition table. Use the diagrammed tape machine and transition table to answer. At each step, find the row with the current state and the symbol under the head, write the new symbol, move the head L or R, and switch to the next state. Follow the tape machine for 5 steps and report the final head cell number.
Final answer format: set "answer" to the 1-based integer tape cell number.
Example JSON:
{"answer":5}
```

### task_symbolic__turing_tape__turing_written_symbol_count / single / answer_and_annotation / sample 4473877317529143

- `instance_seed`: `4473877317529143`
- `word_count`: `124`
- `body_word_count`: `73`

```text
The visual shows a tape-machine automaton with a starting tape, head marker, state label, step count, symbol alphabet, and transition table. Follow the displayed machine rules exactly. At each step, find the row with the current state and the symbol under the head, write the new symbol, move the head L or R, and switch to the next state. Simulate exactly 6 steps. What is the count of tape cells showing 0 afterward?
Format for the "annotation" field: set "annotation" to an object with keys "machine_panel" and "transition_table", each mapped to a bounding box [x0, y0, x1, y1].
Format for the "answer" field: set "answer" to the integer count.
Example JSON:
{"annotation":{"machine_panel":[248,96,792,238],"transition_table":[316,282,724,536]},"answer":4}
```

### task_symbolic__turing_tape__turing_written_symbol_count / single / answer_only / sample 4473877317529143

- `instance_seed`: `4473877317529143`
- `word_count`: `86`
- `body_word_count`: `73`

```text
The visual shows a tape-machine automaton with a starting tape, head marker, state label, step count, symbol alphabet, and transition table. Follow the displayed machine rules exactly. At each step, find the row with the current state and the symbol under the head, write the new symbol, move the head L or R, and switch to the next state. Simulate exactly 6 steps. What is the count of tape cells showing 0 afterward?
Required answer format: set "answer" to the integer count.
Example JSON:
{"answer":4}
```

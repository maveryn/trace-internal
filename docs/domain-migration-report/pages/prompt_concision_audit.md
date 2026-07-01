# Prompt Concision Audit

- rendered prompts: `214`
- tasks covered: `80`
- observed query ids covered: `107`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_pages__calendar__date_range_day_class_count | `weekday_range_count, weekend_range_count` | `{'weekday_range_count': 1, 'weekend_range_count': 1}` | 2 | `` |
| task_pages__calendar__date_weekday_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar__marked_day_class_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar__weekday_occurrence_date | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar__workday_offset_date | `workday_after_offset_date, workday_before_offset_date` | `{'workday_after_offset_date': 1, 'workday_before_offset_date': 1}` | 2 | `` |
| task_pages__calendar_event_grid__category_slot_day_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar_event_grid__date_filled_slot_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar_event_grid__date_for_category_slot_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__calendar_event_grid__date_slot_category_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__category_grid__category_item_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__category_grid__category_slot_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__concept_map__branch_child_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__concept_map__marked_child_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__concept_map__ordered_child_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__control_board__control_state_condition_count | `disabled_controls_in_group_count, selected_enabled_controls_in_group_count` | `{'disabled_controls_in_group_count': 1, 'selected_enabled_controls_in_group_count': 1}` | 2 | `` |
| task_pages__cycle__offset_stage_label | `after_stage_offset_label, before_stage_offset_label` | `{'after_stage_offset_label': 1, 'before_stage_offset_label': 1}` | 2 | `` |
| task_pages__form_section__sum_minus_amount_in_section_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__form_section__two_amount_arithmetic_value | `difference_two_amounts_in_section_value, sum_two_amounts_in_section_value` | `{'difference_two_amounts_in_section_value': 1, 'sum_two_amounts_in_section_value': 1}` | 2 | `` |
| task_pages__hero_callout_infographic__callout_condition_count | `field_value_above_threshold_count, field_value_below_threshold_count` | `{'field_value_above_threshold_count': 1, 'field_value_below_threshold_count': 1}` | 2 | `` |
| task_pages__hero_callout_infographic__callout_field_value_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__hero_callout_infographic__callout_metric_extremum_label | `highest_field_value_callout_label, lowest_field_value_callout_label` | `{'highest_field_value_callout_label': 1, 'lowest_field_value_callout_label': 1}` | 2 | `` |
| task_pages__hierarchy__manager_most_direct_reports_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__hierarchy__manager_most_total_reports_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__hierarchy__subtree_descendant_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__global_metric_ranked_item_label | `nth_highest_metric_label, nth_lowest_metric_label` | `{'nth_highest_metric_label': 1, 'nth_lowest_metric_label': 1}` | 2 | `` |
| task_pages__infographic__metric_card_field_lookup | `detail_for_named_item, item_for_named_value, value_for_named_item` | `{'detail_for_named_item': 1, 'item_for_named_value': 1, 'value_for_named_item': 1}` | 3 | `` |
| task_pages__infographic__section_extrema_arithmetic_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_icon_extremum_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_icon_total_difference_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_icon_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_metric_ranked_item_label | `nth_highest_metric_in_section_label, nth_lowest_metric_in_section_label` | `{'nth_highest_metric_in_section_label': 1, 'nth_lowest_metric_in_section_label': 1}` | 2 | `` |
| task_pages__infographic__section_ranked_total_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_total_except_named_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__section_total_extrema_difference_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__infographic__sum_named_metrics_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__instruction_panel__shared_control_for_step_set_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__instruction_panel__step_for_control_pair_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__map__destination_after_directions_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__map__landmark_after_route_step_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_condition_item_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_field_ranked_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_field_total_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_field_value_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__module_two_field_condition_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__page_field_extremum_module_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__navigation_flow__navigation_path_target_label | `menu_path_target_label, ribbon_group_command_label, sidebar_tree_target_label` | `{'menu_path_target_label': 1, 'ribbon_group_command_label': 1, 'sidebar_tree_target_label': 1}` | 3 | `` |
| task_pages__navigation_flow__same_group_target_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__paired_forms__shortfall_minus_overage_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__paired_forms__sum_absolute_quantity_differences_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__paired_forms__total_amount_delta_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__process_flow__condition_path_endpoint_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__process_flow__filtered_node_count | `role_node_count, shape_node_count, status_node_count` | `{'role_node_count': 1, 'shape_node_count': 1, 'status_node_count': 1}` | 3 | `` |
| task_pages__process_flow__lane_filtered_handoff_count | `lane_involved_handoff_count, lane_outgoing_handoff_count` | `{'lane_involved_handoff_count': 1, 'lane_outgoing_handoff_count': 1}` | 2 | `` |
| task_pages__profile_card_grid__field_ranked_profile_label | `highest_field_profile_label, lowest_field_profile_label, nth_highest_field_profile_label, nth_lowest_field_profile_label` | `{'highest_field_profile_label': 1, 'lowest_field_profile_label': 1, 'nth_highest_field_profile_label': 1, 'nth_lowest_field_profile_label': 1}` | 4 | `` |
| task_pages__profile_card_grid__profile_for_field_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__profile_card_grid__value_for_named_profile_field | `single` | `{'single': 1}` | 2 | `` |
| task_pages__record_table__enabled_action_for_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__record_table__selected_rows_with_status_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__record_table__value_threshold_in_group_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schedule__longer_than_reference_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schedule__maximum_non_overlapping_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schedule__overlap_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schema__field_role_count | `all_field_count, attribute_field_count` | `{'all_field_count': 1, 'attribute_field_count': 1}` | 2 | `` |
| task_pages__schema__join_path_length_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schema__relationship_cardinality_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schema__relationship_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__schema__relationship_endpoint_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__sectioned_infographic__section_filtered_item_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__sectioned_infographic__section_item_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__step_list__nth_step_field_label | `nth_step_detail, nth_step_title` | `{'nth_step_detail': 1, 'nth_step_title': 1}` | 2 | `` |
| task_pages__step_list__step_after_named_step_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__step_list__step_for_detail_label | `step_number_for_detail, step_title_for_detail` | `{'step_number_for_detail': 1, 'step_title_for_detail': 1}` | 2 | `` |
| task_pages__timeline__event_date_gap_value | `single` | `{'single': 1}` | 2 | `` |
| task_pages__timeline__interval_membership_count | `between_reference_events_count, outside_reference_interval_count` | `{'between_reference_events_count': 1, 'outside_reference_interval_count': 1}` | 2 | `` |
| task_pages__web_action__action_target_label | `click_target_label, select_option_label, type_field_label` | `{'click_target_label': 1, 'select_option_label': 1, 'type_field_label': 1}` | 3 | `` |
| task_pages__web_action__guide_code_target_count | `click_guide_code_target_count, select_option_guide_code_target_count, type_field_guide_code_target_count` | `{'click_guide_code_target_count': 1, 'select_option_guide_code_target_count': 1, 'type_field_guide_code_target_count': 1}` | 3 | `` |
| task_pages__workspace__context_control_count | `single` | `{'single': 1}` | 2 | `` |
| task_pages__workspace__control_label | `single` | `{'single': 1}` | 2 | `` |
| task_pages__workspace__dual_guide_control_label | `single` | `{'single': 1}` | 2 | `` |

## Longest Prompts

### task_pages__process_flow__condition_path_endpoint_label / answer_and_annotation / sample 2040856734394341

- `query_id`: `single`
- `instance_seed`: `2040856734394341`
- `word_count`: `123`
- `body_word_count`: `51`

```text
The figure shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Begin at "Verify". Follow the decision labels "approve" then "pass"; use unlabeled arrows only to move between decisions. What step label do you land on?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "start_step", "first_decision_label", "second_decision_label", and "endpoint_step", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the exact visible destination step label as a string.
Example JSON:
{"annotation":{"start_step":[126,208,260,270],"first_decision_label":[286,254,340,278],"second_decision_label":[512,412,570,436],"endpoint_step":[630,458,764,520]},"answer":"Publish"}
```

### task_pages__form_section__sum_minus_amount_in_section_value / answer_and_annotation / sample 4106865584098799

- `query_id`: `single`
- `instance_seed`: `4106865584098799`
- `word_count`: `117`
- `body_word_count`: `47`

```text
This page shows a structured document with visible section headers and labeled currency fields. In the "Fees" section, what is "Facility Fee" plus "Service Fee" minus "Registration Fee"? Use currency notation with exactly two digits after the decimal point.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an object mapping "first_operand", "second_operand", and "third_operand" to the referenced operand field boxes [x0, y0, x1, y1], including each field label and value.
Answer format: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Example JSON:
{"annotation":{"first_operand":[120,248,420,306],"second_operand":[120,308,420,366],"third_operand":[120,368,420,426]},"answer":"$133.30"}
```

### task_pages__web_action__action_target_label / answer_and_annotation / sample 5385102067759693

- `query_id`: `click_target_label`
- `instance_seed`: `5385102067759693`
- `word_count`: `109`
- `body_word_count`: `59`

```text
The figure shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Instruction: For the item with category "Creative" and status "Reserved", use guide code "X6" from the Action Guide. Which labeled web control matches the guide code and page context?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to one [x0, y0, x1, y1] pixel box around the target button and its candidate label marker.
Format for the "answer" field: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"annotation":[410,378,584,442],"answer":"G"}
```

### task_pages__form_section__two_amount_arithmetic_value / answer_and_annotation / sample 610633119778029

- `query_id`: `sum_two_amounts_in_section_value`
- `instance_seed`: `610633119778029`
- `word_count`: `105`
- `body_word_count`: `35`

```text
The image shows a structured document with visible section headers and labeled currency fields. Using only the "Totals" section, add "Rounding" and "Bag Fee". What amount results?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object mapping "first_operand" and "second_operand" to the referenced operand field boxes [x0, y0, x1, y1], including each field label and value.
Format for the "answer" field: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Example JSON:
{"annotation":{"first_operand":[120,248,420,306],"second_operand":[120,308,420,366]},"answer":"$146.80"}
```

### task_pages__calendar__date_weekday_label / answer_and_annotation / sample 7090564677460468

- `query_id`: `single`
- `instance_seed`: `7090564677460468`
- `word_count`: `104`
- `body_word_count`: `48`

```text
The picture shows one month-view calendar with weekday headers and date cells. Which weekday header is above date 21? Answer with the exact short header label shown in the calendar, such as Mon, Tue, Wed, Thu, Fri, Sat, or Sun.
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible three-letter weekday header label above the queried date, one of Mon, Tue, Wed, Thu, Fri, Sat, or Sun.
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the queried date cell.
Example JSON:
{"annotation":[354,256,456,352],"answer":"Wed"}
```

### task_pages__map__destination_after_directions_label / answer_and_annotation / sample 1707024503580881

- `query_id`: `single`
- `instance_seed`: `1707024503580881`
- `word_count`: `104`
- `body_word_count`: `49`

```text
The figure shows a printed campus layout with labeled landmarks, named zones, visible walking paths, and a compass. Begin at "Auditorium" and follow these directions one step at a time: north, then west, then north, then west. Which landmark is reached?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible destination landmark label.
Annotation format: set "annotation" to an ordered array of [x0, y0, x1, y1] pixel bounding boxes around the route landmarks from the start through the destination.
Example JSON:
{"annotation":[[188,310,314,368],[426,310,552,368],[426,478,552,536]],"answer":"Clinic"}
```

### task_pages__map__landmark_after_route_step_label / answer_and_annotation / sample 741138217825354

- `query_id`: `single`
- `instance_seed`: `741138217825354`
- `word_count`: `103`
- `body_word_count`: `43`

```text
The figure shows a printed campus layout with labeled landmarks, named zones, visible walking paths, and a highlighted orange route. Using only the orange route, count landmarks after "Depot". What is the 3rd reached landmark?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible landmark label at the requested route step.
Annotation format: set "annotation" to an ordered array of [x0, y0, x1, y1] pixel bounding boxes around the highlighted-route landmarks from the start through the requested landmark.
Example JSON:
{"annotation":[[214,388,340,446],[452,388,578,446],[690,388,816,446]],"answer":"Gallery"}
```

### task_pages__paired_forms__sum_absolute_quantity_differences_value / answer_and_annotation / sample 7787010893722139

- `query_id`: `single`
- `instance_seed`: `7787010893722139`
- `word_count`: `103`
- `body_word_count`: `45`

```text
The page shows two side-by-side business forms, a purchase order and a receiving slip, with matching item codes and visible quantities. Compare ordered and received quantities row by row, take absolute differences for mismatches, and add them.
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the computed integer sum of absolute quantity differences.
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for the full receiving-slip rows whose received quantity differs from the matching purchase-order quantity.
Example JSON:
{"annotation":[[850,340,1268,378],[850,388,1268,426],[850,436,1268,474]],"answer":42}
```

### task_pages__calendar_event_grid__date_filled_slot_count / answer_and_annotation / sample 2207101115369380

- `query_id`: `single`
- `instance_seed`: `2207101115369380`
- `word_count`: `101`
- `body_word_count`: `40`

```text
This page shows one month calendar where date cells contain short category chips in Top, Mid, and End event slots. Find date 20. How many event chips are shown in its slots?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the event chips on the requested date, or [] if no slots are filled.
Answer format: set "answer" to the integer number of filled event slots on the requested date.
Example JSON:
{"annotation":[[268,286,376,304],[268,310,376,328]],"answer":2}
```

### task_pages__hierarchy__subtree_descendant_count / answer_and_annotation / sample 7237503248477476

- `query_id`: `single`
- `instance_seed`: `7237503248477476`
- `word_count`: `101`
- `body_word_count`: `38`

```text
The figure shows an organization chart with the CEO at the top, labeled employees, and visible reporting lines. What is the total number of people under "Moon" in the chart?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around every counted person.
Format for the "answer" field: set "answer" to the integer count of people under the requested manager.
Example JSON:
{"annotation":[[256,316,368,374],[196,462,308,520],[374,462,486,520],[374,608,486,666]],"answer":4}
```

### task_pages__paired_forms__shortfall_minus_overage_value / answer_and_annotation / sample 7630874396360166

- `query_id`: `single`
- `instance_seed`: `7630874396360166`
- `word_count`: `101`
- `body_word_count`: `45`

```text
This page shows two side-by-side business forms, a purchase order and a receiving slip, with matching item codes and visible quantities. What integer value results from summing purchase-order unit value times ordered-minus-received quantity for every mismatched row?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for the full receiving-slip rows whose received quantity differs from the matching purchase-order quantity.
Required answer format: set "answer" to the computed integer shortfall-minus-overage value.
Example JSON:
{"annotation":[[850,340,1268,378],[850,388,1268,426],[850,436,1268,474]],"answer":324}
```

### task_pages__category_grid__category_slot_item_label / answer_and_annotation / sample 962532276611877

- `query_id`: `single`
- `instance_seed`: `962532276611877`
- `word_count`: `100`
- `body_word_count`: `33`

```text
The visual shows a category grid page with category headers, subcategory headers, and short item rows. Read the fourth item under "Transfer" within category "Media".
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "category_header", "subcategory_header", and "target_item", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the exact visible item label requested by the question.
Example JSON:
{"annotation":{"category_header":[20,40,210,78],"subcategory_header":[28,90,190,116],"target_item":[32,146,202,168]},"answer":"Amber Leaf"}
```

### task_pages__infographic__section_icon_total_difference_value / answer_and_annotation / sample 1614288303312218

- `query_id`: `single`
- `instance_seed`: `1614288303312218`
- `word_count`: `99`
- `body_word_count`: `38`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using only cards marked with the folder icon, compute the absolute total gap between "Beverage" and "Apparel".
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "section_a_filtered_icon_cards" and "section_b_filtered_icon_cards", each mapped to a list of matching metric card [x0, y0, x1, y1] pixel bounding boxes.
Format for the "answer" field: set "answer" to the requested integer.
Example JSON:
{"annotation":{"section_a_filtered_icon_cards":[[108,164,248,258],[252,164,392,258]],"section_b_filtered_icon_cards":[[398,164,538,258]]},"answer":64}
```

### task_pages__calendar__workday_offset_date / answer_and_annotation / sample 5410970293453682

- `query_id`: `workday_after_offset_date`
- `instance_seed`: `5410970293453682`
- `word_count`: `98`
- `body_word_count`: `37`

```text
The canvas contains one month-view calendar with weekday headers, date cells, and one marked reference date. From the marked date, go 7 workdays later. What date number is that?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an object with keys "reference_date" and "target_date", each mapped to the [x0, y0, x1, y1] box of that date cell.
Answer field: set "answer" to the integer date number reached after moving the requested number of workdays from the marked date.
Example JSON:
{"annotation":{"reference_date":[354,256,456,352],"target_date":[560,256,662,352]},"answer":20}
```

### task_pages__calendar__workday_offset_date / answer_and_annotation / sample 5026260176069673

- `query_id`: `workday_before_offset_date`
- `instance_seed`: `5026260176069673`
- `word_count`: `98`
- `body_word_count`: `37`

```text
The page contains one month-view calendar with weekday headers, date cells, and one marked reference date. Counting only workdays, which date is 5 workdays before the marked reference date?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an object with keys "reference_date" and "target_date", each mapped to the [x0, y0, x1, y1] box of that date cell.
Answer format: set "answer" to the integer date number reached before moving the requested number of workdays from the marked date.
Example JSON:
{"annotation":{"reference_date":[560,256,662,352],"target_date":[354,256,456,352]},"answer":18}
```

### task_pages__concept_map__marked_child_count / answer_and_annotation / sample 5836206212209361

- `query_id`: `single`
- `instance_seed`: `5836206212209361`
- `word_count`: `98`
- `body_word_count`: `36`

```text
The concept map shows a central topic, labeled branches, visible child-item nodes, small marker icons, and connector lines. How many child items under "Quality" have the circle marker?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted marked child-item nodes.
Answer format: set "answer" to the integer count of visible child-item nodes under the requested branch that have the requested marker.
Example JSON:
{"annotation":[[240,180,370,216],[240,276,370,312],[240,324,370,360]],"answer":3}
```

### task_pages__record_table__value_threshold_in_group_count / answer_and_annotation / sample 5296313908776588

- `query_id`: `single`
- `instance_seed`: `5296313908776588`
- `word_count`: `98`
- `body_word_count`: `32`

```text
The image shows a sectioned record table in a desktop application. In the "Inbox" section, how many rows have Size at least 65 MB?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around every counted row.
Format for the "answer" field: set "answer" to the integer count of rows in the requested section whose Size is at least the threshold.
Example JSON:
{"annotation":[[72,236,1208,264],[72,292,1208,320],[72,404,1208,432]],"answer":3}
```

### task_pages__schema__join_path_length_value / answer_and_annotation / sample 2610934651459491

- `query_id`: `single`
- `instance_seed`: `2610934651459491`
- `word_count`: `98`
- `body_word_count`: `37`

```text
The visual shows database tables with field rows, key markers, cardinality markers, and relationship lines. What is the fewest number of relationship lines needed to connect "Session" to "Newsletter"?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to a JSON array of line segments; each segment is [[x0, y0], [x1, y1]] for one relationship line on the shortest path.
Required answer format: set "answer" to the integer number of relationship lines on the shortest path between the two requested tables.
Example JSON:
{"annotation":[[[150,180],[330,260]],[[330,260],[520,260]]],"answer":2}
```

### task_pages__workspace__control_label / answer_and_annotation / sample 6566443435970051

- `query_id`: `single`
- `instance_seed`: `6566443435970051`
- `word_count`: `98`
- `body_word_count`: `49`

```text
The figure shows a professional application workspace with a shuffled guide, context rows, coded headers, and labeled controls. Find the row and coded column implied by this instruction: Select the labeled control for "show item" in "Data".. Which label is shown?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to the [x0, y0, x1, y1] box around the target labeled control in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"annotation":[520,360,690,444],"answer":"G"}
```

### task_pages__form_section__two_amount_arithmetic_value / answer_and_annotation / sample 7401663078445916

- `query_id`: `difference_two_amounts_in_section_value`
- `instance_seed`: `7401663078445916`
- `word_count`: `97`
- `body_word_count`: `32`

```text
The page shows a structured document with visible section headers and labeled currency fields. Read the "Billing Summary" section and compute "Archive" minus "Discount".
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Annotation format: set "annotation" to an object mapping "first_operand" and "second_operand" to the referenced operand field boxes [x0, y0, x1, y1], including each field label and value.
Example JSON:
{"annotation":{"first_operand":[120,248,420,306],"second_operand":[120,308,420,366]},"answer":"$42.50"}
```

### task_pages__hero_callout_infographic__callout_metric_extremum_label / answer_and_annotation / sample 2355758423162620

- `query_id`: `lowest_field_value_callout_label`
- `instance_seed`: `2355758423162620`
- `word_count`: `97`
- `body_word_count`: `36`

```text
This infographic shows titled callout cards with field labels, visible values, badges, and connector lines. Using all visible "Score" values, identify the callout title with the lowest value.
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object mapping "winning_callout_card" and each compared "candidate_N_field_row" to [x0, y0, x1, y1] pixel bounding boxes.
Format for the "answer" field: set "answer" to the exact visible callout title requested by the question.
Example JSON:
{"annotation":{"winning_callout_card":[80,210,360,350],"candidate_1_field_row":[96,280,344,318],"candidate_2_field_row":[700,430,948,468]},"answer":"Atlas"}
```

### task_pages__timeline__event_date_gap_value / answer_and_annotation / sample 7025830844825715

- `query_id`: `single`
- `instance_seed`: `7025830844825715`
- `word_count`: `97`
- `body_word_count`: `33`

```text
The timeline shows one labeled milestone timeline with dated event cards and highlighted reference events. How many days apart are event F and event B?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "earlier_event" and "later_event", each mapped to the [x0, y0, x1, y1] box of that endpoint event card.
Format for the "answer" field: set "answer" to the nonnegative integer number of calendar days between the two named events.
Example JSON:
{"annotation":{"earlier_event":[160,158,264,228],"later_event":[538,158,642,228]},"answer":9}
```

### task_pages__infographic__section_total_extrema_difference_value / answer_and_annotation / sample 77085026798844

- `query_id`: `single`
- `instance_seed`: `77085026798844`
- `word_count`: `96`
- `body_word_count`: `35`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. What is the difference between the highest section total and the lowest section total?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to an object with keys "highest_total_section" and "lowest_total_section", each mapped to a list of supporting metric card [x0, y0, x1, y1] pixel bounding boxes.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":{"highest_total_section":[[108,164,248,258],[252,164,392,258]],"lowest_total_section":[[398,164,538,258],[542,164,682,258]]},"answer":64}
```

### task_pages__web_action__action_target_label / answer_and_annotation / sample 3637705091930165

- `query_id`: `select_option_label`
- `instance_seed`: `3637705091930165`
- `word_count`: `96`
- `body_word_count`: `52`

```text
This screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Find the option implied by this guide-code instruction: Choose the option for "Alert channel" with guide code "T4". Which label is shown?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel box around the target option and its candidate label marker.
Answer format: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"annotation":[410,378,584,442],"answer":"G"}
```

### task_pages__calendar__date_range_day_class_count / answer_and_annotation / sample 3400034276803113

- `query_id`: `weekday_range_count`
- `instance_seed`: `3400034276803113`
- `word_count`: `95`
- `body_word_count`: `38`

```text
The picture shows one month-view calendar with weekday headers, date cells, and two marked boundary dates. Using the two marked dates as inclusive endpoints, count the dates that are weekdays.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around all counted weekday date cells.
Answer format: set "answer" to the integer count of weekday dates in the inclusive marked range.
Example JSON:
{"annotation":[[148,256,250,352],[251,256,353,352],[354,256,456,352]],"answer":3}
```

## Repeated Scaffolding Terms

### task_pages__process_flow__condition_path_endpoint_label / answer_only / sample 2040856734394341

- `query_id`: `single`
- `instance_seed`: `2040856734394341`
- `word_count`: `68`
- `body_word_count`: `64`
- `repeated_terms`: `{'answer': 3}`

```text
The figure shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Begin at "Verify". Follow the decision labels "approve" then "pass"; use unlabeled arrows only to move between decisions. What step label do you land on?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible destination step label as a string.
Example JSON:
{"answer":"Publish"}
```

### task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label / answer_only / sample 331939245773630

- `query_id`: `single`
- `instance_seed`: `331939245773630`
- `word_count`: `63`
- `body_word_count`: `59`
- `repeated_terms`: `{'answer': 3}`

```text
The visual shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Using the "Count" field, total the listed values in modules "Software" and "Energy". Which module is larger?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible module title with the larger total.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__calendar__workday_offset_date / answer_only / sample 5410970293453682

- `query_id`: `workday_after_offset_date`
- `instance_seed`: `5410970293453682`
- `word_count`: `61`
- `body_word_count`: `57`
- `repeated_terms`: `{'answer': 3}`

```text
The canvas contains one month-view calendar with weekday headers, date cells, and one marked reference date. From the marked date, go 7 workdays later. What date number is that?
Return a JSON object with "answer" only.
Answer field: set "answer" to the integer date number reached after moving the requested number of workdays from the marked date.
Example JSON:
{"answer":20}
```

### task_pages__concept_map__marked_child_count / answer_only / sample 5836206212209361

- `query_id`: `single`
- `instance_seed`: `5836206212209361`
- `word_count`: `60`
- `body_word_count`: `56`
- `repeated_terms`: `{'answer': 3}`

```text
The concept map shows a central topic, labeled branches, visible child-item nodes, small marker icons, and connector lines. How many child items under "Quality" have the circle marker?
Return a JSON object with "answer" only.
Answer field: set "answer" to the integer count of visible child-item nodes under the requested branch that have the requested marker.
Example JSON:
{"answer":3}
```

### task_pages__calendar_event_grid__date_filled_slot_count / answer_only / sample 2207101115369380

- `query_id`: `single`
- `instance_seed`: `2207101115369380`
- `word_count`: `59`
- `body_word_count`: `55`
- `repeated_terms`: `{'answer': 3}`

```text
This page shows one month calendar where date cells contain short category chips in Top, Mid, and End event slots. Find date 20. How many event chips are shown in its slots?
Return a JSON object with "answer" only.
Answer field: set "answer" to the integer number of filled event slots on the requested date.
Example JSON:
{"answer":2}
```

### task_pages__calendar__date_range_day_class_count / answer_only / sample 3400034276803113

- `query_id`: `weekday_range_count`
- `instance_seed`: `3400034276803113`
- `word_count`: `57`
- `body_word_count`: `53`
- `repeated_terms`: `{'answer': 3}`

```text
The picture shows one month-view calendar with weekday headers, date cells, and two marked boundary dates. Using the two marked dates as inclusive endpoints, count the dates that are weekdays.
Return a JSON object with "answer" only.
Answer field: set "answer" to the integer count of weekday dates in the inclusive marked range.
Example JSON:
{"answer":3}
```

### task_pages__mixed_infographic_page__page_field_extremum_module_label / answer_only / sample 8818848054638216

- `query_id`: `single`
- `instance_seed`: `8818848054638216`
- `word_count`: `56`
- `body_word_count`: `52`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Using all visible modules with field "Reach", which module title has the lowest value?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible module title.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__instruction_panel__shared_control_for_step_set_label / answer_only / sample 7672964101085635

- `query_id`: `single`
- `instance_seed`: `7672964101085635`
- `word_count`: `54`
- `body_word_count`: `50`
- `repeated_terms`: `{'answer': 3}`

```text
The figure shows an instruction panel with numbered steps and visible control chips on each step. Which visible control label appears in each of steps 1 and 5?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible control label common to the referenced steps.
Example JSON:
{"answer":"Sync"}
```

### task_pages__web_action__guide_code_target_count / answer_only / sample 7551843831494709

- `query_id`: `click_guide_code_target_count`
- `instance_seed`: `7551843831494709`
- `word_count`: `53`
- `body_word_count`: `49`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Count all visible candidate controls using guide code "T4".
Return a JSON object with "answer" only.
Answer field: set "answer" to the number of matching candidate controls.
Example JSON:
{"answer":3}
```

### task_pages__profile_card_grid__field_ranked_profile_label / answer_only / sample 6247767060531509

- `query_id`: `nth_lowest_field_profile_label`
- `instance_seed`: `6247767060531509`
- `word_count`: `50`
- `body_word_count`: `46`
- `repeated_terms`: `{'answer': 3}`

```text
This page shows a grid of profile cards, each with a visible profile name and labeled fields. After ranking by ascending Score, what profile name is in third place?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible profile name.
Example JSON:
{"answer":"Aster"}
```

### task_pages__hierarchy__manager_most_total_reports_label / answer_only / sample 4840768874226773

- `query_id`: `single`
- `instance_seed`: `4840768874226773`
- `word_count`: `48`
- `body_word_count`: `44`
- `repeated_terms`: `{'answer': 3}`

```text
The visual shows an organization chart with the CEO at the top, labeled employees, and visible reporting lines. Which non-CEO manager has the largest total team under them?
Return a JSON object with "answer" only.
Answer field: set "answer" to the selected manager name.
Example JSON:
{"answer":"Morgan"}
```

### task_pages__infographic__sum_named_metrics_value / answer_only / sample 3733524850266373

- `query_id`: `single`
- `instance_seed`: `3733524850266373`
- `word_count`: `47`
- `body_word_count`: `43`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using the cards labeled "Quartz", "Birch", "Summit", "Flint", and "Umber", what is the combined value?
Return a JSON object with "answer" only.
Answer field: set "answer" to the requested integer.
Example JSON:
{"answer":64}
```

### task_pages__infographic__section_total_except_named_value / answer_only / sample 8940833545948757

- `query_id`: `single`
- `instance_seed`: `8940833545948757`
- `word_count`: `45`
- `body_word_count`: `41`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Within section "Dining", skip "Silver" and "Azure" and sum the remaining metric values.
Return a JSON object with "answer" only.
Answer field: set "answer" to the requested integer.
Example JSON:
{"answer":64}
```

### task_pages__hero_callout_infographic__callout_condition_count / answer_only / sample 5404889805439418

- `query_id`: `field_value_below_threshold_count`
- `instance_seed`: `5404889805439418`
- `word_count`: `44`
- `body_word_count`: `40`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows titled callout cards with field labels, visible values, badges, and connector lines. What count of callout cards satisfies "Score" below "90"?
Return a JSON object with "answer" only.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"answer":2}
```

## All Prompt Samples

### task_pages__calendar__date_range_day_class_count / weekday_range_count / answer_and_annotation / sample 3400034276803113

- `instance_seed`: `3400034276803113`
- `word_count`: `95`
- `body_word_count`: `38`

```text
The picture shows one month-view calendar with weekday headers, date cells, and two marked boundary dates. Using the two marked dates as inclusive endpoints, count the dates that are weekdays.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around all counted weekday date cells.
Answer format: set "answer" to the integer count of weekday dates in the inclusive marked range.
Example JSON:
{"annotation":[[148,256,250,352],[251,256,353,352],[354,256,456,352]],"answer":3}
```

### task_pages__calendar__date_range_day_class_count / weekday_range_count / answer_only / sample 3400034276803113

- `instance_seed`: `3400034276803113`
- `word_count`: `57`
- `body_word_count`: `53`

```text
The picture shows one month-view calendar with weekday headers, date cells, and two marked boundary dates. Using the two marked dates as inclusive endpoints, count the dates that are weekdays.
Return a JSON object with "answer" only.
Answer field: set "answer" to the integer count of weekday dates in the inclusive marked range.
Example JSON:
{"answer":3}
```

### task_pages__calendar__date_range_day_class_count / weekend_range_count / answer_and_annotation / sample 2300930941635308

- `instance_seed`: `2300930941635308`
- `word_count`: `92`
- `body_word_count`: `39`

```text
The image shows one month-view calendar with weekday headers, date cells, and two marked boundary dates. Between the two marked boundary dates, inclusive, how many dates fall on Saturday or Sunday?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around all counted weekend date cells.
Answer field: set "answer" to the integer count of weekend dates in the inclusive marked range.
Example JSON:
{"annotation":[[560,256,662,352],[663,256,765,352]],"answer":2}
```

### task_pages__calendar__date_range_day_class_count / weekend_range_count / answer_only / sample 2300930941635308

- `instance_seed`: `2300930941635308`
- `word_count`: `61`
- `body_word_count`: `38`

```text
The image shows one month-view calendar with weekday headers, date cells, and two marked boundary dates. Between the two marked boundary dates, inclusive, how many dates fall on Saturday or Sunday?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the integer count of weekend dates in the inclusive marked range.
Example JSON:
{"answer":2}
```

### task_pages__calendar__date_weekday_label / single / answer_and_annotation / sample 7090564677460468

- `instance_seed`: `7090564677460468`
- `word_count`: `104`
- `body_word_count`: `48`

```text
The picture shows one month-view calendar with weekday headers and date cells. Which weekday header is above date 21? Answer with the exact short header label shown in the calendar, such as Mon, Tue, Wed, Thu, Fri, Sat, or Sun.
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible three-letter weekday header label above the queried date, one of Mon, Tue, Wed, Thu, Fri, Sat, or Sun.
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the queried date cell.
Example JSON:
{"annotation":[354,256,456,352],"answer":"Wed"}
```

### task_pages__calendar__date_weekday_label / single / answer_only / sample 7090564677460468

- `instance_seed`: `7090564677460468`
- `word_count`: `80`
- `body_word_count`: `47`

```text
The picture shows one month-view calendar with weekday headers and date cells. Which weekday header is above date 21? Answer with the exact short header label shown in the calendar, such as Mon, Tue, Wed, Thu, Fri, Sat, or Sun.
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible three-letter weekday header label above the queried date, one of Mon, Tue, Wed, Thu, Fri, Sat, or Sun.
Example JSON:
{"answer":"Wed"}
```

### task_pages__calendar__marked_day_class_count / single / answer_and_annotation / sample 7986161836039903

- `instance_seed`: `7986161836039903`
- `word_count`: `88`
- `body_word_count`: `31`

```text
The canvas contains one month-view calendar with weekday headers, date cells, and several marked dates. Count the marked dates that are weekend days.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around all matching marked date cells; use [] if none match.
Answer field: set "answer" to the integer count of marked dates in the requested day class.
Example JSON:
{"annotation":[[148,352,250,448],[560,352,662,448]],"answer":2}
```

### task_pages__calendar__marked_day_class_count / single / answer_only / sample 7986161836039903

- `instance_seed`: `7986161836039903`
- `word_count`: `53`
- `body_word_count`: `30`

```text
The canvas contains one month-view calendar with weekday headers, date cells, and several marked dates. Count the marked dates that are weekend days.
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the integer count of marked dates in the requested day class.
Example JSON:
{"answer":2}
```

### task_pages__calendar__weekday_occurrence_date / single / answer_and_annotation / sample 6734166775306702

- `instance_seed`: `6734166775306702`
- `word_count`: `69`
- `body_word_count`: `31`

```text
The picture shows one month-view calendar with weekday headers and date cells. Using the calendar, identify the date number of the 3rd Friday.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the target date cell.
Answer format: set "answer" to the integer date number.
Example JSON:
{"annotation":[354,256,456,352],"answer":18}
```

### task_pages__calendar__weekday_occurrence_date / single / answer_only / sample 6734166775306702

- `instance_seed`: `6734166775306702`
- `word_count`: `44`
- `body_word_count`: `30`

```text
The picture shows one month-view calendar with weekday headers and date cells. Using the calendar, identify the date number of the 3rd Friday.
Return a JSON object with "answer" only.
Final answer format: set "answer" to the integer date number.
Example JSON:
{"answer":18}
```

### task_pages__calendar__workday_offset_date / workday_after_offset_date / answer_and_annotation / sample 5410970293453682

- `instance_seed`: `5410970293453682`
- `word_count`: `98`
- `body_word_count`: `37`

```text
The canvas contains one month-view calendar with weekday headers, date cells, and one marked reference date. From the marked date, go 7 workdays later. What date number is that?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an object with keys "reference_date" and "target_date", each mapped to the [x0, y0, x1, y1] box of that date cell.
Answer field: set "answer" to the integer date number reached after moving the requested number of workdays from the marked date.
Example JSON:
{"annotation":{"reference_date":[354,256,456,352],"target_date":[560,256,662,352]},"answer":20}
```

### task_pages__calendar__workday_offset_date / workday_after_offset_date / answer_only / sample 5410970293453682

- `instance_seed`: `5410970293453682`
- `word_count`: `61`
- `body_word_count`: `57`

```text
The canvas contains one month-view calendar with weekday headers, date cells, and one marked reference date. From the marked date, go 7 workdays later. What date number is that?
Return a JSON object with "answer" only.
Answer field: set "answer" to the integer date number reached after moving the requested number of workdays from the marked date.
Example JSON:
{"answer":20}
```

### task_pages__calendar__workday_offset_date / workday_before_offset_date / answer_and_annotation / sample 5026260176069673

- `instance_seed`: `5026260176069673`
- `word_count`: `98`
- `body_word_count`: `37`

```text
The page contains one month-view calendar with weekday headers, date cells, and one marked reference date. Counting only workdays, which date is 5 workdays before the marked reference date?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an object with keys "reference_date" and "target_date", each mapped to the [x0, y0, x1, y1] box of that date cell.
Answer format: set "answer" to the integer date number reached before moving the requested number of workdays from the marked date.
Example JSON:
{"annotation":{"reference_date":[560,256,662,352],"target_date":[354,256,456,352]},"answer":18}
```

### task_pages__calendar__workday_offset_date / workday_before_offset_date / answer_only / sample 5026260176069673

- `instance_seed`: `5026260176069673`
- `word_count`: `62`
- `body_word_count`: `36`

```text
The page contains one month-view calendar with weekday headers, date cells, and one marked reference date. Counting only workdays, which date is 5 workdays before the marked reference date?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer date number reached before moving the requested number of workdays from the marked date.
Example JSON:
{"answer":18}
```

### task_pages__calendar_event_grid__category_slot_day_count / single / answer_and_annotation / sample 6385092617231797

- `instance_seed`: `6385092617231797`
- `word_count`: `93`
- `body_word_count`: `38`

```text
The canvas contains one month calendar where date cells contain short category chips in Top, Mid, and End event slots. How many date cells contain "Travel" in their "End" slot?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the integer number of dates whose requested slot has the requested category label.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the matching event chips.
Example JSON:
{"annotation":[[268,286,376,304],[392,382,500,400]],"answer":2}
```

### task_pages__calendar_event_grid__category_slot_day_count / single / answer_only / sample 6385092617231797

- `instance_seed`: `6385092617231797`
- `word_count`: `62`
- `body_word_count`: `37`

```text
The canvas contains one month calendar where date cells contain short category chips in Top, Mid, and End event slots. How many date cells contain "Travel" in their "End" slot?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the integer number of dates whose requested slot has the requested category label.
Example JSON:
{"answer":2}
```

### task_pages__calendar_event_grid__date_filled_slot_count / single / answer_and_annotation / sample 2207101115369380

- `instance_seed`: `2207101115369380`
- `word_count`: `101`
- `body_word_count`: `40`

```text
This page shows one month calendar where date cells contain short category chips in Top, Mid, and End event slots. Find date 20. How many event chips are shown in its slots?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the event chips on the requested date, or [] if no slots are filled.
Answer format: set "answer" to the integer number of filled event slots on the requested date.
Example JSON:
{"annotation":[[268,286,376,304],[268,310,376,328]],"answer":2}
```

### task_pages__calendar_event_grid__date_filled_slot_count / single / answer_only / sample 2207101115369380

- `instance_seed`: `2207101115369380`
- `word_count`: `59`
- `body_word_count`: `55`

```text
This page shows one month calendar where date cells contain short category chips in Top, Mid, and End event slots. Find date 20. How many event chips are shown in its slots?
Return a JSON object with "answer" only.
Answer field: set "answer" to the integer number of filled event slots on the requested date.
Example JSON:
{"answer":2}
```

### task_pages__calendar_event_grid__date_for_category_slot_label / single / answer_and_annotation / sample 72309637066021

- `instance_seed`: `72309637066021`
- `word_count`: `84`
- `body_word_count`: `38`

```text
The canvas contains one month calendar where date cells contain short category chips in Top, Mid, and End event slots. Identify the date where the "Top" slot is labeled "Science".
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the [x0, y0, x1, y1] box around the matching event chip in image pixel coordinates.
Answer field: set "answer" to the integer date number whose requested slot contains the requested category label.
Example JSON:
{"annotation":[268,286,376,304],"answer":12}
```

### task_pages__calendar_event_grid__date_for_category_slot_label / single / answer_only / sample 72309637066021

- `instance_seed`: `72309637066021`
- `word_count`: `59`
- `body_word_count`: `37`

```text
The canvas contains one month calendar where date cells contain short category chips in Top, Mid, and End event slots. Identify the date where the "Top" slot is labeled "Science".
Return a JSON object with "answer" only.
Final answer format: set "answer" to the integer date number whose requested slot contains the requested category label.
Example JSON:
{"answer":12}
```

### task_pages__calendar_event_grid__date_slot_category_label / single / answer_and_annotation / sample 7458609207013418

- `instance_seed`: `7458609207013418`
- `word_count`: `87`
- `body_word_count`: `42`

```text
This page shows one month calendar where date cells contain short category chips in Top, Mid, and End event slots. Read the "Top" event slot on date 11. What category label is shown there?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the visible category label in the requested date and slot.
Annotation format: set "annotation" to the [x0, y0, x1, y1] box around the requested event chip in image pixel coordinates.
Example JSON:
{"annotation":[268,286,376,304],"answer":"Tech"}
```

### task_pages__calendar_event_grid__date_slot_category_label / single / answer_only / sample 7458609207013418

- `instance_seed`: `7458609207013418`
- `word_count`: `61`
- `body_word_count`: `41`

```text
This page shows one month calendar where date cells contain short category chips in Top, Mid, and End event slots. Read the "Top" event slot on date 11. What category label is shown there?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the visible category label in the requested date and slot.
Example JSON:
{"answer":"Tech"}
```

### task_pages__category_grid__category_item_count / single / answer_and_annotation / sample 64787926267776

- `instance_seed`: `64787926267776`
- `word_count`: `87`
- `body_word_count`: `35`

```text
The image shows a category grid page with category headers, subcategory headers, and short item rows. How many items are listed under subcategory "Aggregation" within category "Tickets"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted item rows.
Answer format: set "answer" to the integer count of visible item rows in the requested block.
Example JSON:
{"annotation":[[20,80,180,104],[20,110,180,134]],"answer":2}
```

### task_pages__category_grid__category_item_count / single / answer_only / sample 64787926267776

- `instance_seed`: `64787926267776`
- `word_count`: `55`
- `body_word_count`: `34`

```text
The image shows a category grid page with category headers, subcategory headers, and short item rows. How many items are listed under subcategory "Aggregation" within category "Tickets"?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the integer count of visible item rows in the requested block.
Example JSON:
{"answer":2}
```

### task_pages__category_grid__category_slot_item_label / single / answer_and_annotation / sample 962532276611877

- `instance_seed`: `962532276611877`
- `word_count`: `100`
- `body_word_count`: `33`

```text
The visual shows a category grid page with category headers, subcategory headers, and short item rows. Read the fourth item under "Transfer" within category "Media".
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "category_header", "subcategory_header", and "target_item", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the exact visible item label requested by the question.
Example JSON:
{"annotation":{"category_header":[20,40,210,78],"subcategory_header":[28,90,190,116],"target_item":[32,146,202,168]},"answer":"Amber Leaf"}
```

### task_pages__category_grid__category_slot_item_label / single / answer_only / sample 962532276611877

- `instance_seed`: `962532276611877`
- `word_count`: `52`
- `body_word_count`: `32`

```text
The visual shows a category grid page with category headers, subcategory headers, and short item rows. Read the fourth item under "Transfer" within category "Media".
Return a JSON object with "answer" only.
Final answer format: set "answer" to the exact visible item label requested by the question.
Example JSON:
{"answer":"Amber Leaf"}
```

### task_pages__concept_map__branch_child_count / single / answer_and_annotation / sample 7397351348282229

- `instance_seed`: `7397351348282229`
- `word_count`: `86`
- `body_word_count`: `31`

```text
The image shows a central topic, labeled branches, visible child-item nodes, and connector lines. What is the number of child items under "Media"?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted child-item nodes.
Required answer format: set "answer" to the integer count of visible child-item nodes directly under the requested branch.
Example JSON:
{"annotation":[[240,180,370,216],[240,228,370,264]],"answer":2}
```

### task_pages__concept_map__branch_child_count / single / answer_only / sample 7397351348282229

- `instance_seed`: `7397351348282229`
- `word_count`: `52`
- `body_word_count`: `30`

```text
The image shows a central topic, labeled branches, visible child-item nodes, and connector lines. What is the number of child items under "Media"?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of visible child-item nodes directly under the requested branch.
Example JSON:
{"answer":2}
```

### task_pages__concept_map__marked_child_count / single / answer_and_annotation / sample 5836206212209361

- `instance_seed`: `5836206212209361`
- `word_count`: `98`
- `body_word_count`: `36`

```text
The concept map shows a central topic, labeled branches, visible child-item nodes, small marker icons, and connector lines. How many child items under "Quality" have the circle marker?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted marked child-item nodes.
Answer format: set "answer" to the integer count of visible child-item nodes under the requested branch that have the requested marker.
Example JSON:
{"annotation":[[240,180,370,216],[240,276,370,312],[240,324,370,360]],"answer":3}
```

### task_pages__concept_map__marked_child_count / single / answer_only / sample 5836206212209361

- `instance_seed`: `5836206212209361`
- `word_count`: `60`
- `body_word_count`: `56`

```text
The concept map shows a central topic, labeled branches, visible child-item nodes, small marker icons, and connector lines. How many child items under "Quality" have the circle marker?
Return a JSON object with "answer" only.
Answer field: set "answer" to the integer count of visible child-item nodes under the requested branch that have the requested marker.
Example JSON:
{"answer":3}
```

### task_pages__concept_map__ordered_child_label / single / answer_and_annotation / sample 2913927909803227

- `instance_seed`: `2913927909803227`
- `word_count`: `87`
- `body_word_count`: `43`

```text
The concept map shows a central topic, labeled branches, visible child-item nodes, and connector lines. Use the child-item order under "Domestic" (from top to bottom, breaking ties from left to right). What label is 5th?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a [x0, y0, x1, y1] box in image pixel coordinates around the selected child-item node.
Answer format: set "answer" to the exact visible child-item label requested by the question.
Example JSON:
{"annotation":[280,210,420,248],"answer":"New York"}
```

### task_pages__concept_map__ordered_child_label / single / answer_only / sample 2913927909803227

- `instance_seed`: `2913927909803227`
- `word_count`: `61`
- `body_word_count`: `42`

```text
The concept map shows a central topic, labeled branches, visible child-item nodes, and connector lines. Use the child-item order under "Domestic" (from top to bottom, breaking ties from left to right). What label is 5th?
Return a JSON object with "answer" only.
Answer format: set "answer" to the exact visible child-item label requested by the question.
Example JSON:
{"answer":"New York"}
```

### task_pages__control_board__control_state_condition_count / disabled_controls_in_group_count / answer_and_annotation / sample 5798127058265131

- `instance_seed`: `5798127058265131`
- `word_count`: `83`
- `body_word_count`: `28`

```text
The visual shows grouped labeled controls in a desktop application. For the "Review" group, determine how many controls are disabled.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted disabled controls.
Answer format: set "answer" to the integer count of disabled controls in the requested group.
Example JSON:
{"annotation":[[96,218,221,300],[233,218,358,300],[370,310,495,392]],"answer":3}
```

### task_pages__control_board__control_state_condition_count / disabled_controls_in_group_count / answer_only / sample 5798127058265131

- `instance_seed`: `5798127058265131`
- `word_count`: `47`
- `body_word_count`: `27`

```text
The visual shows grouped labeled controls in a desktop application. For the "Review" group, determine how many controls are disabled.
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of disabled controls in the requested group.
Example JSON:
{"answer":3}
```

### task_pages__control_board__control_state_condition_count / selected_enabled_controls_in_group_count / answer_and_annotation / sample 4197696829961105

- `instance_seed`: `4197696829961105`
- `word_count`: `93`
- `body_word_count`: `32`

```text
The image shows grouped labeled controls in a desktop application. Looking only at the "Output" group, how many controls are selected without being disabled?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted selected enabled controls.
Answer format: set "answer" to the integer count of controls in the requested group that are both selected and enabled.
Example JSON:
{"annotation":[[96,218,221,300],[233,218,358,300],[370,310,495,392]],"answer":3}
```

### task_pages__control_board__control_state_condition_count / selected_enabled_controls_in_group_count / answer_only / sample 4197696829961105

- `instance_seed`: `4197696829961105`
- `word_count`: `56`
- `body_word_count`: `31`

```text
The image shows grouped labeled controls in a desktop application. Looking only at the "Output" group, how many controls are selected without being disabled?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of controls in the requested group that are both selected and enabled.
Example JSON:
{"answer":3}
```

### task_pages__cycle__offset_stage_label / after_stage_offset_label / answer_and_annotation / sample 8756763697065600

- `instance_seed`: `8756763697065600`
- `word_count`: `78`
- `body_word_count`: `34`

```text
This diagram shows a directed cycle with labeled stages connected by arrows. Starting from "Nada", move 2 steps after along the arrows. Which stage is reached?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the correct stage box.
Answer field: set "answer" to the exact visible stage label reached after following the prompt.
Example JSON:
{"annotation":[747,242,869,300],"answer":"Mina"}
```

### task_pages__cycle__offset_stage_label / after_stage_offset_label / answer_only / sample 8756763697065600

- `instance_seed`: `8756763697065600`
- `word_count`: `55`
- `body_word_count`: `33`

```text
This diagram shows a directed cycle with labeled stages connected by arrows. Starting from "Nada", move 2 steps after along the arrows. Which stage is reached?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible stage label reached after following the prompt.
Example JSON:
{"answer":"Mina"}
```

### task_pages__cycle__offset_stage_label / before_stage_offset_label / answer_and_annotation / sample 1303641292798311

- `instance_seed`: `1303641292798311`
- `word_count`: `79`
- `body_word_count`: `34`

```text
This diagram shows a directed cycle with labeled stages connected by arrows. Use the arrows and count 2 steps before "Doll". What stage do you reach?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible stage label reached after following the prompt.
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the correct stage box.
Example JSON:
{"annotation":[747,242,869,300],"answer":"Mina"}
```

### task_pages__cycle__offset_stage_label / before_stage_offset_label / answer_only / sample 1303641292798311

- `instance_seed`: `1303641292798311`
- `word_count`: `55`
- `body_word_count`: `33`

```text
This diagram shows a directed cycle with labeled stages connected by arrows. Use the arrows and count 2 steps before "Doll". What stage do you reach?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible stage label reached after following the prompt.
Example JSON:
{"answer":"Mina"}
```

### task_pages__form_section__sum_minus_amount_in_section_value / single / answer_and_annotation / sample 4106865584098799

- `instance_seed`: `4106865584098799`
- `word_count`: `117`
- `body_word_count`: `47`

```text
This page shows a structured document with visible section headers and labeled currency fields. In the "Fees" section, what is "Facility Fee" plus "Service Fee" minus "Registration Fee"? Use currency notation with exactly two digits after the decimal point.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an object mapping "first_operand", "second_operand", and "third_operand" to the referenced operand field boxes [x0, y0, x1, y1], including each field label and value.
Answer format: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Example JSON:
{"annotation":{"first_operand":[120,248,420,306],"second_operand":[120,308,420,366],"third_operand":[120,368,420,426]},"answer":"$133.30"}
```

### task_pages__form_section__sum_minus_amount_in_section_value / single / answer_only / sample 4106865584098799

- `instance_seed`: `4106865584098799`
- `word_count`: `73`
- `body_word_count`: `46`

```text
This page shows a structured document with visible section headers and labeled currency fields. In the "Fees" section, what is "Facility Fee" plus "Service Fee" minus "Registration Fee"? Use currency notation with exactly two digits after the decimal point.
Return a JSON object with "answer" only.
Final answer format: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Example JSON:
{"answer":"$133.30"}
```

### task_pages__form_section__two_amount_arithmetic_value / difference_two_amounts_in_section_value / answer_and_annotation / sample 7401663078445916

- `instance_seed`: `7401663078445916`
- `word_count`: `97`
- `body_word_count`: `32`

```text
The page shows a structured document with visible section headers and labeled currency fields. Read the "Billing Summary" section and compute "Archive" minus "Discount".
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Annotation format: set "annotation" to an object mapping "first_operand" and "second_operand" to the referenced operand field boxes [x0, y0, x1, y1], including each field label and value.
Example JSON:
{"annotation":{"first_operand":[120,248,420,306],"second_operand":[120,308,420,366]},"answer":"$42.50"}
```

### task_pages__form_section__two_amount_arithmetic_value / difference_two_amounts_in_section_value / answer_only / sample 7401663078445916

- `instance_seed`: `7401663078445916`
- `word_count`: `60`
- `body_word_count`: `31`

```text
The page shows a structured document with visible section headers and labeled currency fields. Read the "Billing Summary" section and compute "Archive" minus "Discount".
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Example JSON:
{"answer":"$42.50"}
```

### task_pages__form_section__two_amount_arithmetic_value / sum_two_amounts_in_section_value / answer_and_annotation / sample 610633119778029

- `instance_seed`: `610633119778029`
- `word_count`: `105`
- `body_word_count`: `35`

```text
The image shows a structured document with visible section headers and labeled currency fields. Using only the "Totals" section, add "Rounding" and "Bag Fee". What amount results?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object mapping "first_operand" and "second_operand" to the referenced operand field boxes [x0, y0, x1, y1], including each field label and value.
Format for the "answer" field: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Example JSON:
{"annotation":{"first_operand":[120,248,420,306],"second_operand":[120,308,420,366]},"answer":"$146.80"}
```

### task_pages__form_section__two_amount_arithmetic_value / sum_two_amounts_in_section_value / answer_only / sample 610633119778029

- `instance_seed`: `610633119778029`
- `word_count`: `60`
- `body_word_count`: `34`

```text
The image shows a structured document with visible section headers and labeled currency fields. Using only the "Totals" section, add "Rounding" and "Bag Fee". What amount results?
Return a JSON object with "answer" only.
Answer format: set "answer" to the computed amount formatted as a currency string with exactly two digits after the decimal point.
Example JSON:
{"answer":"$146.80"}
```

### task_pages__hero_callout_infographic__callout_condition_count / field_value_above_threshold_count / answer_and_annotation / sample 2867278009999226

- `instance_seed`: `2867278009999226`
- `word_count`: `83`
- `body_word_count`: `35`

```text
This infographic shows titled callout cards with field labels, visible values, badges, and connector lines. Across the callout cards, what is the number with "Score" above "48"?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an array of [x0, y0, x1, y1] pixel bounding boxes for the matching field rows.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[96,280,344,318],[700,430,948,468]],"answer":2}
```

### task_pages__hero_callout_infographic__callout_condition_count / field_value_above_threshold_count / answer_only / sample 2867278009999226

- `instance_seed`: `2867278009999226`
- `word_count`: `48`
- `body_word_count`: `34`

```text
This infographic shows titled callout cards with field labels, visible values, badges, and connector lines. Across the callout cards, what is the number with "Score" above "48"?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":2}
```

### task_pages__hero_callout_infographic__callout_condition_count / field_value_below_threshold_count / answer_and_annotation / sample 5404889805439418

- `instance_seed`: `5404889805439418`
- `word_count`: `80`
- `body_word_count`: `32`

```text
The image shows titled callout cards with field labels, visible values, badges, and connector lines. What count of callout cards satisfies "Score" below "90"?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an array of [x0, y0, x1, y1] pixel bounding boxes for the matching field rows.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[96,280,344,318],[700,430,948,468]],"answer":2}
```

### task_pages__hero_callout_infographic__callout_condition_count / field_value_below_threshold_count / answer_only / sample 5404889805439418

- `instance_seed`: `5404889805439418`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The image shows titled callout cards with field labels, visible values, badges, and connector lines. What count of callout cards satisfies "Score" below "90"?
Return a JSON object with "answer" only.
Answer field: set "answer" to the requested integer count.
Example JSON:
{"answer":2}
```

### task_pages__hero_callout_infographic__callout_field_value_label / single / answer_and_annotation / sample 6180802312778606

- `instance_seed`: `6180802312778606`
- `word_count`: `85`
- `body_word_count`: `32`

```text
This infographic shows titled callout cards with field labels, visible values, badges, and connector lines. What value appears beside field "Reach" in callout "Hardware"?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object mapping "target_callout_card" and "target_field_row" to [x0, y0, x1, y1] pixel bounding boxes.
Format for the "answer" field: set "answer" to the exact visible value requested by the question.
Example JSON:
{"annotation":{"target_callout_card":[80,210,360,350],"target_field_row":[96,280,344,318]},"answer":"42k"}
```

### task_pages__hero_callout_infographic__callout_field_value_label / single / answer_only / sample 6180802312778606

- `instance_seed`: `6180802312778606`
- `word_count`: `51`
- `body_word_count`: `31`

```text
This infographic shows titled callout cards with field labels, visible values, badges, and connector lines. What value appears beside field "Reach" in callout "Hardware"?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible value requested by the question.
Example JSON:
{"answer":"42k"}
```

### task_pages__hero_callout_infographic__callout_metric_extremum_label / highest_field_value_callout_label / answer_and_annotation / sample 854874820637

- `instance_seed`: `854874820637`
- `word_count`: `90`
- `body_word_count`: `34`

```text
The page shows titled callout cards with field labels, visible values, badges, and connector lines. Scan the callout cards that show "Rate". Which callout is highest?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible callout title requested by the question.
Annotation format: set "annotation" to an object mapping "winning_callout_card" and each compared "candidate_N_field_row" to [x0, y0, x1, y1] pixel bounding boxes.
Example JSON:
{"annotation":{"winning_callout_card":[80,210,360,350],"candidate_1_field_row":[96,280,344,318],"candidate_2_field_row":[700,430,948,468]},"answer":"Atlas"}
```

### task_pages__hero_callout_infographic__callout_metric_extremum_label / highest_field_value_callout_label / answer_only / sample 854874820637

- `instance_seed`: `854874820637`
- `word_count`: `51`
- `body_word_count`: `33`

```text
The page shows titled callout cards with field labels, visible values, badges, and connector lines. Scan the callout cards that show "Rate". Which callout is highest?
Return a JSON object with "answer" only.
Answer format: set "answer" to the exact visible callout title requested by the question.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__hero_callout_infographic__callout_metric_extremum_label / lowest_field_value_callout_label / answer_and_annotation / sample 2355758423162620

- `instance_seed`: `2355758423162620`
- `word_count`: `97`
- `body_word_count`: `36`

```text
This infographic shows titled callout cards with field labels, visible values, badges, and connector lines. Using all visible "Score" values, identify the callout title with the lowest value.
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object mapping "winning_callout_card" and each compared "candidate_N_field_row" to [x0, y0, x1, y1] pixel bounding boxes.
Format for the "answer" field: set "answer" to the exact visible callout title requested by the question.
Example JSON:
{"annotation":{"winning_callout_card":[80,210,360,350],"candidate_1_field_row":[96,280,344,318],"candidate_2_field_row":[700,430,948,468]},"answer":"Atlas"}
```

### task_pages__hero_callout_infographic__callout_metric_extremum_label / lowest_field_value_callout_label / answer_only / sample 2355758423162620

- `instance_seed`: `2355758423162620`
- `word_count`: `56`
- `body_word_count`: `35`

```text
This infographic shows titled callout cards with field labels, visible values, badges, and connector lines. Using all visible "Score" values, identify the callout title with the lowest value.
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible callout title requested by the question.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__hierarchy__manager_most_direct_reports_label / single / answer_and_annotation / sample 957783911759410

- `instance_seed`: `957783911759410`
- `word_count`: `80`
- `body_word_count`: `37`

```text
This diagram shows an organization chart with the CEO at the top, labeled employees, and visible reporting lines. Among managers below the CEO, who has the most direct reports?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the selected manager.
Format for the "answer" field: set "answer" to the selected manager name.
Example JSON:
{"annotation":[424,316,508,364],"answer":"Morgan"}
```

### task_pages__hierarchy__manager_most_direct_reports_label / single / answer_only / sample 957783911759410

- `instance_seed`: `957783911759410`
- `word_count`: `49`
- `body_word_count`: `36`

```text
This diagram shows an organization chart with the CEO at the top, labeled employees, and visible reporting lines. Among managers below the CEO, who has the most direct reports?
Return a JSON object with "answer" only.
Answer format: set "answer" to the selected manager name.
Example JSON:
{"answer":"Morgan"}
```

### task_pages__hierarchy__manager_most_total_reports_label / single / answer_and_annotation / sample 4840768874226773

- `instance_seed`: `4840768874226773`
- `word_count`: `73`
- `body_word_count`: `36`

```text
The visual shows an organization chart with the CEO at the top, labeled employees, and visible reporting lines. Which non-CEO manager has the largest total team under them?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the selected manager.
Answer format: set "answer" to the selected manager name.
Example JSON:
{"annotation":[424,316,508,364],"answer":"Morgan"}
```

### task_pages__hierarchy__manager_most_total_reports_label / single / answer_only / sample 4840768874226773

- `instance_seed`: `4840768874226773`
- `word_count`: `48`
- `body_word_count`: `44`

```text
The visual shows an organization chart with the CEO at the top, labeled employees, and visible reporting lines. Which non-CEO manager has the largest total team under them?
Return a JSON object with "answer" only.
Answer field: set "answer" to the selected manager name.
Example JSON:
{"answer":"Morgan"}
```

### task_pages__hierarchy__subtree_descendant_count / single / answer_and_annotation / sample 7237503248477476

- `instance_seed`: `7237503248477476`
- `word_count`: `101`
- `body_word_count`: `38`

```text
The figure shows an organization chart with the CEO at the top, labeled employees, and visible reporting lines. What is the total number of people under "Moon" in the chart?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around every counted person.
Format for the "answer" field: set "answer" to the integer count of people under the requested manager.
Example JSON:
{"annotation":[[256,316,368,374],[196,462,308,520],[374,462,486,520],[374,608,486,666]],"answer":4}
```

### task_pages__hierarchy__subtree_descendant_count / single / answer_only / sample 7237503248477476

- `instance_seed`: `7237503248477476`
- `word_count`: `58`
- `body_word_count`: `37`

```text
The figure shows an organization chart with the CEO at the top, labeled employees, and visible reporting lines. What is the total number of people under "Moon" in the chart?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the integer count of people under the requested manager.
Example JSON:
{"answer":4}
```

### task_pages__infographic__global_metric_ranked_item_label / nth_highest_metric_label / answer_and_annotation / sample 7980172497947108

- `instance_seed`: `7980172497947108`
- `word_count`: `79`
- `body_word_count`: `34`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Order all metric-card values from highest to lowest. What card label is second?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to the selected metric card [x0, y0, x1, y1] pixel bounding box.
Format for the "answer" field: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"annotation":[108,164,248,258],"answer":"Atlas"}
```

### task_pages__infographic__global_metric_ranked_item_label / nth_highest_metric_label / answer_only / sample 7980172497947108

- `instance_seed`: `7980172497947108`
- `word_count`: `52`
- `body_word_count`: `33`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Order all metric-card values from highest to lowest. What card label is second?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__infographic__global_metric_ranked_item_label / nth_lowest_metric_label / answer_and_annotation / sample 3671047891166266

- `instance_seed`: `3671047891166266`
- `word_count`: `71`
- `body_word_count`: `30`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Which metric card has the third lowest printed value?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to the selected metric card [x0, y0, x1, y1] pixel bounding box.
Required answer format: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"annotation":[108,164,248,258],"answer":"Atlas"}
```

### task_pages__infographic__global_metric_ranked_item_label / nth_lowest_metric_label / answer_only / sample 3671047891166266

- `instance_seed`: `3671047891166266`
- `word_count`: `50`
- `body_word_count`: `29`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Which metric card has the third lowest printed value?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__infographic__metric_card_field_lookup / detail_for_named_item / answer_and_annotation / sample 7687572838647059

- `instance_seed`: `7687572838647059`
- `word_count`: `74`
- `body_word_count`: `32`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Find card "River" within section "Footwear". What reference code is shown?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to the supporting metric card [x0, y0, x1, y1] pixel bounding box.
Required answer format: set "answer" to the exact visible reference code requested by the question.
Example JSON:
{"annotation":[108,164,248,258],"answer":"Ref 42"}
```

### task_pages__infographic__metric_card_field_lookup / detail_for_named_item / answer_only / sample 7687572838647059

- `instance_seed`: `7687572838647059`
- `word_count`: `51`
- `body_word_count`: `31`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Find card "River" within section "Footwear". What reference code is shown?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible reference code requested by the question.
Example JSON:
{"answer":"Ref 42"}
```

### task_pages__infographic__metric_card_field_lookup / item_for_named_value / answer_and_annotation / sample 1386634694740366

- `instance_seed`: `1386634694740366`
- `word_count`: `76`
- `body_word_count`: `31`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Which metric card in section "Gaming" shows the value "79"?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to the supporting metric card [x0, y0, x1, y1] pixel bounding box.
Format for the "answer" field: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"annotation":[108,164,248,258],"answer":"Atlas"}
```

### task_pages__infographic__metric_card_field_lookup / item_for_named_value / answer_only / sample 1386634694740366

- `instance_seed`: `1386634694740366`
- `word_count`: `49`
- `body_word_count`: `30`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Which metric card in section "Gaming" shows the value "79"?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__infographic__metric_card_field_lookup / value_for_named_item / answer_and_annotation / sample 2950455457511194

- `instance_seed`: `2950455457511194`
- `word_count`: `75`
- `body_word_count`: `31`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Look in section "Hardware". What printed value belongs to "River"?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to the supporting metric card [x0, y0, x1, y1] pixel bounding box.
Format for the "answer" field: set "answer" to the exact visible value requested by the question.
Example JSON:
{"annotation":[108,164,248,258],"answer":"64"}
```

### task_pages__infographic__metric_card_field_lookup / value_for_named_item / answer_only / sample 2950455457511194

- `instance_seed`: `2950455457511194`
- `word_count`: `47`
- `body_word_count`: `30`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Look in section "Hardware". What printed value belongs to "River"?
Return a JSON object with "answer" only.
Answer format: set "answer" to the exact visible value requested by the question.
Example JSON:
{"answer":"64"}
```

### task_pages__infographic__section_extrema_arithmetic_value / single / answer_and_annotation / sample 2764593262160760

- `instance_seed`: `2764593262160760`
- `word_count`: `91`
- `body_word_count`: `40`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Find the minimum value in section "Music" and the minimum value in section "Pharmacy". What is their absolute difference?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to an object with keys "section_a_extremum" and "section_b_extremum", each mapped to the supporting metric card [x0, y0, x1, y1] pixel bounding box.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":{"section_a_extremum":[108,164,248,258],"section_b_extremum":[398,164,538,258]},"answer":64}
```

### task_pages__infographic__section_extrema_arithmetic_value / single / answer_only / sample 2764593262160760

- `instance_seed`: `2764593262160760`
- `word_count`: `52`
- `body_word_count`: `39`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Find the minimum value in section "Music" and the minimum value in section "Pharmacy". What is their absolute difference?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"answer":64}
```

### task_pages__infographic__section_icon_extremum_label / single / answer_and_annotation / sample 534188421399181

- `instance_seed`: `534188421399181`
- `word_count`: `74`
- `body_word_count`: `34`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using only cards with the mail icon, which section has the lowest total?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the answer section panel [x0, y0, x1, y1] pixel bounding box.
Answer field: set "answer" to the exact visible section label requested by the question.
Example JSON:
{"annotation":[80,120,420,360],"answer":"Program Totals"}
```

### task_pages__infographic__section_icon_extremum_label / single / answer_only / sample 534188421399181

- `instance_seed`: `534188421399181`
- `word_count`: `52`
- `body_word_count`: `33`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using only cards with the mail icon, which section has the lowest total?
Return a JSON object with "answer" only.
Answer format: set "answer" to the exact visible section label requested by the question.
Example JSON:
{"answer":"Program Totals"}
```

### task_pages__infographic__section_icon_total_difference_value / single / answer_and_annotation / sample 1614288303312218

- `instance_seed`: `1614288303312218`
- `word_count`: `99`
- `body_word_count`: `38`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using only cards marked with the folder icon, compute the absolute total gap between "Beverage" and "Apparel".
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "section_a_filtered_icon_cards" and "section_b_filtered_icon_cards", each mapped to a list of matching metric card [x0, y0, x1, y1] pixel bounding boxes.
Format for the "answer" field: set "answer" to the requested integer.
Example JSON:
{"annotation":{"section_a_filtered_icon_cards":[[108,164,248,258],[252,164,392,258]],"section_b_filtered_icon_cards":[[398,164,538,258]]},"answer":64}
```

### task_pages__infographic__section_icon_total_difference_value / single / answer_only / sample 1614288303312218

- `instance_seed`: `1614288303312218`
- `word_count`: `50`
- `body_word_count`: `37`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using only cards marked with the folder icon, compute the absolute total gap between "Beverage" and "Apparel".
Return a JSON object with "answer" only.
Final answer format: set "answer" to the requested integer.
Example JSON:
{"answer":64}
```

### task_pages__infographic__section_icon_total_value / single / answer_and_annotation / sample 1117582816192243

- `instance_seed`: `1117582816192243`
- `word_count`: `75`
- `body_word_count`: `33`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. What total do you get from the inventory-icon cards in section "Telecom"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes for the matching icon-filtered metric cards.
Answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":[[108,164,248,258],[398,164,538,258]],"answer":64}
```

### task_pages__infographic__section_icon_total_value / single / answer_only / sample 1117582816192243

- `instance_seed`: `1117582816192243`
- `word_count`: `45`
- `body_word_count`: `32`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. What total do you get from the inventory-icon cards in section "Telecom"?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"answer":64}
```

### task_pages__infographic__section_metric_ranked_item_label / nth_highest_metric_in_section_label / answer_and_annotation / sample 4837291464059707

- `instance_seed`: `4837291464059707`
- `word_count`: `74`
- `body_word_count`: `35`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using the cards in section "Furniture", identify the label with the second highest value.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the selected metric card [x0, y0, x1, y1] pixel bounding box.
Answer field: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"annotation":[108,164,248,258],"answer":"Atlas"}
```

### task_pages__infographic__section_metric_ranked_item_label / nth_highest_metric_in_section_label / answer_only / sample 4837291464059707

- `instance_seed`: `4837291464059707`
- `word_count`: `53`
- `body_word_count`: `34`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using the cards in section "Furniture", identify the label with the second highest value.
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__infographic__section_metric_ranked_item_label / nth_lowest_metric_in_section_label / answer_and_annotation / sample 5207821352142891

- `instance_seed`: `5207821352142891`
- `word_count`: `79`
- `body_word_count`: `39`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Looking only at section "Kitchen", which metric label is second when values are sorted from lowest to highest?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible metric-card label requested by the question.
Annotation format: set "annotation" to the selected metric card [x0, y0, x1, y1] pixel bounding box.
Example JSON:
{"annotation":[108,164,248,258],"answer":"Atlas"}
```

### task_pages__infographic__section_metric_ranked_item_label / nth_lowest_metric_in_section_label / answer_only / sample 5207821352142891

- `instance_seed`: `5207821352142891`
- `word_count`: `56`
- `body_word_count`: `38`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Looking only at section "Kitchen", which metric label is second when values are sorted from lowest to highest?
Return a JSON object with "answer" only.
Answer format: set "answer" to the exact visible metric-card label requested by the question.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__infographic__section_ranked_total_label / single / answer_and_annotation / sample 7075651022012871

- `instance_seed`: `7075651022012871`
- `word_count`: `87`
- `body_word_count`: `35`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Which section ranks second when the section totals are ordered from highest to lowest?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible section label requested by the question.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes for the metric cards in the selected section.
Example JSON:
{"annotation":[[108,164,248,258],[398,164,538,258]],"answer":"Program Totals"}
```

### task_pages__infographic__section_ranked_total_label / single / answer_only / sample 7075651022012871

- `instance_seed`: `7075651022012871`
- `word_count`: `56`
- `body_word_count`: `34`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Which section ranks second when the section totals are ordered from highest to lowest?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible section label requested by the question.
Example JSON:
{"answer":"Program Totals"}
```

### task_pages__infographic__section_total_except_named_value / single / answer_and_annotation / sample 8940833545948757

- `instance_seed`: `8940833545948757`
- `word_count`: `79`
- `body_word_count`: `34`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Within section "Dining", skip "Silver" and "Azure" and sum the remaining metric values.
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes for the included metric cards after exclusions.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":[[108,164,248,258],[398,164,538,258]],"answer":64}
```

### task_pages__infographic__section_total_except_named_value / single / answer_only / sample 8940833545948757

- `instance_seed`: `8940833545948757`
- `word_count`: `45`
- `body_word_count`: `41`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Within section "Dining", skip "Silver" and "Azure" and sum the remaining metric values.
Return a JSON object with "answer" only.
Answer field: set "answer" to the requested integer.
Example JSON:
{"answer":64}
```

### task_pages__infographic__section_total_extrema_difference_value / single / answer_and_annotation / sample 77085026798844

- `instance_seed`: `77085026798844`
- `word_count`: `96`
- `body_word_count`: `35`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. What is the difference between the highest section total and the lowest section total?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to an object with keys "highest_total_section" and "lowest_total_section", each mapped to a list of supporting metric card [x0, y0, x1, y1] pixel bounding boxes.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"annotation":{"highest_total_section":[[108,164,248,258],[252,164,392,258]],"lowest_total_section":[[398,164,538,258],[542,164,682,258]]},"answer":64}
```

### task_pages__infographic__section_total_extrema_difference_value / single / answer_only / sample 77085026798844

- `instance_seed`: `77085026798844`
- `word_count`: `47`
- `body_word_count`: `34`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. What is the difference between the highest section total and the lowest section total?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the requested integer.
Example JSON:
{"answer":64}
```

### task_pages__infographic__sum_named_metrics_value / single / answer_and_annotation / sample 3733524850266373

- `instance_seed`: `3733524850266373`
- `word_count`: `83`
- `body_word_count`: `36`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using the cards labeled "Quartz", "Birch", "Summit", "Flint", and "Umber", what is the combined value?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes for the supporting metric cards.
Format for the "answer" field: set "answer" to the requested integer.
Example JSON:
{"annotation":[[108,164,248,258],[398,164,538,258]],"answer":64}
```

### task_pages__infographic__sum_named_metrics_value / single / answer_only / sample 3733524850266373

- `instance_seed`: `3733524850266373`
- `word_count`: `47`
- `body_word_count`: `43`

```text
The image shows a multi-section infographic with labeled metric cards and printed values. Using the cards labeled "Quartz", "Birch", "Summit", "Flint", and "Umber", what is the combined value?
Return a JSON object with "answer" only.
Answer field: set "answer" to the requested integer.
Example JSON:
{"answer":64}
```

### task_pages__instruction_panel__shared_control_for_step_set_label / single / answer_and_annotation / sample 7672964101085635

- `instance_seed`: `7672964101085635`
- `word_count`: `89`
- `body_word_count`: `36`

```text
The figure shows an instruction panel with numbered steps and visible control chips on each step. Which visible control label appears in each of steps 1 and 5?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to a list of [x0, y0, x1, y1] boxes for the matching shared control chips in the referenced steps.
Required answer format: set "answer" to the exact visible control label common to the referenced steps.
Example JSON:
{"annotation":[[236,220,340,250],[236,410,340,440]],"answer":"Sync"}
```

### task_pages__instruction_panel__shared_control_for_step_set_label / single / answer_only / sample 7672964101085635

- `instance_seed`: `7672964101085635`
- `word_count`: `54`
- `body_word_count`: `50`

```text
The figure shows an instruction panel with numbered steps and visible control chips on each step. Which visible control label appears in each of steps 1 and 5?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible control label common to the referenced steps.
Example JSON:
{"answer":"Sync"}
```

### task_pages__instruction_panel__step_for_control_pair_label / single / answer_and_annotation / sample 2224996568275583

- `instance_seed`: `2224996568275583`
- `word_count`: `91`
- `body_word_count`: `37`

```text
The image shows an instruction panel with numbered steps and visible control chips on each step. Which visible step number has both "Search" and "Alert" on the same step?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] boxes for the two matching control chips and their step-number badge.
Answer format: set "answer" to the integer step number containing both referenced control labels.
Example JSON:
{"annotation":[[640,280,750,310],[760,280,870,310],[120,270,152,302]],"answer":4}
```

### task_pages__instruction_panel__step_for_control_pair_label / single / answer_only / sample 2224996568275583

- `instance_seed`: `2224996568275583`
- `word_count`: `57`
- `body_word_count`: `36`

```text
The image shows an instruction panel with numbered steps and visible control chips on each step. Which visible step number has both "Search" and "Alert" on the same step?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the integer step number containing both referenced control labels.
Example JSON:
{"answer":4}
```

### task_pages__map__destination_after_directions_label / single / answer_and_annotation / sample 1707024503580881

- `instance_seed`: `1707024503580881`
- `word_count`: `104`
- `body_word_count`: `49`

```text
The figure shows a printed campus layout with labeled landmarks, named zones, visible walking paths, and a compass. Begin at "Auditorium" and follow these directions one step at a time: north, then west, then north, then west. Which landmark is reached?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible destination landmark label.
Annotation format: set "annotation" to an ordered array of [x0, y0, x1, y1] pixel bounding boxes around the route landmarks from the start through the destination.
Example JSON:
{"annotation":[[188,310,314,368],[426,310,552,368],[426,478,552,536]],"answer":"Clinic"}
```

### task_pages__map__destination_after_directions_label / single / answer_only / sample 1707024503580881

- `instance_seed`: `1707024503580881`
- `word_count`: `66`
- `body_word_count`: `48`

```text
The figure shows a printed campus layout with labeled landmarks, named zones, visible walking paths, and a compass. Begin at "Auditorium" and follow these directions one step at a time: north, then west, then north, then west. Which landmark is reached?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible destination landmark label.
Example JSON:
{"answer":"Clinic"}
```

### task_pages__map__landmark_after_route_step_label / single / answer_and_annotation / sample 741138217825354

- `instance_seed`: `741138217825354`
- `word_count`: `103`
- `body_word_count`: `43`

```text
The figure shows a printed campus layout with labeled landmarks, named zones, visible walking paths, and a highlighted orange route. Using only the orange route, count landmarks after "Depot". What is the 3rd reached landmark?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible landmark label at the requested route step.
Annotation format: set "annotation" to an ordered array of [x0, y0, x1, y1] pixel bounding boxes around the highlighted-route landmarks from the start through the requested landmark.
Example JSON:
{"annotation":[[214,388,340,446],[452,388,578,446],[690,388,816,446]],"answer":"Gallery"}
```

### task_pages__map__landmark_after_route_step_label / single / answer_only / sample 741138217825354

- `instance_seed`: `741138217825354`
- `word_count`: `62`
- `body_word_count`: `42`

```text
The figure shows a printed campus layout with labeled landmarks, named zones, visible walking paths, and a highlighted orange route. Using only the orange route, count landmarks after "Depot". What is the 3rd reached landmark?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible landmark label at the requested route step.
Example JSON:
{"answer":"Gallery"}
```

### task_pages__mixed_infographic_page__module_condition_item_count / single / answer_and_annotation / sample 7955987380349257

- `instance_seed`: `7955987380349257`
- `word_count`: `85`
- `body_word_count`: `41`

```text
The figure shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. How many item values in module "Storage" are above #6 for "Rank"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] pixel bounding boxes around every matching value cell.
Answer format: set "answer" to the integer count of matching items.
Example JSON:
{"annotation":[[5,6,7,8],[6,7,8,9]],"answer":2}
```

### task_pages__mixed_infographic_page__module_condition_item_count / single / answer_only / sample 7955987380349257

- `instance_seed`: `7955987380349257`
- `word_count`: `55`
- `body_word_count`: `40`

```text
The figure shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. How many item values in module "Storage" are above #6 for "Rank"?
Return a JSON object with "answer" only.
Answer format: set "answer" to the integer count of matching items.
Example JSON:
{"answer":2}
```

### task_pages__mixed_infographic_page__module_field_ranked_item_label / single / answer_and_annotation / sample 7425029838719780

- `instance_seed`: `7425029838719780`
- `word_count`: `88`
- `body_word_count`: `45`

```text
The visual shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Using the "Count" field in module "Energy", which item ranks third in lowest to highest order?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to the [x0, y0, x1, y1] pixel bounding box around the answer item label.
Required answer format: set "answer" to the exact visible item label at the requested rank.
Example JSON:
{"annotation":[3,4,5,6],"answer":"Atlas"}
```

### task_pages__mixed_infographic_page__module_field_ranked_item_label / single / answer_only / sample 7425029838719780

- `instance_seed`: `7425029838719780`
- `word_count`: `65`
- `body_word_count`: `44`

```text
The visual shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Using the "Count" field in module "Energy", which item ranks third in lowest to highest order?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible item label at the requested rank.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__mixed_infographic_page__module_field_total_value / single / answer_and_annotation / sample 6476911105733050

- `instance_seed`: `6476911105733050`
- `word_count`: `89`
- `body_word_count`: `40`

```text
The page shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. What is the combined value for field "Score" in module "Stationery"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] pixel bounding boxes around every value cell included in the sum.
Answer format: set "answer" to the requested integer total.
Example JSON:
{"annotation":[[5,6,7,8],[6,7,8,9],[7,8,9,10]],"answer":126}
```

### task_pages__mixed_infographic_page__module_field_total_value / single / answer_only / sample 6476911105733050

- `instance_seed`: `6476911105733050`
- `word_count`: `55`
- `body_word_count`: `39`

```text
The page shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. What is the combined value for field "Score" in module "Stationery"?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the requested integer total.
Example JSON:
{"answer":126}
```

### task_pages__mixed_infographic_page__module_field_value_label / single / answer_and_annotation / sample 4188416142176414

- `instance_seed`: `4188416142176414`
- `word_count`: `80`
- `body_word_count`: `42`

```text
The page shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Read the value where item "Grove" and field "Reach" meet in module "Tools".
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible value string.
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel bounding box around the answer value cell.
Example JSON:
{"annotation":[5,6,7,8],"answer":"42k"}
```

### task_pages__mixed_infographic_page__module_field_value_label / single / answer_only / sample 4188416142176414

- `instance_seed`: `4188416142176414`
- `word_count`: `56`
- `body_word_count`: `41`

```text
The page shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Read the value where item "Grove" and field "Reach" meet in module "Tools".
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible value string.
Example JSON:
{"answer":"42k"}
```

### task_pages__mixed_infographic_page__module_two_field_condition_item_label / single / answer_and_annotation / sample 3443005777984967

- `instance_seed`: `3443005777984967`
- `word_count`: `90`
- `body_word_count`: `44`

```text
The image shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. In module "Tools", which item has "Score" at least 79 and "Window" equal to "Q1"?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to the [x0, y0, x1, y1] pixel bounding box around the answer item label.
Format for the "answer" field: set "answer" to the exact visible item label satisfying both conditions.
Example JSON:
{"annotation":[3,4,5,6],"answer":"Atlas"}
```

### task_pages__mixed_infographic_page__module_two_field_condition_item_label / single / answer_only / sample 3443005777984967

- `instance_seed`: `3443005777984967`
- `word_count`: `61`
- `body_word_count`: `43`

```text
The image shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. In module "Tools", which item has "Score" at least 79 and "Window" equal to "Q1"?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible item label satisfying both conditions.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__mixed_infographic_page__page_field_extremum_module_label / single / answer_and_annotation / sample 8818848054638216

- `instance_seed`: `8818848054638216`
- `word_count`: `80`
- `body_word_count`: `43`

```text
The image shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Using all visible modules with field "Reach", which module title has the lowest value?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel bounding box around the winning module panel.
Answer format: set "answer" to the exact visible module title.
Example JSON:
{"annotation":[2,3,4,5],"answer":"Atlas"}
```

### task_pages__mixed_infographic_page__page_field_extremum_module_label / single / answer_only / sample 8818848054638216

- `instance_seed`: `8818848054638216`
- `word_count`: `56`
- `body_word_count`: `52`

```text
The image shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Using all visible modules with field "Reach", which module title has the lowest value?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible module title.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label / single / answer_and_annotation / sample 331939245773630

- `instance_seed`: `331939245773630`
- `word_count`: `87`
- `body_word_count`: `46`

```text
The visual shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Using the "Count" field, total the listed values in modules "Software" and "Energy". Which module is larger?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel bounding box around the winning module panel.
Answer field: set "answer" to the exact visible module title with the larger total.
Example JSON:
{"annotation":[2,3,4,5],"answer":"Atlas"}
```

### task_pages__mixed_infographic_page__two_module_field_total_comparison_module_label / single / answer_only / sample 331939245773630

- `instance_seed`: `331939245773630`
- `word_count`: `63`
- `body_word_count`: `59`

```text
The visual shows a dense mixed infographic page with titled modules, item labels, field labels, printed values, and native context text. Using the "Count" field, total the listed values in modules "Software" and "Energy". Which module is larger?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible module title with the larger total.
Example JSON:
{"answer":"Atlas"}
```

### task_pages__navigation_flow__navigation_path_target_label / menu_path_target_label / answer_and_annotation / sample 3069679672113861

- `instance_seed`: `3069679672113861`
- `word_count`: `71`
- `body_word_count`: `38`

```text
The image shows a desktop application navigation screen with menu paths and lettered candidate commands. Follow the menu path "Edit > Inspect > Primary > Export". Which candidate letter marks the final command?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to the bounding box of the selected target command.
Required answer format: set "answer" to the selected candidate letter.
Example JSON:
{"annotation":[112,316,286,354],"answer":"G"}
```

### task_pages__navigation_flow__navigation_path_target_label / menu_path_target_label / answer_only / sample 3069679672113861

- `instance_seed`: `3069679672113861`
- `word_count`: `51`
- `body_word_count`: `37`

```text
The image shows a desktop application navigation screen with menu paths and lettered candidate commands. Follow the menu path "Edit > Inspect > Primary > Export". Which candidate letter marks the final command?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the selected candidate letter.
Example JSON:
{"answer":"G"}
```

### task_pages__navigation_flow__navigation_path_target_label / ribbon_group_command_label / answer_and_annotation / sample 3556636109733292

- `instance_seed`: `3556636109733292`
- `word_count`: `68`
- `body_word_count`: `37`

```text
The figure shows a desktop application navigation screen with ribbon tabs, ribbon groups, and lettered candidate commands. Which candidate letter marks "Filter" in the "Review" ribbon tab under "Arrange"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the bounding box of the selected target command.
Answer format: set "answer" to the selected candidate letter.
Example JSON:
{"annotation":[112,316,286,354],"answer":"G"}
```

### task_pages__navigation_flow__navigation_path_target_label / ribbon_group_command_label / answer_only / sample 3556636109733292

- `instance_seed`: `3556636109733292`
- `word_count`: `52`
- `body_word_count`: `36`

```text
The figure shows a desktop application navigation screen with ribbon tabs, ribbon groups, and lettered candidate commands. Which candidate letter marks "Filter" in the "Review" ribbon tab under "Arrange"?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the selected candidate letter.
Example JSON:
{"answer":"G"}
```

### task_pages__navigation_flow__navigation_path_target_label / sidebar_tree_target_label / answer_and_annotation / sample 94511497869345

- `instance_seed`: `94511497869345`
- `word_count`: `75`
- `body_word_count`: `38`

```text
This screen shows a desktop application navigation screen with a sidebar tree and lettered candidate items. For the sidebar path "Settings > Pinned > Timeline", select the letter on the final item.
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to the bounding box of the selected target item.
Format for the "answer" field: set "answer" to the selected candidate letter.
Example JSON:
{"annotation":[112,316,286,354],"answer":"G"}
```

### task_pages__navigation_flow__navigation_path_target_label / sidebar_tree_target_label / answer_only / sample 94511497869345

- `instance_seed`: `94511497869345`
- `word_count`: `51`
- `body_word_count`: `37`

```text
This screen shows a desktop application navigation screen with a sidebar tree and lettered candidate items. For the sidebar path "Settings > Pinned > Timeline", select the letter on the final item.
Return a JSON object with "answer" only.
Required answer format: set "answer" to the selected candidate letter.
Example JSON:
{"answer":"G"}
```

### task_pages__navigation_flow__same_group_target_label / single / answer_and_annotation / sample 8189590501067502

- `instance_seed`: `8189590501067502`
- `word_count`: `66`
- `body_word_count`: `35`

```text
The image shows a desktop application navigation screen with grouped lettered candidate controls. What candidate letter is in the same visible group as candidate "Y", excluding "Y"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the bounding box of the selected target control.
Answer field: set "answer" to the selected candidate letter.
Example JSON:
{"annotation":[112,316,286,354],"answer":"G"}
```

### task_pages__navigation_flow__same_group_target_label / single / answer_only / sample 8189590501067502

- `instance_seed`: `8189590501067502`
- `word_count`: `48`
- `body_word_count`: `34`

```text
The image shows a desktop application navigation screen with grouped lettered candidate controls. What candidate letter is in the same visible group as candidate "Y", excluding "Y"?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the selected candidate letter.
Example JSON:
{"answer":"G"}
```

### task_pages__paired_forms__shortfall_minus_overage_value / single / answer_and_annotation / sample 7630874396360166

- `instance_seed`: `7630874396360166`
- `word_count`: `101`
- `body_word_count`: `45`

```text
This page shows two side-by-side business forms, a purchase order and a receiving slip, with matching item codes and visible quantities. What integer value results from summing purchase-order unit value times ordered-minus-received quantity for every mismatched row?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for the full receiving-slip rows whose received quantity differs from the matching purchase-order quantity.
Required answer format: set "answer" to the computed integer shortfall-minus-overage value.
Example JSON:
{"annotation":[[850,340,1268,378],[850,388,1268,426],[850,436,1268,474]],"answer":324}
```

### task_pages__paired_forms__shortfall_minus_overage_value / single / answer_only / sample 7630874396360166

- `instance_seed`: `7630874396360166`
- `word_count`: `58`
- `body_word_count`: `44`

```text
This page shows two side-by-side business forms, a purchase order and a receiving slip, with matching item codes and visible quantities. What integer value results from summing purchase-order unit value times ordered-minus-received quantity for every mismatched row?
Return a JSON object with "answer" only.
Answer format: set "answer" to the computed integer shortfall-minus-overage value.
Example JSON:
{"answer":324}
```

### task_pages__paired_forms__sum_absolute_quantity_differences_value / single / answer_and_annotation / sample 7787010893722139

- `instance_seed`: `7787010893722139`
- `word_count`: `103`
- `body_word_count`: `45`

```text
The page shows two side-by-side business forms, a purchase order and a receiving slip, with matching item codes and visible quantities. Compare ordered and received quantities row by row, take absolute differences for mismatches, and add them.
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the computed integer sum of absolute quantity differences.
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for the full receiving-slip rows whose received quantity differs from the matching purchase-order quantity.
Example JSON:
{"annotation":[[850,340,1268,378],[850,388,1268,426],[850,436,1268,474]],"answer":42}
```

### task_pages__paired_forms__sum_absolute_quantity_differences_value / single / answer_only / sample 7787010893722139

- `instance_seed`: `7787010893722139`
- `word_count`: `62`
- `body_word_count`: `44`

```text
The page shows two side-by-side business forms, a purchase order and a receiving slip, with matching item codes and visible quantities. Compare ordered and received quantities row by row, take absolute differences for mismatches, and add them.
Return a JSON object with "answer" only.
Final answer format: set "answer" to the computed integer sum of absolute quantity differences.
Example JSON:
{"answer":42}
```

### task_pages__paired_forms__total_amount_delta_value / single / answer_and_annotation / sample 462737615681892

- `instance_seed`: `462737615681892`
- `word_count`: `95`
- `body_word_count`: `40`

```text
This page shows two side-by-side business forms, a purchase order and a receiving slip, with matching item codes and visible quantities. What integer total do you get by summing unit-value-weighted quantity mismatches?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for the full receiving-slip rows whose received quantity differs from the matching purchase-order quantity.
Answer field: set "answer" to the computed integer total amount delta.
Example JSON:
{"annotation":[[850,340,1268,378],[850,388,1268,426],[850,436,1268,474]],"answer":864}
```

### task_pages__paired_forms__total_amount_delta_value / single / answer_only / sample 462737615681892

- `instance_seed`: `462737615681892`
- `word_count`: `57`
- `body_word_count`: `39`

```text
This page shows two side-by-side business forms, a purchase order and a receiving slip, with matching item codes and visible quantities. What integer total do you get by summing unit-value-weighted quantity mismatches?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the computed integer total amount delta.
Example JSON:
{"answer":864}
```

### task_pages__process_flow__condition_path_endpoint_label / single / answer_and_annotation / sample 2040856734394341

- `instance_seed`: `2040856734394341`
- `word_count`: `123`
- `body_word_count`: `51`

```text
The figure shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Begin at "Verify". Follow the decision labels "approve" then "pass"; use unlabeled arrows only to move between decisions. What step label do you land on?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "start_step", "first_decision_label", "second_decision_label", and "endpoint_step", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the exact visible destination step label as a string.
Example JSON:
{"annotation":{"start_step":[126,208,260,270],"first_decision_label":[286,254,340,278],"second_decision_label":[512,412,570,436],"endpoint_step":[630,458,764,520]},"answer":"Publish"}
```

### task_pages__process_flow__condition_path_endpoint_label / single / answer_only / sample 2040856734394341

- `instance_seed`: `2040856734394341`
- `word_count`: `68`
- `body_word_count`: `64`

```text
The figure shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Begin at "Verify". Follow the decision labels "approve" then "pass"; use unlabeled arrows only to move between decisions. What step label do you land on?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible destination step label as a string.
Example JSON:
{"answer":"Publish"}
```

### task_pages__process_flow__filtered_node_count / role_node_count / answer_and_annotation / sample 5427099235638371

- `instance_seed`: `5427099235638371`
- `word_count`: `87`
- `body_word_count`: `37`

```text
This process diagram shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. How many steps match the role filter not process steps?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted step boxes.
Required answer format: set "answer" to the integer count of qualifying step boxes.
Example JSON:
{"annotation":[[168,246,302,308],[340,386,474,448]],"answer":2}
```

### task_pages__process_flow__filtered_node_count / role_node_count / answer_only / sample 5427099235638371

- `instance_seed`: `5427099235638371`
- `word_count`: `53`
- `body_word_count`: `36`

```text
This process diagram shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. How many steps match the role filter not process steps?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of qualifying step boxes.
Example JSON:
{"answer":2}
```

### task_pages__process_flow__filtered_node_count / shape_node_count / answer_and_annotation / sample 42072908062167

- `instance_seed`: `42072908062167`
- `word_count`: `81`
- `body_word_count`: `33`

```text
The image shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Count all steps that are decision diamonds.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted step boxes.
Answer format: set "answer" to the integer count of qualifying step boxes.
Example JSON:
{"annotation":[[168,246,302,308],[340,386,474,448]],"answer":2}
```

### task_pages__process_flow__filtered_node_count / shape_node_count / answer_only / sample 42072908062167

- `instance_seed`: `42072908062167`
- `word_count`: `48`
- `body_word_count`: `32`

```text
The image shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Count all steps that are decision diamonds.
Return a JSON object with "answer" only.
Answer format: set "answer" to the integer count of qualifying step boxes.
Example JSON:
{"answer":2}
```

### task_pages__process_flow__filtered_node_count / status_node_count / answer_and_annotation / sample 2933426952055266

- `instance_seed`: `2933426952055266`
- `word_count`: `91`
- `body_word_count`: `37`

```text
The figure shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Using the status badges, how many steps are not marked Review?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted step boxes.
Format for the "answer" field: set "answer" to the integer count of qualifying step boxes.
Example JSON:
{"annotation":[[168,246,302,308],[340,386,474,448]],"answer":2}
```

### task_pages__process_flow__filtered_node_count / status_node_count / answer_only / sample 2933426952055266

- `instance_seed`: `2933426952055266`
- `word_count`: `52`
- `body_word_count`: `36`

```text
The figure shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Using the status badges, how many steps are not marked Review?
Return a JSON object with "answer" only.
Answer format: set "answer" to the integer count of qualifying step boxes.
Example JSON:
{"answer":2}
```

### task_pages__process_flow__lane_filtered_handoff_count / lane_involved_handoff_count / answer_and_annotation / sample 3514050196501929

- `instance_seed`: `3514050196501929`
- `word_count`: `86`
- `body_word_count`: `38`

```text
The diagram shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Using the lane labels, count arrows between "Billing" and any other lane.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of arrow segments in image pixel coordinates, where each segment is [[x0, y0], [x1, y1]].
Answer field: set "answer" to the integer count of qualifying handoff arrows.
Example JSON:
{"annotation":[[[272,294],[462,348]],[[526,408],[706,462]]],"answer":2}
```

### task_pages__process_flow__lane_filtered_handoff_count / lane_involved_handoff_count / answer_only / sample 3514050196501929

- `instance_seed`: `3514050196501929`
- `word_count`: `54`
- `body_word_count`: `37`

```text
The diagram shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. Using the lane labels, count arrows between "Billing" and any other lane.
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of qualifying handoff arrows.
Example JSON:
{"answer":2}
```

### task_pages__process_flow__lane_filtered_handoff_count / lane_outgoing_handoff_count / answer_and_annotation / sample 5775153438040050

- `instance_seed`: `5775153438040050`
- `word_count`: `85`
- `body_word_count`: `37`

```text
The figure shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. What is the number of cross-lane handoffs that begin in "Eval"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of arrow segments in image pixel coordinates, where each segment is [[x0, y0], [x1, y1]].
Answer field: set "answer" to the integer count of qualifying handoff arrows.
Example JSON:
{"annotation":[[[272,294],[462,348]],[[526,408],[706,462]]],"answer":2}
```

### task_pages__process_flow__lane_filtered_handoff_count / lane_outgoing_handoff_count / answer_only / sample 5775153438040050

- `instance_seed`: `5775153438040050`
- `word_count`: `53`
- `body_word_count`: `36`

```text
The figure shows a labeled process-flow diagram with lane bands, step boxes, status badges, decision labels, and arrows. What is the number of cross-lane handoffs that begin in "Eval"?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the integer count of qualifying handoff arrows.
Example JSON:
{"answer":2}
```

### task_pages__profile_card_grid__field_ranked_profile_label / highest_field_profile_label / answer_and_annotation / sample 7430352643393346

- `instance_seed`: `7430352643393346`
- `word_count`: `77`
- `body_word_count`: `32`

```text
The figure shows a grid of profile cards, each with a visible profile name and labeled fields. Which profile has the highest Hours value?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to the [x0, y0, x1, y1] box around the selected profile card in image pixel coordinates.
Format for the "answer" field: set "answer" to the exact visible profile name.
Example JSON:
{"annotation":[72,142,324,332],"answer":"Aster"}
```

### task_pages__profile_card_grid__field_ranked_profile_label / highest_field_profile_label / answer_only / sample 7430352643393346

- `instance_seed`: `7430352643393346`
- `word_count`: `48`
- `body_word_count`: `31`

```text
The figure shows a grid of profile cards, each with a visible profile name and labeled fields. Which profile has the highest Hours value?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the exact visible profile name.
Example JSON:
{"answer":"Aster"}
```

### task_pages__profile_card_grid__field_ranked_profile_label / lowest_field_profile_label / answer_and_annotation / sample 7762511171284283

- `instance_seed`: `7762511171284283`
- `word_count`: `73`
- `body_word_count`: `34`

```text
The page shows a grid of profile cards, each with a visible profile name and labeled fields. What profile name corresponds to the minimum Score value?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the [x0, y0, x1, y1] box around the selected profile card in image pixel coordinates.
Answer field: set "answer" to the exact visible profile name.
Example JSON:
{"annotation":[72,142,324,332],"answer":"Aster"}
```

### task_pages__profile_card_grid__field_ranked_profile_label / lowest_field_profile_label / answer_only / sample 7762511171284283

- `instance_seed`: `7762511171284283`
- `word_count`: `48`
- `body_word_count`: `33`

```text
The page shows a grid of profile cards, each with a visible profile name and labeled fields. What profile name corresponds to the minimum Score value?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible profile name.
Example JSON:
{"answer":"Aster"}
```

### task_pages__profile_card_grid__field_ranked_profile_label / nth_highest_field_profile_label / answer_and_annotation / sample 2835067881953012

- `instance_seed`: `2835067881953012`
- `word_count`: `77`
- `body_word_count`: `38`

```text
The figure shows a grid of profile cards, each with a visible profile name and labeled fields. Sort the profiles by Hours from highest to lowest. Which profile is third?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the [x0, y0, x1, y1] box around the selected profile card in image pixel coordinates.
Answer field: set "answer" to the exact visible profile name.
Example JSON:
{"annotation":[72,142,324,332],"answer":"Aster"}
```

### task_pages__profile_card_grid__field_ranked_profile_label / nth_highest_field_profile_label / answer_only / sample 2835067881953012

- `instance_seed`: `2835067881953012`
- `word_count`: `52`
- `body_word_count`: `37`

```text
The figure shows a grid of profile cards, each with a visible profile name and labeled fields. Sort the profiles by Hours from highest to lowest. Which profile is third?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible profile name.
Example JSON:
{"answer":"Aster"}
```

### task_pages__profile_card_grid__field_ranked_profile_label / nth_lowest_field_profile_label / answer_and_annotation / sample 6247767060531509

- `instance_seed`: `6247767060531509`
- `word_count`: `76`
- `body_word_count`: `37`

```text
This page shows a grid of profile cards, each with a visible profile name and labeled fields. After ranking by ascending Score, what profile name is in third place?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the [x0, y0, x1, y1] box around the selected profile card in image pixel coordinates.
Answer field: set "answer" to the exact visible profile name.
Example JSON:
{"annotation":[72,142,324,332],"answer":"Aster"}
```

### task_pages__profile_card_grid__field_ranked_profile_label / nth_lowest_field_profile_label / answer_only / sample 6247767060531509

- `instance_seed`: `6247767060531509`
- `word_count`: `50`
- `body_word_count`: `46`

```text
This page shows a grid of profile cards, each with a visible profile name and labeled fields. After ranking by ascending Score, what profile name is in third place?
Return a JSON object with "answer" only.
Answer field: set "answer" to the exact visible profile name.
Example JSON:
{"answer":"Aster"}
```

### task_pages__profile_card_grid__profile_for_field_value / single / answer_and_annotation / sample 6135881588662356

- `instance_seed`: `6135881588662356`
- `word_count`: `72`
- `body_word_count`: `33`

```text
The figure shows a grid of profile cards, each with a visible profile name and labeled fields. Which visible profile card matches Region: "River Bend"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to the [x0, y0, x1, y1] box around the matching profile card in image pixel coordinates.
Answer field: set "answer" to the exact visible profile name.
Example JSON:
{"annotation":[72,142,324,332],"answer":"Aster"}
```

### task_pages__profile_card_grid__profile_for_field_value / single / answer_only / sample 6135881588662356

- `instance_seed`: `6135881588662356`
- `word_count`: `47`
- `body_word_count`: `32`

```text
The figure shows a grid of profile cards, each with a visible profile name and labeled fields. Which visible profile card matches Region: "River Bend"?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible profile name.
Example JSON:
{"answer":"Aster"}
```

### task_pages__profile_card_grid__value_for_named_profile_field / single / answer_and_annotation / sample 8323231853487107

- `instance_seed`: `8323231853487107`
- `word_count`: `75`
- `body_word_count`: `34`

```text
The image shows a grid of profile cards, each with a visible profile name and labeled fields. Which visible value is listed as Signal for "Zaedin"?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the exact visible field value.
Annotation format: set "annotation" to the [x0, y0, x1, y1] box around the target field value in image pixel coordinates.
Example JSON:
{"annotation":[172,212,246,230],"answer":"North Pier"}
```

### task_pages__profile_card_grid__value_for_named_profile_field / single / answer_only / sample 8323231853487107

- `instance_seed`: `8323231853487107`
- `word_count`: `49`
- `body_word_count`: `33`

```text
The image shows a grid of profile cards, each with a visible profile name and labeled fields. Which visible value is listed as Signal for "Zaedin"?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the exact visible field value.
Example JSON:
{"answer":"North Pier"}
```

### task_pages__record_table__enabled_action_for_type_count / single / answer_and_annotation / sample 6572918378753181

- `instance_seed`: `6572918378753181`
- `word_count`: `92`
- `body_word_count`: `30`

```text
The screen shows a sectioned record table in a desktop application. How many rows have Type "Image" and an active "Sync" button?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around every counted row.
Format for the "answer" field: set "answer" to the integer count of rows with the requested type and enabled action.
Example JSON:
{"annotation":[[72,236,1208,264],[72,292,1208,320],[72,404,1208,432]],"answer":3}
```

### task_pages__record_table__enabled_action_for_type_count / single / answer_only / sample 6572918378753181

- `instance_seed`: `6572918378753181`
- `word_count`: `53`
- `body_word_count`: `29`

```text
The screen shows a sectioned record table in a desktop application. How many rows have Type "Image" and an active "Sync" button?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the integer count of rows with the requested type and enabled action.
Example JSON:
{"answer":3}
```

### task_pages__record_table__selected_rows_with_status_count / single / answer_and_annotation / sample 8185012312939468

- `instance_seed`: `8185012312939468`
- `word_count`: `88`
- `body_word_count`: `32`

```text
The figure shows a sectioned record table in a desktop application. What is the number of rows that are selected and have status "Ready"?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around every counted row.
Required answer format: set "answer" to the integer count of selected rows with the requested status.
Example JSON:
{"annotation":[[72,236,1208,264],[72,292,1208,320],[72,404,1208,432]],"answer":3}
```

### task_pages__record_table__selected_rows_with_status_count / single / answer_only / sample 8185012312939468

- `instance_seed`: `8185012312939468`
- `word_count`: `51`
- `body_word_count`: `31`

```text
The figure shows a sectioned record table in a desktop application. What is the number of rows that are selected and have status "Ready"?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of selected rows with the requested status.
Example JSON:
{"answer":3}
```

### task_pages__record_table__value_threshold_in_group_count / single / answer_and_annotation / sample 5296313908776588

- `instance_seed`: `5296313908776588`
- `word_count`: `98`
- `body_word_count`: `32`

```text
The image shows a sectioned record table in a desktop application. In the "Inbox" section, how many rows have Size at least 65 MB?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around every counted row.
Format for the "answer" field: set "answer" to the integer count of rows in the requested section whose Size is at least the threshold.
Example JSON:
{"annotation":[[72,236,1208,264],[72,292,1208,320],[72,404,1208,432]],"answer":3}
```

### task_pages__record_table__value_threshold_in_group_count / single / answer_only / sample 5296313908776588

- `instance_seed`: `5296313908776588`
- `word_count`: `56`
- `body_word_count`: `31`

```text
The image shows a sectioned record table in a desktop application. In the "Inbox" section, how many rows have Size at least 65 MB?
Return a JSON object with "answer" only.
Answer format: set "answer" to the integer count of rows in the requested section whose Size is at least the threshold.
Example JSON:
{"answer":3}
```

### task_pages__schedule__longer_than_reference_count / single / answer_and_annotation / sample 2923675892810759

- `instance_seed`: `2923675892810759`
- `word_count`: `86`
- `body_word_count`: `34`

```text
The visual shows one single-day schedule with time labels and scheduled event blocks. Count the other events whose duration is longer than the highlighted reference event.
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the integer count of events longer than the highlighted reference event.
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for all counted event blocks.
Example JSON:
{"annotation":[[250,240,396,408],[404,430,550,634],[558,352,704,568]],"answer":3}
```

### task_pages__schedule__longer_than_reference_count / single / answer_only / sample 2923675892810759

- `instance_seed`: `2923675892810759`
- `word_count`: `54`
- `body_word_count`: `33`

```text
The visual shows one single-day schedule with time labels and scheduled event blocks. Count the other events whose duration is longer than the highlighted reference event.
Return a JSON object with "answer" only.
Final answer format: set "answer" to the integer count of events longer than the highlighted reference event.
Example JSON:
{"answer":3}
```

### task_pages__schedule__maximum_non_overlapping_count / single / answer_and_annotation / sample 8275108537064682

- `instance_seed`: `8275108537064682`
- `word_count`: `95`
- `body_word_count`: `36`

```text
The image shows one single-day schedule with time labels and scheduled event blocks. What is the maximum number of scheduled events that can be selected without any overlap?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an array of [x0, y0, x1, y1] boxes for the unique maximum-size non-overlapping event set.
Format for the "answer" field: set "answer" to the maximum number of mutually non-overlapping events.
Example JSON:
{"annotation":[[250,220,396,316],[404,316,550,412],[558,412,704,508],[250,508,396,604]],"answer":4}
```

### task_pages__schedule__maximum_non_overlapping_count / single / answer_only / sample 8275108537064682

- `instance_seed`: `8275108537064682`
- `word_count`: `54`
- `body_word_count`: `35`

```text
The image shows one single-day schedule with time labels and scheduled event blocks. What is the maximum number of scheduled events that can be selected without any overlap?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the maximum number of mutually non-overlapping events.
Example JSON:
{"answer":4}
```

### task_pages__schedule__overlap_count / single / answer_and_annotation / sample 8871968217480760

- `instance_seed`: `8871968217480760`
- `word_count`: `80`
- `body_word_count`: `33`

```text
The visual shows one single-day schedule with time labels and scheduled event blocks. How many other event blocks cross the highlighted reference event's time range?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for all counted event blocks.
Answer format: set "answer" to the integer count of events that overlap the highlighted reference event.
Example JSON:
{"annotation":[[250,276,396,366],[404,318,550,438]],"answer":2}
```

### task_pages__schedule__overlap_count / single / answer_only / sample 8871968217480760

- `instance_seed`: `8871968217480760`
- `word_count`: `53`
- `body_word_count`: `32`

```text
The visual shows one single-day schedule with time labels and scheduled event blocks. How many other event blocks cross the highlighted reference event's time range?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of events that overlap the highlighted reference event.
Example JSON:
{"answer":2}
```

### task_pages__schema__field_role_count / all_field_count / answer_and_annotation / sample 1799824730279884

- `instance_seed`: `1799824730279884`
- `word_count`: `87`
- `body_word_count`: `33`

```text
The page shows database tables with field rows, key markers, cardinality markers, and relationship lines. Using the "Member" table, how many field rows are shown?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted field rows.
Required answer format: set "answer" to the integer count of visible field rows in the requested table.
Example JSON:
{"annotation":[[90,120,220,146],[90,150,220,176]],"answer":2}
```

### task_pages__schema__field_role_count / all_field_count / answer_only / sample 1799824730279884

- `instance_seed`: `1799824730279884`
- `word_count`: `53`
- `body_word_count`: `32`

```text
The page shows database tables with field rows, key markers, cardinality markers, and relationship lines. Using the "Member" table, how many field rows are shown?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of visible field rows in the requested table.
Example JSON:
{"answer":2}
```

### task_pages__schema__field_role_count / attribute_field_count / answer_and_annotation / sample 8561776349435347

- `instance_seed`: `8561776349435347`
- `word_count`: `89`
- `body_word_count`: `34`

```text
The page shows database tables with field rows, key markers, cardinality markers, and relationship lines. How many fields in "Order" have no PK or FK marker?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around the counted field rows.
Answer format: set "answer" to the integer count of visible non-PK and non-FK field rows in the requested table.
Example JSON:
{"annotation":[[90,150,220,176],[90,180,220,206]],"answer":2}
```

### task_pages__schema__field_role_count / attribute_field_count / answer_only / sample 8561776349435347

- `instance_seed`: `8561776349435347`
- `word_count`: `59`
- `body_word_count`: `33`

```text
The page shows database tables with field rows, key markers, cardinality markers, and relationship lines. How many fields in "Order" have no PK or FK marker?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the integer count of visible non-PK and non-FK field rows in the requested table.
Example JSON:
{"answer":2}
```

### task_pages__schema__join_path_length_value / single / answer_and_annotation / sample 2610934651459491

- `instance_seed`: `2610934651459491`
- `word_count`: `98`
- `body_word_count`: `37`

```text
The visual shows database tables with field rows, key markers, cardinality markers, and relationship lines. What is the fewest number of relationship lines needed to connect "Session" to "Newsletter"?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to a JSON array of line segments; each segment is [[x0, y0], [x1, y1]] for one relationship line on the shortest path.
Required answer format: set "answer" to the integer number of relationship lines on the shortest path between the two requested tables.
Example JSON:
{"annotation":[[[150,180],[330,260]],[[330,260],[520,260]]],"answer":2}
```

### task_pages__schema__join_path_length_value / single / answer_only / sample 2610934651459491

- `instance_seed`: `2610934651459491`
- `word_count`: `61`
- `body_word_count`: `36`

```text
The visual shows database tables with field rows, key markers, cardinality markers, and relationship lines. What is the fewest number of relationship lines needed to connect "Session" to "Newsletter"?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the integer number of relationship lines on the shortest path between the two requested tables.
Example JSON:
{"answer":2}
```

### task_pages__schema__relationship_cardinality_label / single / answer_and_annotation / sample 4569881063514862

- `instance_seed`: `4569881063514862`
- `word_count`: `92`
- `body_word_count`: `34`

```text
The diagram shows database tables with field rows, key markers, cardinality markers, and relationship lines. For the relationship connecting "Payment" and "Order", identify the cardinality class.
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "source_cardinality_marker" and "target_cardinality_marker", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to one of "one_to_one", "one_to_many", "optional_many", or "many_to_many".
Example JSON:
{"annotation":{"source_cardinality_marker":[270,202,300,226],"target_cardinality_marker":[440,202,470,226]},"answer":"one_to_many"}
```

### task_pages__schema__relationship_cardinality_label / single / answer_only / sample 4569881063514862

- `instance_seed`: `4569881063514862`
- `word_count`: `50`
- `body_word_count`: `33`

```text
The diagram shows database tables with field rows, key markers, cardinality markers, and relationship lines. For the relationship connecting "Payment" and "Order", identify the cardinality class.
Return a JSON object with "answer" only.
Final answer format: set "answer" to one of "one_to_one", "one_to_many", "optional_many", or "many_to_many".
Example JSON:
{"answer":"one_to_many"}
```

### task_pages__schema__relationship_count / single / answer_and_annotation / sample 6006861893484107

- `instance_seed`: `6006861893484107`
- `word_count`: `87`
- `body_word_count`: `31`

```text
The image shows database tables with field rows, key markers, cardinality markers, and relationship lines. Across the schema, count every relationship line once.
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a JSON array of line segments; each segment is [[x0, y0], [x1, y1]] using the endpoints of one counted relationship line.
Format for the "answer" field: set "answer" to the integer count of relationship lines.
Example JSON:
{"annotation":[[[150,180],[330,260]],[[420,260],[610,360]]],"answer":2}
```

### task_pages__schema__relationship_count / single / answer_only / sample 6006861893484107

- `instance_seed`: `6006861893484107`
- `word_count`: `46`
- `body_word_count`: `30`

```text
The image shows database tables with field rows, key markers, cardinality markers, and relationship lines. Across the schema, count every relationship line once.
Return a JSON object with "answer" only.
Required answer format: set "answer" to the integer count of relationship lines.
Example JSON:
{"answer":2}
```

### task_pages__schema__relationship_endpoint_label / single / answer_and_annotation / sample 556215497562325

- `instance_seed`: `556215497562325`
- `word_count`: `74`
- `body_word_count`: `34`

```text
The page shows database tables with field rows, key markers, cardinality markers, and relationship lines. Starting at "Speaker", what table does the "represents" relationship connect to?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a [x0, y0, x1, y1] box in image pixel coordinates around the target table.
Answer field: set "answer" to the exact target table label as shown.
Example JSON:
{"annotation":[480,150,650,330],"answer":"Order"}
```

### task_pages__schema__relationship_endpoint_label / single / answer_only / sample 556215497562325

- `instance_seed`: `556215497562325`
- `word_count`: `50`
- `body_word_count`: `33`

```text
The page shows database tables with field rows, key markers, cardinality markers, and relationship lines. Starting at "Speaker", what table does the "represents" relationship connect to?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact target table label as shown.
Example JSON:
{"answer":"Order"}
```

### task_pages__sectioned_infographic__section_filtered_item_label / single / answer_and_annotation / sample 6779600865583875

- `instance_seed`: `6779600865583875`
- `word_count`: `73`
- `body_word_count`: `33`

```text
The page shows a sectioned infographic with named sections and short visible item rows. Using section "Beverage", read the item label with the pin marker.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] box around the matching item row.
Answer format: set "answer" to the exact visible item label requested by the question.
Example JSON:
{"annotation":[20,80,180,104],"answer":"Check lights"}
```

### task_pages__sectioned_infographic__section_filtered_item_label / single / answer_only / sample 6779600865583875

- `instance_seed`: `6779600865583875`
- `word_count`: `52`
- `body_word_count`: `32`

```text
The page shows a sectioned infographic with named sections and short visible item rows. Using section "Beverage", read the item label with the pin marker.
Return a JSON object with "answer" only.
Required answer format: set "answer" to the exact visible item label requested by the question.
Example JSON:
{"answer":"Check lights"}
```

### task_pages__sectioned_infographic__section_item_count / single / answer_and_annotation / sample 7061328486748907

- `instance_seed`: `7061328486748907`
- `word_count`: `83`
- `body_word_count`: `33`

```text
The figure shows a sectioned infographic with named sections and short visible item rows. What is the number of visible listed items in section "Music"?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an array of [x0, y0, x1, y1] boxes for the visible item rows in the requested section.
Format for the "answer" field: set "answer" to the requested integer count.
Example JSON:
{"annotation":[[20,80,180,104],[20,110,180,134]],"answer":2}
```

### task_pages__sectioned_infographic__section_item_count / single / answer_only / sample 7061328486748907

- `instance_seed`: `7061328486748907`
- `word_count`: `46`
- `body_word_count`: `32`

```text
The figure shows a sectioned infographic with named sections and short visible item rows. What is the number of visible listed items in section "Music"?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the requested integer count.
Example JSON:
{"answer":2}
```

### task_pages__step_list__nth_step_field_label / nth_step_detail / answer_and_annotation / sample 5064722914604194

- `instance_seed`: `5064722914604194`
- `word_count`: `82`
- `body_word_count`: `34`

```text
This page shows a numbered step list with a title and detail line on each step card. What detail text is shown in the first step?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to one [x0, y0, x1, y1] box around the requested step detail text.
Format for the "answer" field: set "answer" to the exact visible step detail text requested by the question.
Example JSON:
{"annotation":[220,250,370,278],"answer":"Review packet"}
```

### task_pages__step_list__nth_step_field_label / nth_step_detail / answer_only / sample 5064722914604194

- `instance_seed`: `5064722914604194`
- `word_count`: `54`
- `body_word_count`: `33`

```text
This page shows a numbered step list with a title and detail line on each step card. What detail text is shown in the first step?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the exact visible step detail text requested by the question.
Example JSON:
{"answer":"Review packet"}
```

### task_pages__step_list__nth_step_field_label / nth_step_title / answer_and_annotation / sample 8661800493667904

- `instance_seed`: `8661800493667904`
- `word_count`: `73`
- `body_word_count`: `32`

```text
The figure shows a numbered step list with a title and detail line on each step card. Which title appears on the final step?
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box around the requested step title.
Required answer format: set "answer" to the exact visible step title requested by the question.
Example JSON:
{"annotation":[220,216,340,244],"answer":"Review"}
```

### task_pages__step_list__nth_step_field_label / nth_step_title / answer_only / sample 8661800493667904

- `instance_seed`: `8661800493667904`
- `word_count`: `49`
- `body_word_count`: `31`

```text
The figure shows a numbered step list with a title and detail line on each step card. Which title appears on the final step?
Return a JSON object with "answer" only.
Answer format: set "answer" to the exact visible step title requested by the question.
Example JSON:
{"answer":"Review"}
```

### task_pages__step_list__step_after_named_step_label / single / answer_and_annotation / sample 7660925228700622

- `instance_seed`: `7660925228700622`
- `word_count`: `79`
- `body_word_count`: `34`

```text
The figure shows a numbered step list with a title and detail line on each step card. Read the title on the step immediately following "Perceptron".
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box around the answer step title.
Required answer format: set "answer" to the exact visible title of the step immediately after the named source step.
Example JSON:
{"annotation":[220,216,300,244],"answer":"Approve"}
```

### task_pages__step_list__step_after_named_step_label / single / answer_only / sample 7660925228700622

- `instance_seed`: `7660925228700622`
- `word_count`: `55`
- `body_word_count`: `33`

```text
The figure shows a numbered step list with a title and detail line on each step card. Read the title on the step immediately following "Perceptron".
Return a JSON object with "answer" only.
Answer format: set "answer" to the exact visible title of the step immediately after the named source step.
Example JSON:
{"answer":"Approve"}
```

### task_pages__step_list__step_for_detail_label / step_number_for_detail / answer_and_annotation / sample 3486729897776573

- `instance_seed`: `3486729897776573`
- `word_count`: `76`
- `body_word_count`: `39`

```text
The figure shows a numbered step list with a title and detail line on each step card. What is the step number for the card whose detail line reads "Volume watch"?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] box around the answer step number badge.
Answer format: set "answer" to the step number as visible text.
Example JSON:
{"annotation":[164,208,206,250],"answer":"3"}
```

### task_pages__step_list__step_for_detail_label / step_number_for_detail / answer_only / sample 3486729897776573

- `instance_seed`: `3486729897776573`
- `word_count`: `56`
- `body_word_count`: `38`

```text
The figure shows a numbered step list with a title and detail line on each step card. What is the step number for the card whose detail line reads "Volume watch"?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the step number as visible text.
Example JSON:
{"answer":"3"}
```

### task_pages__step_list__step_for_detail_label / step_title_for_detail / answer_and_annotation / sample 7760395783289751

- `instance_seed`: `7760395783289751`
- `word_count`: `85`
- `body_word_count`: `37`

```text
The figure shows a numbered step list with a title and detail line on each step card. Find the detail "Note M47". What title is shown on that step?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to one [x0, y0, x1, y1] box around the answer step title.
Format for the "answer" field: set "answer" to the exact visible title of the step containing the named detail text.
Example JSON:
{"annotation":[220,216,340,244],"answer":"Review"}
```

### task_pages__step_list__step_for_detail_label / step_title_for_detail / answer_only / sample 7760395783289751

- `instance_seed`: `7760395783289751`
- `word_count`: `57`
- `body_word_count`: `36`

```text
The figure shows a numbered step list with a title and detail line on each step card. Find the detail "Note M47". What title is shown on that step?
Return a JSON object with "answer" only.
Answer format: set "answer" to the exact visible title of the step containing the named detail text.
Example JSON:
{"answer":"Review"}
```

### task_pages__timeline__event_date_gap_value / single / answer_and_annotation / sample 7025830844825715

- `instance_seed`: `7025830844825715`
- `word_count`: `97`
- `body_word_count`: `33`

```text
The timeline shows one labeled milestone timeline with dated event cards and highlighted reference events. How many days apart are event F and event B?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "earlier_event" and "later_event", each mapped to the [x0, y0, x1, y1] box of that endpoint event card.
Format for the "answer" field: set "answer" to the nonnegative integer number of calendar days between the two named events.
Example JSON:
{"annotation":{"earlier_event":[160,158,264,228],"later_event":[538,158,642,228]},"answer":9}
```

### task_pages__timeline__event_date_gap_value / single / answer_only / sample 7025830844825715

- `instance_seed`: `7025830844825715`
- `word_count`: `54`
- `body_word_count`: `32`

```text
The timeline shows one labeled milestone timeline with dated event cards and highlighted reference events. How many days apart are event F and event B?
Return a JSON object with "answer" only.
Required answer format: set "answer" to the nonnegative integer number of calendar days between the two named events.
Example JSON:
{"answer":9}
```

### task_pages__timeline__interval_membership_count / between_reference_events_count / answer_and_annotation / sample 3876121225642767

- `instance_seed`: `3876121225642767`
- `word_count`: `83`
- `body_word_count`: `34`

```text
The figure shows one labeled milestone timeline with dated event cards and highlighted reference events. How many events are strictly between the two highlighted reference events?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the integer count of events strictly between the two highlighted reference events.
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for all counted event cards.
Example JSON:
{"annotation":[[412,410,516,480],[538,158,642,228]],"answer":2}
```

### task_pages__timeline__interval_membership_count / between_reference_events_count / answer_only / sample 3876121225642767

- `instance_seed`: `3876121225642767`
- `word_count`: `54`
- `body_word_count`: `33`

```text
The figure shows one labeled milestone timeline with dated event cards and highlighted reference events. How many events are strictly between the two highlighted reference events?
Return a JSON object with "answer" only.
Answer format: set "answer" to the integer count of events strictly between the two highlighted reference events.
Example JSON:
{"answer":2}
```

### task_pages__timeline__interval_membership_count / outside_reference_interval_count / answer_and_annotation / sample 4133692295286465

- `instance_seed`: `4133692295286465`
- `word_count`: `84`
- `body_word_count`: `35`

```text
The image shows one labeled milestone timeline with dated event cards and highlighted reference events. Count the events outside the highlighted reference interval, excluding the highlighted events.
Return a JSON object with "annotation" and "answer".
Required annotation format: set "annotation" to an array of [x0, y0, x1, y1] boxes for all counted event cards.
Required answer format: set "answer" to the integer count of events in the two outer timeline ranges.
Example JSON:
{"annotation":[[160,158,264,228],[790,410,894,480]],"answer":2}
```

### task_pages__timeline__interval_membership_count / outside_reference_interval_count / answer_only / sample 4133692295286465

- `instance_seed`: `4133692295286465`
- `word_count`: `54`
- `body_word_count`: `34`

```text
The image shows one labeled milestone timeline with dated event cards and highlighted reference events. Count the events outside the highlighted reference interval, excluding the highlighted events.
Return a JSON object with "answer" only.
Answer format: set "answer" to the integer count of events in the two outer timeline ranges.
Example JSON:
{"answer":2}
```

### task_pages__web_action__action_target_label / click_target_label / answer_and_annotation / sample 5385102067759693

- `instance_seed`: `5385102067759693`
- `word_count`: `109`
- `body_word_count`: `59`

```text
The figure shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Instruction: For the item with category "Creative" and status "Reserved", use guide code "X6" from the Action Guide. Which labeled web control matches the guide code and page context?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to one [x0, y0, x1, y1] pixel box around the target button and its candidate label marker.
Format for the "answer" field: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"annotation":[410,378,584,442],"answer":"G"}
```

### task_pages__web_action__action_target_label / click_target_label / answer_only / sample 5385102067759693

- `instance_seed`: `5385102067759693`
- `word_count`: `77`
- `body_word_count`: `58`

```text
The figure shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Instruction: For the item with category "Creative" and status "Reserved", use guide code "X6" from the Action Guide. Which labeled web control matches the guide code and page context?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"answer":"G"}
```

### task_pages__web_action__action_target_label / select_option_label / answer_and_annotation / sample 3637705091930165

- `instance_seed`: `3637705091930165`
- `word_count`: `96`
- `body_word_count`: `52`

```text
This screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Find the option implied by this guide-code instruction: Choose the option for "Alert channel" with guide code "T4". Which label is shown?
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel box around the target option and its candidate label marker.
Answer format: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"annotation":[410,378,584,442],"answer":"G"}
```

### task_pages__web_action__action_target_label / select_option_label / answer_only / sample 3637705091930165

- `instance_seed`: `3637705091930165`
- `word_count`: `72`
- `body_word_count`: `51`

```text
This screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Find the option implied by this guide-code instruction: Choose the option for "Alert channel" with guide code "T4". Which label is shown?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"answer":"G"}
```

### task_pages__web_action__action_target_label / type_field_label / answer_and_annotation / sample 4781215898792142

- `instance_seed`: `4781215898792142`
- `word_count`: `91`
- `body_word_count`: `46`

```text
The screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Instruction: Enter text for "Delivery" using guide code "X6". Which candidate label marks the target input?
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the selected candidate label as a single capital letter.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel box around the target input and its candidate label marker.
Example JSON:
{"annotation":[410,378,584,442],"answer":"G"}
```

### task_pages__web_action__action_target_label / type_field_label / answer_only / sample 4781215898792142

- `instance_seed`: `4781215898792142`
- `word_count`: `64`
- `body_word_count`: `45`

```text
The screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Instruction: Enter text for "Delivery" using guide code "X6". Which candidate label marks the target input?
Return a JSON object with "answer" only.
Final answer format: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"answer":"G"}
```

### task_pages__web_action__guide_code_target_count / click_guide_code_target_count / answer_and_annotation / sample 7551843831494709

- `instance_seed`: `7551843831494709`
- `word_count`: `92`
- `body_word_count`: `39`

```text
The image shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Count all visible candidate controls using guide code "T4".
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the number of matching candidate controls.
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] pixel boxes around every candidate control that matches the requested guide code.
Example JSON:
{"annotation":[[410,378,584,442],[410,452,584,516],[410,526,584,590]],"answer":3}
```

### task_pages__web_action__guide_code_target_count / click_guide_code_target_count / answer_only / sample 7551843831494709

- `instance_seed`: `7551843831494709`
- `word_count`: `53`
- `body_word_count`: `49`

```text
The image shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Count all visible candidate controls using guide code "T4".
Return a JSON object with "answer" only.
Answer field: set "answer" to the number of matching candidate controls.
Example JSON:
{"answer":3}
```

### task_pages__web_action__guide_code_target_count / select_option_guide_code_target_count / answer_and_annotation / sample 52789204760715

- `instance_seed`: `52789204760715`
- `word_count`: `92`
- `body_word_count`: `40`

```text
This screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Count the candidate option controls marked with guide code "X6".
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] pixel boxes around every candidate option that matches the requested guide code.
Answer field: set "answer" to the number of matching candidate options.
Example JSON:
{"annotation":[[410,378,584,442],[410,452,584,516],[410,526,584,590]],"answer":3}
```

### task_pages__web_action__guide_code_target_count / select_option_guide_code_target_count / answer_only / sample 52789204760715

- `instance_seed`: `52789204760715`
- `word_count`: `54`
- `body_word_count`: `39`

```text
This screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Count the candidate option controls marked with guide code "X6".
Return a JSON object with "answer" only.
Answer format: set "answer" to the number of matching candidate options.
Example JSON:
{"answer":3}
```

### task_pages__web_action__guide_code_target_count / type_field_guide_code_target_count / answer_and_annotation / sample 8348102215549040

- `instance_seed`: `8348102215549040`
- `word_count`: `92`
- `body_word_count`: `40`

```text
The screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Count the candidate input fields marked with guide code "K1".
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to an array of [x0, y0, x1, y1] pixel boxes around every candidate input that matches the requested guide code.
Answer field: set "answer" to the number of matching candidate inputs.
Example JSON:
{"annotation":[[410,378,584,442],[410,452,584,516],[410,526,584,590]],"answer":3}
```

### task_pages__web_action__guide_code_target_count / type_field_guide_code_target_count / answer_only / sample 8348102215549040

- `instance_seed`: `8348102215549040`
- `word_count`: `55`
- `body_word_count`: `39`

```text
The screen shows a browser page with an action instruction banner, a visible guide-code table, and candidate markers on targetable web controls. Count the candidate input fields marked with guide code "K1".
Return a JSON object with "answer" only.
Final answer format: set "answer" to the number of matching candidate inputs.
Example JSON:
{"answer":3}
```

### task_pages__workspace__context_control_count / single / answer_and_annotation / sample 3889218866778905

- `instance_seed`: `3889218866778905`
- `word_count`: `91`
- `body_word_count`: `35`

```text
The screen shows a professional application workspace with a shuffled guide, context rows, coded headers, and labeled controls. Count the gray-disabled controls in the "Display" context row.
Return a JSON object with "annotation" and "answer".
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] boxes around the counted controls; use an empty list if none match.
Answer format: set "answer" to the integer count of controls in the named row with the requested visible state.
Example JSON:
{"annotation":[[410,378,560,418],[580,378,730,418]],"answer":2}
```

### task_pages__workspace__context_control_count / single / answer_only / sample 3889218866778905

- `instance_seed`: `3889218866778905`
- `word_count`: `58`
- `body_word_count`: `34`

```text
The screen shows a professional application workspace with a shuffled guide, context rows, coded headers, and labeled controls. Count the gray-disabled controls in the "Display" context row.
Return a JSON object with "answer" only.
Final answer format: set "answer" to the integer count of controls in the named row with the requested visible state.
Example JSON:
{"answer":2}
```

### task_pages__workspace__control_label / single / answer_and_annotation / sample 6566443435970051

- `instance_seed`: `6566443435970051`
- `word_count`: `98`
- `body_word_count`: `49`

```text
The figure shows a professional application workspace with a shuffled guide, context rows, coded headers, and labeled controls. Find the row and coded column implied by this instruction: Select the labeled control for "show item" in "Data".. Which label is shown?
Return a JSON object with "annotation" and "answer".
Format for the "annotation" field: set "annotation" to the [x0, y0, x1, y1] box around the target labeled control in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"annotation":[520,360,690,444],"answer":"G"}
```

### task_pages__workspace__control_label / single / answer_only / sample 6566443435970051

- `instance_seed`: `6566443435970051`
- `word_count`: `69`
- `body_word_count`: `48`

```text
The figure shows a professional application workspace with a shuffled guide, context rows, coded headers, and labeled controls. Find the row and coded column implied by this instruction: Select the labeled control for "show item" in "Data".. Which label is shown?
Return a JSON object with "answer" only.
Format for the "answer" field: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"answer":"G"}
```

### task_pages__workspace__dual_guide_control_label / single / answer_and_annotation / sample 3774171551208737

- `instance_seed`: `3774171551208737`
- `word_count`: `91`
- `body_word_count`: `47`

```text
This screen shows a professional application workspace with a shuffled guide, context rows, coded headers, and labeled controls. Choose the candidate label for the control described by this dual-guide instruction: Resolve context cue "Q1" and action cue "pick file".
Return a JSON object with "annotation" and "answer".
Final answer format: set "answer" to the selected candidate label as a single capital letter.
Annotation format: set "annotation" to the [x0, y0, x1, y1] box around the target labeled control in image pixel coordinates.
Example JSON:
{"annotation":[520,360,690,444],"answer":"G"}
```

### task_pages__workspace__dual_guide_control_label / single / answer_only / sample 3774171551208737

- `instance_seed`: `3774171551208737`
- `word_count`: `64`
- `body_word_count`: `46`

```text
This screen shows a professional application workspace with a shuffled guide, context rows, coded headers, and labeled controls. Choose the candidate label for the control described by this dual-guide instruction: Resolve context cue "Q1" and action cue "pick file".
Return a JSON object with "answer" only.
Answer format: set "answer" to the selected candidate label as a single capital letter.
Example JSON:
{"answer":"G"}
```

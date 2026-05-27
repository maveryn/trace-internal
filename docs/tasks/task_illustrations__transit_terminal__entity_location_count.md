# task_illustrations__transit_terminal__entity_location_count

Status: accepted branch merge; replaces the previous transit terminal person,
luggage, and queue counting public tasks.

## Identity
- domain: `illustrations`
- scene_id: `transit_terminal`
- task_group: `counting`
- task: `terminal_entity_location_count`
- module: `trace/tasks/illustrations/counting/terminal_entity_location_count.py`
- prompt bundle: `prompts/illustrations/counting/illustrations_counting_v0.json`

## Scene And Query
The task renders a synthetic transit terminal with labeled boarding areas,
service points, people, loose luggage, and terminal decor.

Public query variants:

- `boarding_area_a_person_count`
- `boarding_area_b_person_count`
- `boarding_area_c_person_count`
- `boarding_area_d_person_count`
- `suitcase_in_boarding_area_count`
- `backpack_in_boarding_area_count`
- `luggage_cart_in_boarding_area_count`
- `security_queue_person_count`
- `ticket_counter_queue_person_count`
- `gate_queue_person_count`

## Answer Contract
- `answer_gt.type = integer`
- value is the count requested by the selected `query_id`

## Evidence Contract
- `evidence_gt.type = bbox_set`
- person queries return one bbox around each counted person
- luggage queries return one bbox around each counted luggage item

## Trace Contract
- `query_spec.task_id` is this merged public task id.
- `query_spec.branch_id` records the private branch generator used for the
  selected query.
- `query_spec.params.merged_query_probabilities` records public query
  sampling support.
- Branch-specific render maps and witness fields are preserved.

## Prompt Contract
- `scene_key = transit_terminal_canvas`
- `query_key` is the selected query variant
- branch-specific task keys from `illustrations_counting_v0` are reused

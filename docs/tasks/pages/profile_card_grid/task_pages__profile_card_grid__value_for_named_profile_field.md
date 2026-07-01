# `task_pages__profile_card_grid__value_for_named_profile_field`

## Identity
1. Domain: `pages`
2. Scene id: `profile_card_grid`
3. Source scene: `profile_card_grid`
4. Task id: `task_pages__profile_card_grid__value_for_named_profile_field`

## Contract
1. Objective: read the visible value of a named field from a named profile card.
2. Public task contract: `value_for_named_profile_field`
3. Supported `query_id` values: `single`
4. Answer type: `string`
5. Annotation schema: `bbox`
6. Annotation witness: scalar box around the target field value; profile-name and field-label boxes stay in trace metadata.
7. Query argument axes: target profile name, target field label, target field value, card count, and scene variant.

## Program Contract
- `profile_card_grid_value_for_named_profile_field(profile_name, field_label); output=field_value_string; annotation=bbox(target_field_value); scene=profile_card_grid; scope=one profile-card grid page`

## Prompt + Trace
1. Prompt bundle: `pages_profile_card_grid_v1`
2. Scene key: `profile_card_grid`
3. Task key: `profile_attribute_lookup_query`
4. Prompt query key: `value_for_named_profile_field`
5. Runtime `query_id` is `single`; semantic branch identity is recorded as `prompt_query_key`.
6. Trace records visible profile cards, field labels/values, target profile payload, final text boxes, layout metadata, and prompt metadata.
7. Generation is deterministic from `instance_seed`; answer and annotation come from the finalized render metadata.

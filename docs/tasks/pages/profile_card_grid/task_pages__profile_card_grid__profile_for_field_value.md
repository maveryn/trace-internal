# `task_pages__profile_card_grid__profile_for_field_value`

## Identity
1. Domain: `pages`
2. Scene id: `profile_card_grid`
3. Source scene: `profile_card_grid`
4. Task id: `task_pages__profile_card_grid__profile_for_field_value`

## Contract
1. Objective: identify the profile name whose visible field has a requested value.
2. Public task contract: `profile_for_field_value`
3. Supported `query_id` values: `single`
4. Answer type: `string`
5. Annotation schema: `bbox`
6. Annotation witness: scalar box around the matched profile card; profile-name, field-label, and field-value boxes stay in trace metadata.
7. Query argument axes: target field label, target field value, target profile card, card count, and scene variant.

## Program Contract
- `profile_card_grid_profile_for_field_value(field_label, field_value); output=profile_name_string; annotation=bbox(matched_profile_card); scene=profile_card_grid; scope=one profile-card grid page`

## Prompt + Trace
1. Prompt bundle: `pages_profile_card_grid_v1`
2. Scene key: `profile_card_grid`
3. Task key: `profile_attribute_lookup_query`
4. Prompt query key: `profile_for_field_value`
5. Runtime `query_id` is `single`; semantic branch identity is recorded as `prompt_query_key`.
6. Trace records visible profile cards, field labels/values, target profile payload, final text boxes, layout metadata, and prompt metadata.
7. Generation is deterministic from `instance_seed`; answer and annotation come from the finalized render metadata.

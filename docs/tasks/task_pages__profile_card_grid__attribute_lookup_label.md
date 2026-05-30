# `task_pages__profile_card_grid__attribute_lookup_label`

## Taxonomy
1. Domain: `pages`
2. Scene id: `profile_card_grid`
3. Task id: `task_pages__profile_card_grid__attribute_lookup_label`
4. Implementation group: `pages/document_lookup`

## Contract
Reads or reverse-lookups one labeled field in a grid of profile cards.

Query ids: `value_for_named_profile_field|profile_for_field_value`.

Answers are exact visible strings: either the requested field value or the profile name whose field matches the requested value. Evidence is a `keyed_bbox_map` over the matched card row:
- `profile_name`: the target card's profile-name text,
- `field_label`: the queried field-label text,
- `field_value`: the target field-value text.

## Prompt + Trace
1. Prompt bundle: `pages_document_lookup_v0`
2. Scene key: `profile_card_grid`
3. Task key: `profile_attribute_lookup_query`
4. Trace records profile ids, names, field labels/values, target field, answer value, card bboxes, name bboxes, field-label bboxes, and field-value bboxes.

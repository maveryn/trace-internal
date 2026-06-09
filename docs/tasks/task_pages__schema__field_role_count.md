# task_pages__schema__field_role_count

## Identity
- domain: `pages`
- scene_id: `schema`
- task_group: `schema`

## Contract
Counts field rows in a named database-schema table. Query branches count either all field rows or only ordinary attribute rows that are not marked `PK` or `FK`.

Annotation is a `bbox_set` over the counted field rows.

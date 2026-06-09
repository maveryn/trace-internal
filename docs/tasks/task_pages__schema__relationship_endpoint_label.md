# `task_pages__schema__relationship_endpoint_label`

## Identity
1. Domain: `pages`
2. Scene id: `schema`
3. Source task group: `schema`
4. Task id: `task_pages__schema__relationship_endpoint_label`

## Contract
1. Objective: given a named source table and a visible relationship label in a rendered database schema, return the table label at the other end of that relationship.
2. Branch metadata: `query_id`
3. `query_id`: `target_table_for_relationship_label`
4. Answer type: `string`
5. Annotation type: `keyed_bbox_map` over the source table, relationship-label badge, and target table.
6. Annotation keys: `source_table`, `relationship_label`, and `target_table`.

## Prompt + Trace
1. Prompt bundle: `pages_schema_v0`
2. Scene key: `database_schema_diagram`
3. Task key: `relationship_endpoint_label_query`
4. Trace records the sampled schema context, layout/style variants, selected relationship id, source table id, target table id, relationship label, overlap score, and keyed annotation boxes.
5. Generation is deterministic from `instance_seed`; answers and annotation come from finalized table placement and relationship-label geometry.

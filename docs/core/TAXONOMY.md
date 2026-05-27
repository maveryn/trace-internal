# TRACE Public Taxonomy

TRACE public metadata uses:

`domain -> scene_id -> task_id`

## Public Fields
1. `domain` is the broad public domain used for balancing and reporting.
2. `scene_id` is the visual rendering grammar for the instance.
3. `task_id` is the sampling unit.
4. `query_id` is optional diagnostic metadata for the query id inside one
   task. Use **query id** as the human-facing term and `query_id` as the
   canonical field. Do not use `task_variant` for this concept.

`task_group` remains an implementation/config grouping field for module layout,
prompt bundles, and domain config defaults. It is not a public taxonomy level.

## Trace Metadata Shape
Sidecar traces store taxonomy metadata under `trace_payload["taxonomy"]`.
The public flat keys are:

- `domain`
- `scene_id`
- `task_id`
- `query_id`

Routing metadata lives in explicit nested blocks:

1. `taxonomy.public`
   - `domain`, `scene_id`, `task_id`, and optional `query_id`.
   - This is the public dataset taxonomy and reporting surface.
2. `taxonomy.registered`
   - `task_id`, `domain`, and `task_group` for the registered wrapper task
     class that produced the instance.
   - This is runtime registry metadata, not public taxonomy.
3. `taxonomy.source`
   - `implementation_task_id`, `implementation_domain`,
     `implementation_task_group`.
   - `config_domain`, `config_task_group`.
   - `prompt_domain`, `prompt_task_group`.
   - This records the internal implementation/config/prompt surfaces used by
     wrappers or shared generators.

Do not infer source/config/prompt routing from `taxonomy.public`. A public task
may be backed by a wrapper, a shared implementation task, or a prompt bundle in a
different implementation group.

## Active Domains
The active public domains are:
1. `charts`
2. `games`
3. `geometry`
4. `graph`
5. `icons`
6. `illustrations`
7. `pages`
8. `physics`
9. `puzzles`
10. `three_d`

## Scene Rule
A scene is a visually distinct rendering grammar. Tasks under one scene can
share a parameterized renderer and visual evidence contract.

Two tasks can share solver/helper code and even the same `scene_id` without being
the same public task. For enumeration, apply the hard task boundary in
`docs/core/TASK_UNIT_POLICY.md`: scene grammar, primary witness kind, visual
search pattern, and algorithmic/objective family. Same scene, answer type, or
evidence type is not sufficient to merge tasks if the witness kind, visual
search, or algorithmic objective differs.

## Sampling Rule
Equal task-level sampling remains the default. `query_id` values are diagnostics
for query ids inside a task, not separate public sampling units.
`query_id` is an internal replay selector, not a public sampling unit.

## Implementation Layer
The active taxonomy mapping lives in `trace/core/taxonomy.py`. Build,
validation, RLVR export, and task-review tools should resolve public taxonomy
through that module instead of parsing task ids.

`TaxonomyEntry.source_domain` and `TaxonomyEntry.source_task_group` describe
current implementation/config routing. Trace consumers should prefer
`taxonomy.registered` and `taxonomy.source` when they need to distinguish public
identity from registry/config/prompt routing.

# TRACE Public Taxonomy

TRACE public metadata uses:

```text
domain -> scene_id -> task_id
```

## 1) Public Fields
1. `domain` is the broad reporting and balancing domain.
2. `scene_id` is the visible rendering grammar: board, chart, diagram, page,
   instrument, object scene, or other stable visual scaffold.
3. `task_id` is the public sampling unit and uses taxonomy-v0 form:
   `task_<domain>__<scene_id>__<objective_contract>`.
4. `query_id` is internal task metadata for replay, branch diagnostics, and
   review breakdowns inside one task contract. It is not a public taxonomy
   level and not a sampling unit.

Do not maintain active domain or task lists in this file. The generated public
inventory lives in `docs/ACTIVE_TASK_INVENTORY.md`.

## 2) Scene And Task Identity
The public task is the pair:

```text
scene contract + objective contract
```

The scene contract defines the visual grammar, object vocabulary, layout family,
non-semantic style support, and any stable query-facing scaffold.

The objective contract defines the answer schema, annotation schema, and concrete
program schema. The detailed boundary rules live in
`docs/core/TASK_UNIT_POLICY.md`.

## 3) Implementation Routing
Public taxonomy is not source layout.

Target scene-package layout is:

```text
trace/tasks/<domain>/<scene_id>/<objective_contract>.py
trace/tasks/<domain>/<scene_id>/shared/
configs/domains/<domain>/<scene_id>.yaml
prompts/<domain>/<scene_id>/<bundle_id>.json
```

Legacy source routing fields, including `scene_id`, may remain in older code,
configs, prompt assets, or trace `taxonomy.source` metadata until their scene is
migrated. They are not public taxonomy nodes. New review-candidate migrated
scenes must not depend on scene routing.

## 4) Trace Metadata Shape
Sidecar traces store taxonomy metadata under `trace_payload["taxonomy"]`.

Public fields:
- `domain`
- `scene_id`
- `task_id`
- optional `query_id`

Routing/debug fields should live under explicit nested blocks such as
`taxonomy.registered` and `taxonomy.source`. Trace consumers must not infer
implementation paths, config files, or prompt bundles from public task ids.

## 5) Sampling Rule
Equal task-level sampling is the default. Domain and scene probabilities are
derived by aggregating active public tasks unless a build config explicitly says
otherwise.

Query sampling happens inside the selected task. Query ids should be uniform by
default and should not have config-level weights in review-candidate migrated
scenes.

## 6) Source Of Truth
The active taxonomy mapping lives in `trace/core/taxonomy.py`. Build,
validation, RLVR export, review tooling, and docs checks should resolve public
taxonomy through that module instead of parsing task ids by string.

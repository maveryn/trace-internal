# Taxonomy Review Checklist

Use this checklist during scene-package migration before generating task-review
artifacts. This is a migration gate, not optional commentary.

## Goal

The migrated scene must lock the public task boundary and internal query
meaning. The task code, prompt assets, taxonomy metadata, program code, and
review artifacts must describe the same contract.

## Public Task Contract

A public task is stable only when these stay fixed across all generated
instances and query ids:

- scene id and rendered scene grammar
- answer schema
- annotation schema, including the semantic role of keyed annotation entries
- concrete reasoning program schema
- prompt scaffold and output JSON shape

If any item changes, split the task unless the change is a narrow query
parameter explicitly allowed below.

## Program Code

Program code must describe the actual reasoning skeleton over the scene state.
It is not a task name, a prose summary, or a generic placeholder.

Use `docs/contracts/PROGRAM_SCHEMA_CATALOG.md` for the shared program-schema
vocabulary. Reuse the closest existing schema unless the task genuinely needs a
new reasoning skeleton.

Current taxonomy sources of truth are:

- rules: `docs/contracts/TAXONOMY.md`,
  `docs/contracts/TASK_UNIT_POLICY.md`,
  `docs/contracts/PROGRAM_SCHEMA_CATALOG.md`, and this checklist;
- active public mapping: `trace/core/taxonomy.py`, registered task modules,
  current configs, prompt assets, and task docs;
- scene review state:
  `review/task-reviews/<domain>/<scene_id>/taxonomy_review_status.json`,
  `review/task-reviews/<domain>/<scene_id>/migration_test_status.json`, browser
  issue threads, and human checklist state.

Historical taxonomy audit exports are not migration source of truth. Do not use
old generated audit packages unless a durable rule has been revalidated against
current code and moved into current docs.

Good program code names:

- the candidate set
- the measured value or attribute
- filters or predicates
- rank, aggregate, comparison, arithmetic, or selection operation
- output binding

Allowed argument values must be explicit in taxonomy metadata. Do not leave
placeholder values such as `direction`, `metric`, or `predicate` when the task
has a known finite support such as `above|below` or `largest|smallest`.

## Query IDs

A `query_id` is a semantic branch of the same public task. It must change the
user-facing task operation, not merely the sampled value used to instantiate the
same operation.

Use a query id only when the branch changes at least one of:

- prompt predicate or operator wording, such as above vs below or largest vs
  smallest
- requested output role, such as source vs target, row vs column, or x vs y
- a visible reference role that remains unresolved in the prompt, such as
  "first endpoint" vs "last endpoint"
- operation applied, such as sum vs mean or absolute vs signed difference, when
  the approved task contract intentionally keeps that as one task
- annotation role semantics, while preserving the same annotation schema

Valid query ids include narrow mirrors such as:

- `above_threshold` vs `below_threshold`
- `largest` vs `smallest`
- `first_endpoint` vs `last_endpoint`, only when the prompt names that role
- `sum` vs `mean` only if the approved task contract intentionally treats the
  aggregate operator as one finite argument

Do not promote an argument value to `query_id` just because it has finite
support. If code resolves the argument to a concrete label, object, category,
number, or option before prompt rendering, and the prompt asks the same
operation over that concrete value, it is generation metadata unless it changes
the prompt scaffold or operation.

Do not use query ids for generation-only variation or resolved slot values:

- style, palette, font, layout, panel count, or renderer preset
- random object/category/label values
- sampled numeric thresholds or target values
- random source-content variants
- internal sampling axes that do not change prompt meaning or program schema
- endpoint side, source side, or target side when the prompt shows only the
  resolved label/value rather than the role name

Record those as scene/render/generation metadata instead.

Examples:

- If a prompt says `Compare the callout mark with "Orchid"`, then whether
  `"Orchid"` was sampled from the first endpoint or last endpoint is not a
  query id. Record `endpoint_side=first|last` in trace metadata.
- If a prompt says `Compare the callout mark with the first endpoint` vs
  `Compare the callout mark with the last endpoint`, then first/last can be
  query ids because the role itself is user-facing.
- If a prompt says `How many marks are above 50?` vs `How many marks are below
  50?`, above/below are valid query ids because the predicate changes.
- If a prompt says `How many red icons are present?`, the sampled color is not
  a query id. It is a target attribute value. If another branch asks `How many
  red circles are present?`, that may require a separate task if the program
  changes from single-attribute count to multi-attribute conjunction count.
- If a chart scene renders as line, bar, or lollipop while the task prompt and
  operation are unchanged, chart type is a scene/render variant, not a query id.

Split the public task if a branch changes:

- answer schema
- annotation schema or annotation role meaning
- prompt/output scaffold
- candidate set type
- reasoning program skeleton
- visual contract enough that the task asks over a different rendered setup

Every supported query id must map to a concrete tuple of program arguments. No
orphan query ids, hidden mirrors, or query names that duplicate renderer
variation are allowed.

## Agent Pre-Review Checklist

Before generating task reviews for a migrated scene, the agent must verify:

- every active task id has a written task contract
- every task has concrete program code and explicit allowed argument values
- every query id is a user-facing semantic branch under this checklist
- non-semantic query ids were moved to trace metadata or removed
- tasks were split, merged, or deleted where the contract requires it
- prompt assets match the task/query semantics
- answer and annotation are bound from the same execution trace
- taxonomy metadata shown in the review app matches the source behavior
- every task/query branch was smoke-generated

After verification, write:

```text
review/task-reviews/<domain>/<scene_id>/taxonomy_review_status.json
```

Use this minimal shape:

```json
{
  "schema": "trace_scene_taxonomy_review_status_v1",
  "domain": "charts",
  "scene_id": "example_scene",
  "passed": true,
  "status": "passed",
  "summary": "taxonomy contract audit passed",
  "checked_at": "2026-06-13T00:00:00+00:00",
  "checked_by": "agent",
  "task_ids": [
    "task_charts__example_scene__objective_contract"
  ],
  "checklist": {
    "task_contracts_stable": true,
    "program_codes_concrete": true,
    "query_ids_semantic": true,
    "prompt_taxonomy_aligned": true,
    "annotation_contracts_stable": true,
    "all_query_branches_smoked": true
  },
  "notes": ""
}
```

Do not write a passing status file unless the checklist actually passed.

Do not use stale generated taxonomy audit packages as migration source of
truth.

## Human Reviewer Gate

The browser task audit panel has a `Taxonomy review` checkbox. The human
reviewer checks it only after the visible taxonomy summary, task/query boundary,
program code, prompts, answer schema, and annotation schema are acceptable.

Task review is not done until all non-solve gates pass:

- Prompt
- Image
- Annotation
- Distribution
- Code review
- Taxonomy review

Solve-rate review remains a separate gate. Existing task rows that were
previously marked review-done must be treated as pending until taxonomy review
is checked.

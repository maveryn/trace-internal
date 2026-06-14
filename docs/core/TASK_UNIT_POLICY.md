# TRACE Task-Unit Policy

This document defines what counts as one public TRACE task.

Use it when proposing tasks, deciding whether a branch is a `query_id` or a new
task id, and auditing split/merge decisions under uniform task-level sampling.

## 1) Core Rule
A public task must have one stable:

```text
scene contract + objective contract
```

The objective contract has three required parts:

1. **Answer schema** — prompt-facing answer type and shape, such as integer
   count, numeric value, option letter, string label, reduced fraction, or list.
2. **Annotation schema** — prompt-facing annotation type and semantic witness
   structure, such as unordered points, ordered path points, object bboxes, or
   keyed role-bound witnesses.
3. **Program schema** — the concrete reasoning skeleton over the scene. It must
   name the candidate set, operand roles, intermediate computation, final
   operator, output binding, and annotation witness roles.

Use `docs/core/PROGRAM_SCHEMA_CATALOG.md` for reusable program-schema names and
do-not-merge boundaries. The catalog normalizes terminology; it does not merge
public tasks by itself.

Same scene, answer type, or annotation type is not enough to merge tasks. Merge
only when all three objective-contract fields and the query-facing visual
scaffold remain stable.

## 2) Program Schema Requirement
Do not approve vague program descriptions such as:

```text
count(objects where predicate)
select_by_rank(items, metric, rank)
compute(value)
filter(items, condition)
```

Those are useful draft labels, but final task decisions need concrete schemas,
for example:

- count legal destination cells for one marked piece under the shown move rule;
- select the option board equal to applying the shown move to the source board;
- count visible objects in a named row that satisfy one color predicate;
- compute a formula-derived unknown from marked operand labels.

If the hidden intermediate objects differ, split the task unless the difference
is only a bounded parameter of the same concrete schema.

## 3) Query IDs
Use **query id** in prose and `query_id` as the metadata field.

A query id is allowed only for narrow parameter branches inside one objective
contract:

1. mirrored directions such as left/right, above/below, X/O, red/blue;
2. bounded rank or threshold parameters over the same candidate set;
3. target attributes over the same visible witness family;
4. operand variations that keep the same answer schema, annotation schema,
   program schema, and query-facing scaffold.

A query id must not choose between public objectives. If changing `query_id`
changes the answer schema, annotation schema, concrete program schema, semantic
witness roles, or visible task scaffold, split the public task.

Every review-candidate task should declare `supported_query_ids`. Tasks with
no internal branches use `("default",)`.

## 4) Public Task Selection
`task_id` is the public selector. Callers should request:

```text
task_games__2048__merge_count
```

not a broad task plus `params["query_id"]` to select the objective.

Public task files resolve and validate `query_id`, then pass semantic arguments
into shared helpers. Scene shared code must not branch on public task ids or
query ids.

## 5) When To Split
Create a new task when a branch changes any of these:

1. answer shape or type;
2. annotation type or semantic witness roles;
3. reasoning program or intermediate object set;
4. unit of visual attention, such as nodes vs edges, rows vs cells, or pieces vs
   destinations;
5. query-facing scaffold, such as board-only vs source-plus-option-panels;
6. final output binding, such as selecting an object vs counting all qualifying
   objects.

Common split signals:

- unordered subset counting vs ordered sequence/path reasoning;
- one-bound predicate count vs two-bound interval count;
- choosing a move vs computing the resulting state;
- reading a value vs comparing/ranking multiple values;
- marking answer options instead of marking the visual witnesses used to decide.

## 6) What May Vary Inside One Task
The following do not by themselves require a new task:

1. non-semantic style, palette, font, noise, and layout variation;
2. object counts, labels, names, colors, values, and placements;
3. mirrored directions or players over the same rule;
4. local arithmetic difficulty over the same operand roles;
5. answer range, board size, or item count when the program schema stays fixed;
6. model difficulty.

Difficulty is not taxonomy. A hard and easy branch can stay one task if the
scene and objective contracts are genuinely the same.

## 7) Annotation Boundary
Annotation should mark minimal visual witnesses, not answer labels unless the
task is a true visual option-image task.

Prefer keyed annotation types when roles matter or an unordered set would be
ambiguous. Use unordered sets for homogeneous counting witnesses where
cardinality is the answer or role identity does not matter.

Answer and annotation must come from the same execution trace.

## 8) Migration Policy
Retired public ids should be deleted, not kept as compatibility tasks.
Review-candidate migrated scenes should not use legacy routing, config
query weights, retired difficulty gates, or task-review artifacts as source
contracts. Use the scene-package migration workflow for source-layout changes.

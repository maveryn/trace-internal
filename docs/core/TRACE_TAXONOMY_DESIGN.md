# TRACE Taxonomy Design

This document defines the canonical taxonomy model for TRACE task review,
existing-task refactors, and future task authoring. If another workflow,
domain, skill, or review note conflicts with this file, use this file and then
update the stale reference.

This is a design target for auditing and refactoring; it does not imply that
every active task already has complete taxonomy metadata.

## Goal

TRACE needs task units that are more principled than arbitrary task-id strings,
but not so granular that every parameter value becomes a separate task.

The taxonomy must support:

1. deciding whether parameterized query branches belong inside one public task
   or should split;
2. browsing tasks by visual scene and public task during review, with optional
   reasoning tags for filtering;
3. deriving public task ids from task definition instead of treating task ids
   as the taxonomy itself;
4. keeping global task sampling meaningful by ensuring one public task is one
   stable reasoning contract.

## Canonical Taxonomy Rule

An accepted public task must be one stable pair:

```text
scene_contract + task_contract
```

The task contract is exactly:

```text
answer_schema + annotation_schema + concrete program_schema
```

The program schema must name the actual candidate set, operand roles, derived
computation, and final operation. Generic placeholders are allowed only as
draft taxonomy notes during review; they are not acceptable final contracts.

Examples of draft-only placeholders:

```text
select_by_rank(items, metric, rank)
count(objects where predicate)
compute(value)
filter(items, condition)
```

These are too broad when they hide the real operation. Replace them with a
concrete skeleton before approving a taxonomy decision.

## Public Ids Are Not The Taxonomy

Public task ids are lookup/generation identifiers. They currently use:

```text
task_<domain>__<scene_id>__<task_slug>
```

The public id should be derived from the task contract, not used as proof that
the contract is valid.

The visible taxonomy should be:

```text
domain
  scene_id
    task_slug
```

Definitions:

- `domain`: broad TRACE domain, such as `charts`, `games`, `geometry`, or
  `puzzles` or `misc`.
- `scene_id`: visual grammar / renderer family. Scene matters because the same
  reasoning can appear under visually distinct grammars.
- `task_slug`: short taxonomy slug for the public sampling unit. It should not
  repeat domain/scene words. Example: `median_rank_difference`, not
  `task_charts__boxplot__median_rank_difference_value`.

Optional `review_tags` may be used for search, dashboards, or audit notes, but
they are descriptive only. They are not part of task identity and must not be
used to merge or split tasks.

`query_id` is an implementation key for generation, review folders, solve-rate
breakdowns, or replay. It is not a visible taxonomy node. In the target design,
query ids should be mechanically derived from the task contract and concrete
query parameters when a stable key is needed.

One current `query_id` may still contain multiple task contracts. When the
generated execution trace exposes a branch that changes the concrete program
schema, split by that trace metadata even if the legacy query id is unchanged.
For example, a chart query id named `ranked_ratio_extremum` is not sufficient
if some samples compute a series share and others compute a pairwise ratio; the
review row must split into separate task contracts.

## Scene Contract And Task Contract

TRACE separates the visual input axis from the reasoning/output axis.

```text
public task = scene_contract + task_contract
```

### Scene Contract

The scene contract is the rendered input contract. It defines what kind of
image is shown and what visible grammar the task may reason over.

It includes:

1. `domain`;
2. `scene_id`;
3. renderer grammar and visible object vocabulary;
4. supported nonsemantic style/layout variation;
5. a stable query-facing `view_contract` when the same scene renderer can show
   different scaffolds.

Examples:

- one chart with labeled marks;
- two coordinated charts;
- board only;
- board with candidate option panels;
- source panel plus edited/result panel;
- reference object plus candidate gallery.

`domain + scene_id` is the public renderer/image axis. Two tasks from different
scenes should not be merged into one public task just because their reasoning
program looks similar; the visual grammar is part of what TRACE samples and
evaluates.

`view_contract` is a stability invariant inside the scene contract. It is not a
separate visible taxonomy layer, but one public task must not mix materially
different query-facing views. If a branch needs a different scaffold, split the
task or refine the scene.

### Derived-Composition Scenes

A public scene may be a derived-composition scene when the rendered input is a
new visual scaffold built from source-scene content. In that case, the source
scene is recorded as content metadata, not as the public scene identity.

This is valid only when the task program depends on the derived scaffold and
not on source-scene semantic rules. For example, visual reconstruction,
missing-patch selection, rotated-tile detection, and piece-order recovery may
use source images from richer scenes while keeping a public scene such as
`image_cutout_board` or `missing_patch`.

Do not use this exception for tasks whose answer requires running the source
scene's semantic verifier or source-specific task program. Those should either
live inside the relevant source scene or be redesigned as explicit
scene-specific multi-panel tasks.

### Task Contract

The task contract is the reasoning and answering contract over a fixed scene
contract. It has exactly three required parts:

1. `answer_schema`
2. `annotation_schema`
3. `program_schema`

Everything else is parameterization or optional review metadata.

Example:

```yaml
public_task_id: task_charts__boxplot__median_rank_difference_value
scene_contract:
  domain: charts
  scene_id: boxplot
  view_contract: single_boxplot_panel
task_slug: median_rank_difference_value
task_contract:
  answer_schema: integer_value
  annotation_schema: keyed_point_map selected_category_label -> chart_mark_center
  program_schema: difference(value(rank_select(boxplots, statistic=median, rank_a)), value(rank_select(boxplots, statistic=median, rank_b)))
parameter_axes:
  statistic: [median]
  rank_a: [top]
  rank_b: [bottom, second, third]
valid_constraints:
  - rank_a != rank_b
```

## Controlled Schema Vocabulary

Use a small shared vocabulary for common schemas during taxonomy analysis.
Add a new schema name only when the existing name would hide a meaningful
contract difference.

Common answer schemas:

- `integer_count`
- `integer_value`
- `decimal_value_1dp`
- `string_label`
- `option_letter`
- `boolean_label`
- `reduced_fraction`
- `list_of_labels`

Common annotation schemas:

- `bbox_set`
- `bbox_sequence`
- `point_set`
- `point_sequence`
- `point_pair_set`
- `keyed_bbox_map`
- `keyed_bbox_set_map`
- `keyed_point_map`
- `keyed_point_set_map`

Schema names describe the public answer/annotation contract, not task internals.
For example, a keyed annotation map may use data-bound visible labels as keys,
but the schema name should still be `keyed_point_map` or `keyed_bbox_map`
unless the reward contract itself changes.

### `answer_schema`

`answer_schema` is the prompt-facing answer type and shape, such as:

- integer count;
- numeric value rounded to one decimal;
- string label;
- option letter;
- reduced fraction string.

If the answer schema changes, split.

### `annotation_schema`

`annotation_schema` is the structure and semantic meaning of the annotation, not
literal data-bound key strings.

Allowed within one task:

```json
{"Orchid":[312,180],"Maple":[540,286]}
```

and:

```json
{"A":[312,180],"D":[540,286]}
```

if both mean:

```text
keyed_point_map selected_category_label -> chart_mark_center
```

Not allowed within one task:

```text
keyed_bbox_map query_node -> node_box, answer_node -> node_box
```

mixed with:

```text
keyed_bbox_map input_node_a -> node_box, input_node_b -> node_box, answer_node -> node_box
```

The literal node labels may vary, but the semantic witness structure changed
from one input plus one answer to two inputs plus one answer. That requires a
task split.

### `program_schema`

`program_schema` is a human-readable query-program skeleton over the scene
grammar. It is not required to be executable code. It should be concise review
metadata that explains why query branches are grouped or split.

Good program schemas are neither one-word objectives nor literal
implementation traces. They describe the reasoning objects the model must
construct before answering.

An accepted program schema must explicitly include:

1. `candidate_set`: what visible units are being considered;
2. `operand_roles`: which visible fields, objects, labels, marks, or states
   are read;
3. `derived_computation`: any intermediate value, set, path, formula result,
   rule result, or counterfactual state needed before answering;
4. `final_operator`: count, select, rank, aggregate, compare, optimize,
   classify, transform, or lookup;
5. `output_binding`: how the computed result maps to the answer schema;
6. `annotation_role_template`: the semantic witness structure required by the
   prompt-facing annotation schema.

If any of these differ across branches, split unless the difference is a
bounded parameter inside the same skeleton.

`program_arguments_json` is separate review metadata for the allowed values and
semantic roles inside that skeleton, such as `direction=[highest, lowest]`,
`rank=[second, third]`, or `mode=[absolute_difference]`. It helps reviewers
understand in-task variants, but it is not a hard task-boundary field. If the
program skeleton changes, update `program_schema`; if only bounded argument
support changes, update `program_arguments_json`.

Reusable base signatures may be used to compare rows, but they are not the
final contract by themselves. The accepted row-level contract is the concrete
program schema plus the scene/scope binding and the answer/annotation schemas.
Two rows may share a reusable signature such as `count(filter(...))` while
still requiring separate public tasks because the concrete candidate set,
operand roles, intermediate computation, or annotation witness template differs.

### Concrete Program Contract Requirement

The taxonomy audit may generate inferred rows while a domain is still being
reviewed. Inferred/generic rows are review scaffolding only. A task is not
taxonomy-accepted until its `program_schema` is concrete enough that a reviewer
can tell whether a new query branch is:

- the same program with different arguments; or
- a different program that needs a new task.

Do not approve rows whose only differentiator is a vague argument such as
`metric`, `condition`, `items`, `source`, `target`, `operation`, or `rule`.
Those words may appear as argument names only after the concrete formula or
selector they stand for is named.

Bad:

```text
select_by_rank(items, metric, rank)
```

Good:

```text
label(select_by_rank(categories,
  abs(value(series_a, category) - value(series_b, category)),
  rank,
  order))
```

Bad:

```text
count(objects where predicate)
```

Good:

```text
count(select(cells, scope) where color(cell) == target_color)
```

Good:

```text
count(groups where count(items in group where shape == target_shape) >= threshold)
```

The first count is a scoped object selector. The second is a group-level count
over per-group member counts. They should not share one task contract even if
both answer with an integer count and both use bbox annotation.

### Summary Statistic And Aggregate Modes

For chart/table-style numeric summaries, `sum`, `mean`, `median`, and clear
synonyms such as user-facing `average` are parameter values of one task when
they are the only difference over the same selected support.

Good single-task pattern:

```text
summary_statistic(values(selected_support), statistic)
```

where:

```yaml
statistic: [sum, mean, median]
```

Split when the support-construction stage changes. For example, an unfiltered
table-column summary and a filtered-row table-column summary are different
program schemas because the latter first constructs a row subset:

```text
summary_statistic(values(numeric_column), statistic)
summary_statistic(values(filter(rows, condition), numeric_column), statistic)
```

Use canonical taxonomy argument name `statistic` for these modes. Generated
prompt wording may still say `average`, but taxonomy metadata should normalize
that value to `mean`.

For a domain that has completed taxonomy review, the audit output should not
contain generic contracts or generic argument notes for that domain. The
expected state is:

- every finalized row has a concrete `program_schema`;
- every finalized row has curated `program_arguments_json`;
- every finalized row uses concrete argument names and values, not placeholders
  such as `query_status`, `query_parameters`, `query_selection_rule`,
  `ranked_position`, `sampled_rank_position`, or `sampled_scene_values`;
- every finalized task with multiple query rows has explicit parameter axes
  such as `move_filter`, `rank_position`, `delta_mode`, or
  `target_clear_count`; broad axes like `sampled_scene_values` or
  `manual_override` are draft-only for finalized chart/game/geometry rows;
- no finalized row relies on broad placeholders like `items`, `metric`, or
  `predicate` without defining the visible candidate set and operand roles;
- metadata-derived splits are represented as separate proposed task ids, not as
  hidden cases under one row.

## Atomic Program Schema Rule

Program schemas can be written at different depths. TRACE uses this principle:

```text
Program schema should be the shallowest skeleton that preserves the required
intermediate reasoning objects.
```

Equivalently, a program schema becomes a new task unit at the first semantic
transformation that changes what the model must construct before answering.

Useful intermediate reasoning objects include:

- selected object set;
- scoped object set;
- relation-filtered object set;
- Boolean selector set;
- per-group counts;
- edited/counterfactual scene state;
- path, reachable set, or traversal order;
- ranked list;
- aggregate value;
- formula-derived unknown;
- game-rule legal move set;
- geometry/physics construction implied by a formula.

Changing a parameter inside one intermediate object usually stays inside a
task. Adding, removing, or reordering intermediate objects usually creates a
different task.

Do not make schemas too shallow:

```text
count(objects where predicate)
```

is usually too broad if it hides direct object selection, Boolean attribute
binding, relation filtering, group-level counting, or counterfactual edits.

Do not make schemas too deep:

```text
count(red circles)
count(blue squares)
```

are usually parameter bindings under the same `multi_attribute_and_count`
schema, not separate task units. By contrast, `red circles`, `red OR circles`,
and `red but not circles` use different Boolean operators and should split
under the shared counting rule below.

A useful review test is:

```text
Can every branch be described by one short program skeleton, with differences
only in named parameters?
```

If yes, keep one task. If the explanation becomes "sometimes first compute X,
sometimes first compute Y", the task is probably too broad.

## Query-Axis Rule

Query axes are bounded parameters inside one concrete program schema. They are
not a second taxonomy layer.

Usually safe query axes:

- mirror direction: highest vs lowest, before vs after, left vs right;
- rank position: first, second, third;
- one-bound comparator direction: above vs below, greater than vs less than;
- sampled visible role identity: target color, object type, series label,
  player color, named row, named column;
- simple subset filter over one stable candidate set: all legal moves vs
  legal moves with a bounded property such as capture, corner destination, or
  highlighted candidate scope;
- unknown slot inside one formula schema;
- game side/player when the same legal-rule program is used;
- rendering variant when the scene contract and task contract stay unchanged.

Usually split:

- difference vs ratio;
- pair ratio vs share of a category total;
- one-bound predicate vs interval/two-bound predicate;
- direct count vs count after edit/counterfactual state;
- direct object count vs group-of-objects predicate count;
- select by rank vs compute the ranked value;
- path existence/reachability vs shortest path vs longest path;
- legal move set vs result state after applying a move;
- same answer/annotation type but different annotation role template.

If adding a query axis requires changing the prompt-facing annotation role
template, the branch is probably a separate task.

### Highlighted Geometry And Panel Selection

For coordinate-plane and function-panel tasks, a highlighted or shaded visual
scaffold is not automatically a split trigger. Keep one task when all branches
share the same answer/annotation schema and the same short program skeleton, and
the branch only changes a bounded rule-family parameter.

Examples that stay together:

- selecting the point inside a shaded coordinate region, with
  `region_rule_family` covering circle, annulus, half-plane intersection, or
  strip regions;
- selecting the candidate panel whose shaded region matches a visible condition
  box, with `region_rule_family` as the query axis;
- selecting a function panel by intersection condition, with
  `primitive_pair_type` and `intersection_condition` as query axes;
- selecting positive vs negative sign-interval panels, with `sign_direction` as
  the query axis.

Split when the branch changes the hidden construction or formula program, not
just the visible rule-family parameter. For example, point reflection,
translation, and rotation are separate transformed-point tasks because they use
different transformation programs. Horizontal vs vertical reflection remains
one reflected-point task because it only changes `reflection_axis`.

## Split Rule

Parameterized branches may stay under one public task only when they share the
same scene contract and the same task contract.

Within a fixed `domain + scene_id`, the task contract fields are:

1. same `answer_schema`;
2. same `annotation_schema`;
3. same `program_schema`.

The scene contract must also remain stable. In particular, one task must not
mix different `view_contract`s. If a branch needs a different query-facing
visual scaffold, split the task or refine the scene.

Split when the task contract changes, or when the scene contract/view contract
is no longer stable.

Common split triggers:

- one chart vs two coordinated charts;
- board-only view vs board-with-options view;
- integer count vs label answer;
- one answer witness vs all counted witnesses;
- one input plus answer vs two inputs plus answer;
- threshold predicate vs interval predicate;
- direct aggregation vs filter rows then aggregate;
- direct object count vs group-of-objects count;
- static scene count vs count after hypothetical edits;
- shortest path vs longest path;
- local relation lookup vs multi-node ancestor/path reasoning;
- different formula schema in geometry or physics.

Parameter changes that usually stay inside one task:

- target object/type/color/material;
- direction mirror;
- rank order or rank position;
- comparator direction for the same predicate arity;
- formula unknown slot for the same formula schema;
- game player color;
- game move/destination filter when candidates, rule generation, answer
  schema, and annotation schema remain stable;
- traversal visit order when the traversal family and contract are stable;
- relation value when the same input/output/annotation schema remains valid.

## Shared Counting Rule

Counting tasks should be grouped by count-program structure, not by domain
object vocabulary.

Inside one fixed scene, changing the counted object type, color, size,
orientation, material, icon id, 3D object class, illustration object class, or
target answer value normally changes only query parameters.

Useful shared count-program schemas:

| Program Schema | Typical Examples |
| --- | --- |
| `entity_count` | Count all visible units in a stable candidate set. |
| `single_attribute_membership_count` | Count circles, red objects, chairs, visible 3D cubes, or objects whose one attribute is in `{red, blue}`. |
| `multi_attribute_and_count` | Count red circles or large red chairs. Two or more conjunctive attribute predicates remain one family. |
| `multi_attribute_or_count` | Count objects that are red OR circles, where the predicates come from multiple attribute axes and overlapping objects count once. |
| `multi_attribute_xor_count` | Count objects satisfying exactly one of two or more attribute predicates. |
| `multi_attribute_exclusion_count` | Count objects satisfying one attribute predicate but not another, such as red but not circle. |
| `multi_attribute_complement_count` | Count objects satisfying none of the listed attribute predicates, such as neither red nor circle. |
| `scoped_attribute_count` | Count books in a shelf section, icons in a row, objects in a zone, or items on one shelf level. |
| `relation_attribute_count` | Count objects left of a reference, closer than a reference, connected to a node, or inside/on/under a prop. |
| `group_predicate_count` | Count rows with at least three stars, columns with no circles, or groups whose member count meets a threshold. |
| `reference_attribute_match_count` | Count objects matching a reference on type, color, rotation, material, or another named attribute set. |
| `reference_metric_relation_count` | Count objects larger, smaller, closer, farther, taller, or otherwise metric-related to a reference. |
| `count_arithmetic` | Sum two selector counts, or compute the difference between red and blue object counts. |
| `counterfactual_count` | Count target objects after adding, removing, or replacing visible objects. |
| `change_relation_count` | Count added, removed, moved, color-changed, or size-changed objects between panels. |

Same-axis set membership is still a single-attribute program. For example,
`red or blue` is `single_attribute_membership_count` with
`attribute_axis=color` and `target_values=[red, blue]`.

Cross-axis Boolean operators are separate families because they construct
different selector sets. `red circle`, `red OR circle`, `red but not circle`,
`exactly one of red/circle`, and `neither red nor circle` should not be merged
into one generic Boolean-count task.

Boolean OR is not arithmetic. `red OR circle` counts overlapping red circles
once, while `count(red) + count(circle)` can count them twice. Keep
`multi_attribute_or_count` separate from `count_arithmetic`.

Probability tasks that select outcomes by visible attributes follow the same
selector-family split. `P(red)` and `P(circle)` are one
`single_attribute_probability` family when only the attribute axis changes.
`P(red AND circle)` is a separate conjunctive probability family, and
`P(red OR circle)` is a separate inclusive-or probability family. The answer
operation changes from `count` to `reduced_fraction`, but the selector boundary
is the same as object counting.

Object-count programs follow this chain:

```text
candidate_set -> optional scope/relation/filter -> selector expression -> count -> optional arithmetic/edit/change layer
```

Adding a new layer usually creates a new task. Changing a parameter inside a
layer usually does not.

Do not force algorithmic counts into these object-count names. If the counted
set is produced by a domain rule or construction, use a concrete
domain/program family name instead. Examples include:

- game legal/safe action counts;
- game simulated effect counts after a marked move;
- graph component, degree-filter, cut-structure, exact-distance, or transfer
  counts;
- geometry classified-entity, relation, region-membership, or function-feature
  counts;
- puzzle rule-violation, valid-candidate, simulated-attribute, reachability, or
  path-blocker counts.

The shared object-count names are for candidate sets selected by visible
attributes, scopes, relations, references, edits, or before/after changes. They
are not a replacement for genuine graph algorithms, game rules, geometry
classifications, puzzle simulations, or physics formulas.

For topology/reachability tasks, the reachable set computation can be a shared
subroutine without making the public task identical. A task that returns
`count(reachable_nodes)` and a task that returns `label(select_unreachable_node)`
must split because the output operation and answer schema differ, even if both
derive from `reachable_from(start, graph)`.

## Formula And Rule Domains

Geometry and physics tasks need formula schema in the task boundary.

Same task:

```text
a^2 + b^2 = c^2
unknown_slot: a | b | c
```

Different tasks:

```text
rectangle_area(width, height)
triangle_area(base, height)
circle_area(radius)
```

unless they are explicitly represented inside a stable broader program, such
as:

```text
composite_area(sum_or_difference(component_area(component_type, params)))
```

Geometry count tasks are different from formula-measurement tasks. Counting
squares vs triangles can be one `shape_type_cardinality` task, but counting
equilateral triangles should usually be a `triangle_class_cardinality` task
because the selector requires a different geometric classification program.

Game and graph tasks follow the same principle: legal move generation,
attack-set construction, traversal order, shortest path, longest path,
component membership, and ancestor reasoning are different program schemas
unless they are explicitly one stable skeleton with bounded parameters.

For games, do not split `all legal moves` from a simple filtered subset of the
same legal move set when the program can be written as:

```text
count(filter(legal_moves(state), move_filter))
```

with `move_filter` values such as `any_legal`, `capture`, or `corner`. Split
when the branch adds lookahead, simulates a result state, changes the candidate
set, or changes the annotation witness structure.

## Worked Examples

### Ranked Boxplot Difference

```text
charts
  boxplot
    median_rank_difference_value
```

```yaml
public_task_id: task_charts__boxplot__median_rank_difference_value
scene_contract:
  domain: charts
  scene_id: boxplot
  view_contract: single_boxplot_panel
task_contract:
  answer_schema: integer_value
  annotation_schema: keyed_point_map selected_rank_label -> median_mark_center
  program_schema: difference(value(rank_select(boxplots, statistic=median, rank_a)), value(rank_select(boxplots, statistic=median, rank_b)))
task_slug: median_rank_difference_value
parameter_axes:
  statistic: [median]
  rank_a: [top]
  rank_b: [bottom, second, third]
```

Adding top-vs-fourth extends the parameter support. It does not create a new
taxonomy node.

### Multiseries Ranked Metrics

These should split because they construct different derived metrics before the
same final rank selection:

```text
charts
  multiseries
    ranked_change_extremum_label
    ranked_series_share_extremum_label
    ranked_pair_ratio_extremum_label
```

Representative schemas:

```text
ranked_change_extremum_label:
  program_schema: label(select_by_rank(categories,
    pairwise_change_metric(value(series_a, category), value(series_b, category), mode),
    rank,
    order))
  parameter_axes:
    mode: [directional_increase, directional_decrease, absolute_gap]
    rank: [1, 2, 3]
    order: [largest, smallest where valid]
```

```text
ranked_series_share_extremum_label:
  program_schema: label(select_by_rank(categories,
    value(target_series, category) / sum(value(series, category) for series in all_visible_series),
    rank,
    order))
  annotation_schema: keyed_point_map answer_category:<each_visible_series> -> mark_center
```

```text
ranked_pair_ratio_extremum_label:
  program_schema: label(select_by_rank(categories,
    value(numerator_series, category) / value(denominator_series, category),
    rank,
    order))
  annotation_schema: keyed_point_map answer_category:numerator_series|denominator_series -> mark_center
```

The final operator is rank selection in all three cases, but the task contract
is not the same. Change metrics read two series and compute a difference or
gap. Series share reads all visible series in the answer category and computes
a category-total share. Pair ratio reads two role-bound series and computes a
quotient. The annotation role template also differs between series-share and
pair-ratio branches, so they should not be one task.

### Table Predicate Counts

These should split:

```text
count(table.rows where cell[column].value > threshold)
count(table.rows where low <= cell[column].value <= high)
count(table.rows where cell[column].value == category)
```

They differ by predicate schema: one-bound numeric, two-bound numeric, and
categorical equality.

These may stay together:

```text
rank_select(table.rows, key=cell[column].value, order, k)
```

with:

```yaml
order: [highest, lowest]
k: [2, 3, 4]
column: visible_numeric_column
```

The rank order and rank position are parameters of the same ranked-selection
schema.

### Dominoes

```text
games
  dominoes
    double_count
    exact_pip_sum_count
    relative_reference_sum_count
    direct_play_count
    second_play_candidate_count
    extendable_first_play_count
```

Representative schemas:

```text
double_count:
  program_schema: count(loose_tiles where tile.left == tile.right)
exact_pip_sum_count:
  program_schema: count(loose_tiles where pip_sum(tile) == target_sum)
relative_reference_sum_count:
  program_schema: count(loose_tiles where compare(pip_sum(tile), pip_sum(ref_tile), comparator))
direct_play_count:
  program_schema: count(loose_tiles where can_connect(tile, open_end(ref_tile)))
second_play_candidate_count:
  program_schema: count(loose_tiles - first_play where can_connect(tile, new_open_end(first_play, open_end(ref_tile))))
extendable_first_play_count:
  program_schema: count(first_play in loose_tiles where can_connect(first_play, open_end(ref_tile)) and exists second_play ...)
```

All can return integer counts with `bbox_set` annotation, but the program schemas
are different. `greater_than` vs `less_than` in the relative-reference schema
is a parameter; direct legal play vs lookahead is a split.

### Chess

```text
games
  chess
    piece_kind_count
    colored_piece_kind_count
    marked_piece_destination_count
    marked_piece_blocker_count
    side_capture_piece_count
    target_square_attacker_count
    king_escape_square_count
```

Representative schemas:

```text
piece_kind_count:
  program_schema: count(pieces where piece.kind == target_kind)
colored_piece_kind_count:
  program_schema: count(pieces where piece.kind == target_kind and piece.color == target_color)
marked_piece_destination_count:
  program_schema: count(legal_destinations(marked_piece) where destination_filter(destination))
marked_piece_blocker_count:
  program_schema: count(pieces strictly between marked_slider and target_square)
side_capture_piece_count:
  program_schema: count(opponent_pieces where exists friendly_piece: can_capture(friendly_piece, opponent_piece))
target_square_attacker_count:
  program_schema: count(pieces from queried side where attacks_square(piece, marked_target_square))
king_escape_square_count:
  program_schema: count(one_step_king_destinations(marked_king) where legal_after_move(destination) and not attacked_after_move(destination))
```

Marked-piece legal destinations and marked-piece capture destinations can stay
inside one task when `destination_filter` is a bounded parameter and annotation
is always destination-square witnesses. Line blockers, side-wide capture,
target-square attackers, and king escape are different chess-rule programs.

### Cell Board

```text
puzzles
  cell_board
    scoped_color_cell_count
    color_component_count
    largest_component_size
    shortest_path_length
    color_set_min_distance
    target_reachability_count
    reachable_region_size
    mirror_symmetry_violation_count
```

Representative schemas:

```text
scoped_color_cell_count:
  program_schema: count(filter(select(tile_cells, scope), color == target_color))
color_component_count:
  program_schema: count(connected_components(cells where color == target_color, adjacency=4_neighbor))
largest_component_size:
  program_schema: count(argmax_component_size(connected_components(cells where color == target_color, adjacency=4_neighbor)))
shortest_path_length:
  program_schema: length(shortest_path(open_cells, start_marker, goal_marker))
color_set_min_distance:
  program_schema: min_distance(cells where color == color_a, cells where color == color_b, metric=orthogonal_steps)
target_reachability_count:
  program_schema: count(select(target_cells, reachability_from(start_marker) == target_reachability))
reachable_region_size:
  program_schema: count(reachable_set(open_cells, start_marker))
mirror_symmetry_violation_count:
  program_schema: count(counted_side_cells where cell.value != mirror_partner(cell).value)
```

Row, column, edge, and whole-board color counts are one task because `scope` is
a bounded selector parameter. Component count vs largest component size,
endpoint shortest path vs color-set minimum distance, and target-reachability
count vs reachable-region size are different tasks because they construct
different intermediate reasoning objects.

### Binary Tree

```text
graph
  binary_tree
    child_arity_count
    depth_level_count
    local_node_relation_label
    lowest_common_ancestor_label
    dfs_traversal_kth_label
    level_order_traversal_kth_label
    bst_path_terminal_label
    heap_violation_label
```

Representative schemas:

```text
child_arity_count:
  program_schema: count(nodes where child_count(node) satisfies predicate)
depth_level_count:
  program_schema: count(nodes where depth_from_root(node) == target_depth)
local_node_relation_label:
  program_schema: related_node(query_node, relation)
lowest_common_ancestor_label:
  program_schema: lowest_common_ancestor(node_a, node_b)
dfs_traversal_kth_label:
  program_schema: dfs_traversal(root, visit_order)[k]
level_order_traversal_kth_label:
  program_schema: bfs_level_order(root)[k]
bst_path_terminal_label:
  program_schema: follow_bst_comparisons(root, query_key, mode).terminal_node
heap_violation_label:
  program_schema: select child where child.key < parent.key
```

`parent`, `left_child`, `right_child`, and `sibling` can stay one local-relation
task only if they share one annotation schema such as one query node plus one
answer node. Lowest common ancestor splits because it needs two input nodes and
one answer node and a different ancestor/path program.
BST search-terminal and insert-parent queries can stay one task when both use
the same comparison-path program and only change `operation_mode`.

## Review Workflow

When auditing a scene:

1. List current public tasks and query branches.
2. Write the scene contract and any branch-level view contract for each branch.
3. Write the answer schema and annotation schema for each branch.
4. Write the shallowest program schema that preserves required intermediate
   reasoning objects.
5. Check the concrete program contract fields: candidate set, operand roles,
   derived computation, final operator, output binding, and annotation role
   template.
6. Mark any generic/inferred program rows as draft-only until manually
   refined. Do not approve them.
7. Merge branches only when the scene contract remains stable and all three
   task contract fields match.
8. Split branches when any task contract field changes, or when view contract
   stability would be violated.
9. Name the resulting task from the taxonomy, not from legacy query ids.
10. Record parameter axes for coverage review, but do not treat parameter
   values as taxonomy leaves.

The review app should eventually show:

```text
domain -> scene_id -> task_slug
```

Each task page should show:

- public task id;
- task slug;
- scene contract and view contract;
- answer schema;
- annotation schema;
- program schema;
- optional descriptive review tags;
- parameter axes;
- coverage over generated parameter combinations;
- examples, preferably five per generated parameter combination.

## What Not To Do

- Do not make public task ids tree labels except as metadata/link rows.
- Do not create taxonomy leaves for arbitrary parameter values such as
  `top_second`, `red_circle`, or `sunk_ship`.
- Do not split parameter values only because prompt wording differs.
- Do not merge tasks only because they share an answer type or both contain a
  count.
- Do not approve a program contract with generic placeholders such as
  `items`, `metric`, `condition`, or `predicate` unless those placeholders are
  defined by a concrete candidate set, operand role, and derived computation.
- Do not define parent schemas so broadly that they hide meaningful child
  programs already represented elsewhere.
- Do not define schemas so narrowly that every concrete query string becomes a
  task.

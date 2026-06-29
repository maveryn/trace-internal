# `task_puzzles__string_topology__string_component_count`

## Identity
1. Domain: `puzzles`
2. Scene id: `string_topology`
3. Public task id: `task_puzzles__string_topology__string_component_count`
4. Source: `trace/tasks/puzzles/string_topology/string_component_count.py`

## Query Contract
Supported `query_id`: `open_rope_count`, `closed_loop_count`, `knotted_component_count`

1. `open_rope_count`: count separate string components with two visible endpoints.
2. `closed_loop_count`: count separate closed-loop components, including knotted closed loops.
3. `knotted_component_count`: count separate string components with at least one visible knot.

These query ids are semantic predicate mirrors of the same component-count program. Scene styling, object counts, distractor counts, and layout variation are generation/render metadata, not query ids.

## Program Contract
`count(string_component, predicate=query_id); scene=string_topology; scope=string_component_count`

The generator constructs separate string components plus distractor components so the requested count is unique by construction. Crossings are visual topology cues and do not merge components.

## Answer And Annotation
1. `answer_gt.type`: `integer`
2. `annotation_gt.type`: `bbox_set`
3. Annotation schema: `bbox_set`
4. Annotation contains one image-pixel bounding box for each counted string component.
5. Annotation cardinality equals the integer answer.

## Review Notes
1. The renderer may use `string_strip`, `string_card`, or `string_outline` scene styling.
2. The task uses multi-element bbox-set annotation, so scalar annotation does not apply.

# Annotation Review

Use this procedure when auditing task annotation quality across tasks, scenes,
or domains. The goal is to decide whether each task's annotation contract is
good, bad, or needs human design judgment under Trace's current annotation
norms.

This is a review guide. Do not redefine task ids, reward behavior, or program
contracts here.

## Review Output

For every task reviewed, report one of:

- `good`: annotation schema, generated payload, prompt hint, and task doc are
  aligned with current norms.
- `bad`: there is a clear violation that should be fixed before review
  acceptance.
- `borderline`: more than one annotation choice could be defensible; explain
  the tradeoff and recommend one direction.

When reporting findings, separate clear fixes from suggestions. Do not present
borderline preferences as hard failures.

## Core Checks

Check these for every task:

- The task doc annotation schema matches generated `annotation_gt.type`.
- Prompt wording and output examples use `annotation`, not retired grounding
  wording.
- Prompt annotation hints match the actual schema and shape.
- `projected_annotation` and `annotation_gt` describe the same witness values.
- The answer and annotation are bound from the same execution trace.
- The annotation marks minimal visual witnesses, not answer labels, option text,
  or unrelated context.
- Similar visual witnesses inside the same domain use the same annotation
  family unless the task doc explains a real exception.

## Geometry Choice

Choose annotation geometry from the visual witness the answer depends on.

Use bbox-family annotations for area-like witnesses:

- physical objects in counting tasks;
- selectable regions, option cards, image patches, cells, tiles, board squares,
  page controls, text boxes, table cells, chart bars, and large rendered marks.

Use point-family annotations for point-like or center-like witnesses:

- chart points, graph nodes, vertices, intersections, token centers, marble or
  ball centers, pointer tips, and other compact localization witnesses where a
  box would be artificial.

Use segment-family annotations for line-like witnesses:

- paths, edges, route spans, row or column spans, shot lines, vector arrows,
  geometric sides, and intervals.

Avoid mixed point and bbox annotation in one task. If a task appears to need
mixed geometry, first reconsider the task contract or use homogeneous map
annotation only when the keys are genuinely non-interchangeable.

## Cardinality Choice

Use scalar annotation when cardinality is guaranteed to be one:

- exactly one box: `bbox`
- exactly one point: `point`
- exactly one line/path/span: `segment`

If the task has exactly one witness, do not wrap it in a named map just because
the role has a natural name. For example, a single selected endpoint box should
be `bbox`, not `bbox_map` with an `answer_endpoint` key.

Use set annotation for unordered homogeneous witnesses:

- object counts: usually `bbox_set`
- point-like counts: usually `point_set`
- line/path counts: usually `segment_set`

Use sequence annotation only when order is part of the answer contract, such as
a traversal or path order. Use map annotation only when multiple semantic roles
must be bound, such as source versus selected option, reference versus answer
item, or input versus output measurement.

Do not use a one-item set or a one-key map to avoid scalar annotation.

## Bbox Stability

Bbox-family annotations must be large enough to be useful and stable.

Current global rule:

- Every annotation bbox should have width `>= 24px` and height `>= 24px`.
- This applies to `bbox`, `bbox_set`, `bbox_sequence`, `bbox_map`, and
  `bbox_set_map`.
- If the true visible object is smaller or thinner, expand a centered annotation
  box around it.
- Expanded boxes must stay inside the image and must still identify the same
  witness unambiguously.
- If expansion makes the witness ambiguous or overlaps neighboring answer
  candidates, redesign the rendering or task instead of silently switching to
  points.

Thin physical objects are still physical objects. For example, book-count
tasks should use padded book bboxes rather than points if the domain policy is
physical-object counting by bbox.

## Clear Violations

Mark a task `bad` when any of these is true:

- The generated annotation type differs from the task doc or prompt hint.
- A guaranteed-single witness uses `point_set`, `bbox_set`, or `segment_set`.
- A guaranteed-single witness uses `point_map` or `bbox_map` even though there
  is no second role to bind.
- A bbox-family annotation has a side below `24px` without an approved task
  redesign.
- A physical object counting task uses points while similar domain tasks use
  bboxes, with no documented reason.
- A task uses bbox for a genuinely point-like mark and this makes the witness
  arbitrary or very small.
- A path, edge, route, or span is represented as unrelated endpoint points when
  a segment would be the faithful witness.
- A map annotation is used even though witnesses are homogeneous and unordered.
- An unordered set is used when role binding is required to verify the answer.
- Annotation includes option labels, text answers, decorative context, or the
  whole scene instead of minimal witnesses.
- Docs or prompts still use retired grounding wording for active task output.

## Borderline Cases

Mark a task `borderline` when the annotation is not clearly wrong but another
choice may be more consistent:

- compact game pieces or icons could be treated as centers or object boxes;
- chart glyphs with visible area could be boxes, but the task is really about
  data-point location;
- dense small objects could use padded bboxes, but the renderer may need more
  spacing first;
- a scoped count could annotate counted objects only, or also key the reference
  region if the prompt makes the reference ambiguous;
- a pair or path could be a set, sequence, or segment depending on whether order
  matters.

For borderline cases, recommend the choice that is most consistent with nearby
tasks in the same domain.

## Review Report Format

Use a concise report:

```text
<task_id>: good
<task_id>: bad - generated type is bbox_set but prompt asks for point_set.
<task_id>: borderline - counted icons are small; bbox_set is consistent with
object counts, but renderer may need larger item size before conversion.
```

For scene or domain reviews, include a summary list:

- required changes;
- suggested changes;
- no-change tasks worth noting because they follow the intended exception.

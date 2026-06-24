# Prompt Review

Use this procedure when auditing task prompts across tasks, scenes, or domains.
The goal is to decide whether each prompt is aligned with the task contract,
answer schema, annotation schema, and visible rendered image.

This is a review guide. Do not define prompt-bundle schema or task contracts
here.

## Review Output

For every task reviewed, report one of:

- `good`: prompt wording, answer hint, annotation hint, JSON examples, and task
  contract are aligned.
- `bad`: there is a clear prompt mismatch or confusing instruction that should
  be fixed before review acceptance.
- `borderline`: the prompt is contract-valid but may be too verbose, too terse,
  unnatural, or less consistent than nearby tasks.

Separate required fixes from suggestions. Do not mark stylistic preferences as
hard failures unless they affect task correctness or consistency.

## Core Checks

Check these for every task/query:

- The question asks for exactly the task's answer contract.
- The answer hint matches `answer_gt.type` and tells the model what value to
  compute or select. It must not merely expose the answer support/range, such
  as “integer from 0 to 5,” when the useful instruction is “the number of
  counted boxes” or another task-specific value.
- The annotation hint matches `annotation_gt.type`.
- JSON examples are valid for the active answer and annotation schemas.
- Prompt examples are internally coherent, even though they are not the sampled
  instance answer.
- The prompt uses `annotation`, not historical `evidence` wording.
- The prompt does not expose hidden trace fields, implementation names, or
  sampling internals.
- The prompt does not duplicate generic output-protocol boilerplate such as
  "Use JSON only," "Return only JSON," or "Final answer format." Those
  constraints belong in the shared/system prompt layer; task prompts should
  keep only task-specific answer/annotation content and examples.
- The prompt does not ask for labels, option text, decorative context, or
  unrelated regions as annotation unless those are the actual visual witnesses.
- The prompt includes only the visual/rule details needed to solve the task.
- The prompt does not mention incidental operand attributes such as clothing,
  style, marker absence, or object rendering details unless they are required
  to identify the target or answer the question.
- The question names the task operands directly when the operands are known.
  Prefer “What total flow leaves \"A\" for target nodes \"B\" and \"C\"?” over
  indirect wording such as “Using only the curved bands from \"A\" to \"B\" and
  \"C\", sum the printed values.”

## Example Consistency

Examples show output shape, not the current instance's answer. They still must
be valid examples for the same task contract.

Required consistency:

- If the example answer is a count and annotation is the counted witness
  collection, the example annotation cardinality must match the example answer.
- Scalar `point`, `bbox`, and `segment` examples must use scalar shapes, not
  one-item sets.
- `point_set`, `bbox_set`, and `segment_set` examples must use arrays of
  homogeneous witnesses.
- Ordered annotation examples must preserve the expected order.
- Map annotation examples must use keys that are valid for that
  task family.
- Label/MCQ examples must use labels that are valid for that task style. Use
  one-letter examples only for option-letter tasks.
- Segment examples should use `[[x1, y1], [x2, y2]]` shape so endpoints are
  unambiguous.
- Annotation coordinates in examples are final image pixel coordinates. Do not
  show grid indices, row/column labels, chart values, scene-local coordinates,
  or normalized values as annotation.

Bad example for a count task:

```json
{"annotation": [[100, 120], [140, 120], [180, 120]], "answer": 2}
```

Good example for the same `point_set` count contract:

```json
{"annotation": [[100, 120], [140, 120]], "answer": 2}
```

## Annotation Prompting

The annotation instruction should describe the witness, not the reasoning
process.

Good annotation hints:

- “one bbox per counted visible vehicle”
- “the center point of the selected node”
- “the segment joining the two endpoints of the marked path”

Avoid hints that ask for:

- answer labels instead of visual witnesses;
- all options when only the selected option is annotated;
- whole panels or scenes when the witness is a smaller object;
- internal ids, trace keys, or sampled variables;
- grid coordinates or row/column names instead of image pixels.

## Verbosity And Naturalness

Prompts should be natural and direct.

Mark a prompt `borderline` when it is correct but:

- repeats the same scene or task noun across layers;
- explains obvious visual conventions that the image already makes clear;
- phrases a simple operand-bound lookup or arithmetic task indirectly when a
  direct source/target, row/column, panel/category, or node/edge wording would
  be clearer;
- includes long rule text when a shorter rule is enough;
- mixes too many parentheticals, caveats, or implementation details;
- says “image,” “question,” “answer,” or “task” repeatedly without adding
  useful information;
- repeats shared output-protocol wording instead of just naming the
  task-specific answer and annotation payloads.

Mark a prompt `bad` when verbosity changes the task meaning, hides the actual
question, or introduces contradictions.

## Clear Violations

Mark a task `bad` when any of these is true:

- The prompt question and answer schema disagree.
- The prompt question and generated answer semantics disagree.
- The answer hint only states the answer range/support instead of the
  task-specific value being requested.
- The annotation hint and generated `annotation_gt.type` disagree.
- The prompt asks for point annotation but generated annotation is bbox-family,
  or vice versa.
- The example answer and example annotation cardinality conflict for count
  tasks.
- The example uses one-item sets for scalar annotation.
- The example uses scene/grid/chart/data coordinates instead of image pixels.
- The prompt uses stale `evidence` wording.
- The prompt includes generic JSON-only or final-format boilerplate that should
  be supplied by the shared/system prompt layer.
- The prompt asks the model to annotate non-witness text, labels, or options.
- The prompt includes task-specific hidden trace values that should not be
  visible to the model.

## Borderline Cases

Mark a task `borderline` when:

- the prompt is correct but too detailed;
- the prompt is terse enough that a human might miss the intended witness;
- the example is structurally valid but not representative of the common case;
- the annotation hint is technically correct but inconsistent with nearby tasks;
- the prompt rule is understandable but could be simplified.

For borderline cases, recommend the wording pattern used by the closest
accepted tasks in the same domain.

## Review Report Format

Use a concise report:

```text
<task_id>: good
<task_id>: bad - answer example is 2 but annotation example has 3 points.
<task_id>: borderline - prompt is correct but over-explains the move rule.
```

For scene or domain reviews, include:

- required prompt fixes;
- suggested wording improvements;
- no-change tasks worth noting because their prompt pattern should be reused.

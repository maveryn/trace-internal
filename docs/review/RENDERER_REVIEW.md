# Renderer Review

Use this procedure when auditing rendered images across tasks, scenes, or
domains. The goal is to decide whether each renderer produces a clear,
contract-aligned visual instance for the prompt, answer, annotation, and trace
metadata.

This is a review guide. Do not define renderer APIs, prompt-bundle schema, or
task contracts here.

## Review Output

For every task reviewed, report one of:

- `good`: rendering, prompt-facing visual cues, annotation projection, and trace
  metadata are aligned and legible.
- `bad`: there is a clear rendering mismatch or visual ambiguity that should be
  fixed before review acceptance.
- `borderline`: the rendered image is contract-valid but could be made clearer,
  more consistent, or more robust.

Separate required fixes from suggestions. Do not mark style preferences as hard
failures unless they affect task correctness, consistency, or reviewability.

## Core Checks

Check these for every task/query:

- The rendered scene contains the visual objects, regions, labels, options, and
  cues that the prompt asks about.
- Prompt-facing visual cues match the prompt wording exactly.
- Annotation witnesses align with the final rendered pixels.
- Answer, annotation, prompt, and render metadata come from the same execution
  trace.
- Text, labels, markers, icons, pieces, and option letters are legible and not
  cropped, overlapped, or hidden.
- The scene has enough visual variety for the domain without changing the task
  contract.
- Stochastic render choices that affect prompt wording or annotation projection
  are recorded in trace metadata.

## Prompt-Render Consistency

If the prompt names a visual cue by color, shape, label, direction, pattern, or
style, the renderer must draw that exact cue as the primary visible mark.

Examples:

- If the prompt says `red marked square`, the marked square must use red as the
  primary marker color.
- If the prompt says `blue route`, the route line must be blue.
- If the prompt asks for option `C`, the image must contain a visible option
  label `C` at the relevant candidate.
- If the prompt says `dashed line`, the visible line must be dashed.

Contrast helpers may add halos, shadows, strokes, or outlines, but those support
the named cue. They must not replace or contradict it. A red marker with a black
or white contrast halo is valid. A random cyan, yellow, or purple marker is not
valid when the prompt says red.

Prefer prompts like `marked square`, `highlighted region`, or `shown route`
when the cue color is only a visual aid. Once a prompt names a color or style,
that color or style becomes part of the rendered task contract.

## Semantic Markers

Semantic markers are visual cues that the solver must use: marked cells,
selected objects, highlighted regions, arrows, paths, target points, and similar
answer-bearing marks.

Review semantic markers for:

- Primary cue consistency with the prompt.
- Strong contrast against the local surface.
- Stable visibility across all style variants and backgrounds.
- No confusion with ordinary game pieces, chart marks, text labels, or
  decorative styling.
- No accidental change in annotation geometry.

If a scene uses a shared contrast-safe marker helper, verify that it does not
randomize away from a prompt-named color or style.

## Text And Labels

Text and labels should be readable at the generated image size.

Mark a renderer `bad` when:

- option labels are off-center, cropped, or visually attached to the wrong
  object;
- labels overlap pieces, objects, axes, or other labels;
- label colors blend into their background;
- prompt-referenced labels are missing from the image;
- decorative titles look like answer-bearing labels.

Scene titles, badges, legends, and rule cards should appear only when they carry
useful task context or are part of the scene grammar. Avoid generic titles that
repeat the prompt without adding information.

## Layout And Canvas

Review layout at the image level, not only individual objects.

Mark a renderer `bad` when:

- the relevant object or board is cropped;
- the canvas has excessive empty space that harms readability;
- the board or object is always fixed in the exact same position when the scene
  is expected to use layout jitter;
- generated options overlap or use inconsistent sizing;
- a scene with repeated units violates the domain's minimum unit-size or visual
  jitter expectations without an approved exception.

Mark `borderline` when layout is correct but noticeably less polished than
nearby accepted scenes in the same domain.

## Options And MCQ Panels

For tasks with visual options:

- Option count must match the task contract.
- Abstract option labels should be deterministic, readable, and consecutive in
  display order: usually `A`, `B`, `C`, ... for the visible option count, or
  `1`, `2`, `3`, ... when numeric option ids are the scene convention.
- Do not move the correct answer label to the first visible position or sample a
  non-consecutive visible set such as `E`, `A`, `B`, `C` unless the labels carry
  task-specific semantic meaning in the rendered scene.
- Option panels should use consistent sizing and spacing.
- The correct option must be unique by construction.
- Distractors should be plausible but not visually ambiguous with the answer.
- Annotation should mark the minimal selected visual witness, not all option
  labels, unless the task contract explicitly asks for all options.

## Annotation Projection

Rendered geometry and annotation projection must agree.

Mark a renderer `bad` when:

- projected `point`, `bbox`, or `segment` values do not sit on the intended
  visible witness;
- annotation uses pre-jitter or pre-scale coordinates;
- annotation bboxes are too small, clipped, or shifted away from their object;
- line or route annotations do not match the visible path;
- generated image changes after annotation projection.

Use `docs/review/ANNOTATION_REVIEW.md` for schema-choice review. This renderer
review only checks whether the chosen schema lands correctly on the rendered
pixels.

## Visual Variety

Visual variety should be safe and contract-preserving.

Good variety includes:

- background treatments and palettes that keep contrast safe;
- technical-diagram theme profiles matched to the scene contract: analytical
  profiles may vary paper/board/slide surfaces, while graph-paper profiles must
  preserve Cartesian grid, axis, and lattice readability;
- domain-appropriate board, object, chart, or page style variants;
- font variety where text remains readable;
- layout jitter that updates annotation coordinates correctly.

Bad variety includes:

- color sampling that contradicts prompt text;
- style variants that hide markers or labels;
- font choices that make labels illegible;
- object styles that change the task semantics.

## Clear Violations

Mark a task `bad` when any of these is true:

- Prompt names a marker color or style that the renderer does not use as the
  primary visible cue.
- Prompt asks about a visible object, option, route, row, column, or region that
  is missing or ambiguous in the image.
- A semantic marker blends into the board, chart, object, or background.
- Labels or option text are cropped, off-center enough to confuse ownership, or
  overlap other answer-bearing visuals.
- The annotation projection is visibly shifted, stale, or inconsistent with
  layout jitter.
- Style variation changes the answer semantics or makes a previously valid
  task ambiguous.
- The image includes stale titles, badges, legends, or rule cards that conflict
  with the prompt.

## Borderline Cases

Mark a task `borderline` when:

- a marker is visible but less prominent than nearby scenes;
- prompt wording could avoid naming a color that is only a cue;
- a board, chart, or panel is readable but has too much unused canvas;
- option distractors are valid but too visually similar;
- style variation is safe but underdeveloped;
- labels are readable but visually cramped.

For borderline cases, recommend the rendering pattern used by the closest
accepted tasks in the same domain.

## Review Report Format

Use a concise report:

```text
<task_id>: good
<task_id>: bad - prompt says red marked square, but marker samples cyan.
<task_id>: borderline - route is visible, but the label is cramped near the
board edge.
```

For scene or domain reviews, include:

- required renderer fixes;
- suggested visual polish improvements;
- no-change tasks worth noting because their renderer pattern should be reused.

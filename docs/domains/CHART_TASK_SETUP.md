# Chart Task Setup

## Purpose
Define the concrete v1 setup for the first chart-domain task family.

This is the chart-domain counterpart to `docs/domains/TILE_TASK_SETUP.md`: a source-of-truth note for the first implementation wave, not just a long-term idea list.

## V1 scope
1. `domain = charts`
2. First `task_group = statistics`
3. First concrete statistics tasks:
   - `task_charts_statistics_summary_value`
   - `task_charts_statistics_summary_label`
4. First supported chart-type renderings:
   - `bar`
   - `line`
   - `scatter`

## Taxonomy
1. Keep the normal TRACE split:
   - `domain -> task_group -> task`
2. For this family:
   - `task_group = statistics`
   - active tasks: `summary_value`, `summary_label`
3. The semantic statistic is the public `task_variant`.
4. The chart type is the visual `scene_variant`.

### V1 variant axes
1. `task_variant`:
   - `max`
   - `min`
   - `range`
   - `mean`
   - `median`
   - `sum`
   - `mode`
2. `scene_variant`:
   - `bar`
   - `line`
   - `scatter`

Note:
1. Charts are the first planned domain where one task naturally has both a semantic axis and a chart-type axis.
2. Until the cross-domain `scene_variant` ABI note is fully written in core docs, treat this file as the domain-local contract for that split.

## Scene contract
1. One chart per image.
2. One data series only in v1.
3. Use a clean light background with one chart frame/axis scaffold.
4. Every chart mark must have one visible unique label.
5. The label is the canonical mark identity for prompt-facing evidence.
6. Sample one random mark color per instance and use it consistently across all bars/points in that chart.
7. In v1, that mark color should be at least Lab distance `40` from white/light chart backgrounds.

### Chart-type semantics
1. `bar`
   - the statistic is computed over bar heights / bar values.
2. `line`
   - the statistic is computed over the plotted point `y` values, not over `x`.
   - visible point markers should be present so each labeled mark corresponds to one sampled data point.
3. `scatter`
   - the statistic is computed over point `y` values, not over `x`.

## Mark labels
1. Every mark uses one unique randomized uppercase label.
2. Labels may be one or two letters.
3. Labels must be assigned independently of:
   - rank,
   - value,
   - left-to-right order,
   - top-to-bottom order.
4. V1 should sample chart labels from a random uppercase subset rather than always starting with `A, B, C, ...`.
5. V1 should keep chart size modest enough that one-letter labels are usually sufficient.
6. Recommended initial mark count: `5..10`.

## Value range
1. V1 chart marks should use integer values in the range `1..20`.
2. Statistic-specific target-answer ranges may still be narrower than the full displayed value range.

## Answer contract
1. `answer_gt.type = integer`
2. All seven statistics should produce integer answers in v1 by construction.

### Per-variant answer meaning
1. `max`: highest displayed value
2. `min`: lowest displayed value
3. `range`: `max - min`
4. `mean`: arithmetic mean of all displayed values
5. `median`: median of all displayed values
6. `sum`: sum of all displayed values
7. `mode`: unique modal value
8. `sum` should use the full feasible support implied by the active mark-count and per-mark value bounds, not an additional narrow task-local cap.

## Evidence contract
1. V1 default `evidence_gt.type = label_set`
2. The evidence is the set of labeled marks that directly witness the requested statistic.
3. Label order must be deterministic.

### Evidence by statistic
1. `max`
   - singleton `label_set` containing the unique maximum mark
2. `min`
   - singleton `label_set` containing the unique minimum mark
3. `range`
   - two-label `label_set` containing the unique minimum mark and unique maximum mark
4. `mean`
   - `label_set` containing all chart marks used in the average
5. `median`
   - singleton `label_set` containing the median mark
6. `sum`
   - `label_set` containing all chart marks used in the sum
7. `mode`
   - `label_set` containing all marks whose value equals the unique modal value

### Why `label_set` in v1
1. The current ABI already supports `label_set`.
2. A chart-native evidence type such as `label_value_map` may be worth adding later, but it should not block the first chart task family.
3. Raw plotted geometry, bar boxes, or point coordinates should stay in trace as derived render projections rather than the public evidence contract for this family.

## Uniqueness and construction rules
1. Final numeric answer must be unique by construction.
2. `max` / `min`
   - require a unique maximum / unique minimum mark.
3. `range`
   - require a unique maximum and unique minimum mark.
   - prefer `range > 0` in v1.
4. `mean`
   - construct the dataset so the mean is an integer.
5. `median`
   - use an odd number of marks in v1.
   - with the current `5..10` mark-count policy, this means the effective median support is `5|7|9`.
   - prefer distinct values in v1 so the median mark is unique and evidence is singleton.
6. `sum`
   - no extra extremum-style uniqueness rule is needed beyond unique final answer.
7. `mode`
   - require one unique modal value.
   - evidence includes every mark with that modal value.

## Sampling policy
1. Global sampling stays at the task level, as elsewhere in TRACE.
2. Inside `task_charts_statistics_summary_value`, sample:
   - `task_variant` from the supported statistics set,
   - `scene_variant` from the supported chart types for that statistic.
3. These two axes should be sampled independently at the policy level, subject to compatibility.
4. Then sample the target answer from feasible support before finalizing the concrete chart data/layout.

## Prompt rules
1. The chart-family prompt layer should establish:
   - that the image is a chart,
   - that marks are labeled,
   - that the answer must be derived from the chart values.
2. The task layer should ask only for the statistic itself.
3. When `scene_variant` is `line` or `scatter`, the prompt should make it explicit that the statistic is over the plotted values (`y` values), not over the horizontal positions.
4. Do not phrase chart statistics in category-name terms for this family; the requested output is always the numeric summary value.
5. `answer_and_evidence` prompts should ask for the supporting labeled marks, not pixel boxes or coordinates.

### Recommended task-layer wording
1. `max`
   - ask for the highest value among the labeled marks
2. `min`
   - ask for the lowest value among the labeled marks
3. `range`
   - ask for the difference between the highest and lowest values
4. `mean`
   - ask for the mean (average) value
5. `median`
   - ask for the median value
6. `sum`
   - ask for the total / sum of the values
7. `mode`
   - ask for the mode value

### Recommended prompt slots
1. `object_description_<scene_variant>`
   - describe the chart marks for the chosen chart type
2. `question_text_<task_variant>`
   - one per statistic kind
3. `evidence_hint`
   - should explain that evidence is the set of supporting mark labels
4. `answer_hint`
   - should explain that the answer is a numeric value
5. `json_example_answer_only_<task_variant>`
   - variant-aware examples are preferred
6. `json_example_<task_variant>`
   - variant-aware examples are preferred

## Trace guidance
1. Keep symbolic mark records in trace with:
   - `mark_id`
   - visible `label`
   - numeric `value`
   - chart-type-specific geometry metadata
2. Keep `task_variant` and `scene_variant` explicit in trace/query metadata.
3. Keep derived pixel geometry in trace, not as the source of truth.

## Deferred follow-up
1. Add a chart-native evidence type if `label_set` becomes too weak for later chart families.
2. Formalize the cross-domain `scene_variant` ABI in core docs once charts are implemented.
3. Revisit whether the seven statistic kinds should later split into multiple tasks if charts need more task-level mass.

## Companion label-answer task
1. The first follow-up companion task is `task_charts_statistics_summary_label`.
2. It reuses the same chart scenes and `scene_variant` values (`bar|line|scatter`) but narrows the semantic `task_variant` set to:
   - `argmax`
   - `argmin`
   - `median_label`
3. Its contract is:
   - `answer_gt.type = option_letter`
   - `evidence_gt.type = integer`
4. Prompt-facing evidence is the winning numeric statistic value, while the answer is the visible label of the winning mark.
5. The label-answer task intentionally excludes `mean`, `sum`, `range`, and `mode` because those statistics do not map cleanly to one unique label answer in v1.

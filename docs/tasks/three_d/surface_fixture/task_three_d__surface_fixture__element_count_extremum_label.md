# `task_three_d__surface_fixture__element_count_extremum_label`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query ids: `highest_element_count`, `lowest_element_count`
- Answer type: `option_letter`
- Annotation type: `bbox`

## Contract
The image shows four labeled option panels, `A` through `D`, arranged in a 2x2
grid. Each option panel contains the same type of surface fixture and repeated
surface elements, but the visible element count differs across panels. No
numeric counts are printed in the image.

The answer is the capital letter of the option panel whose visible element
count is highest or lowest, depending on the query id.

Visible elements are assigned canonical named colors for visual variety. For
this task, color is recorded as `non_semantic_visual_variation`; it is not part
of the extremum predicate. The selected option is determined only by total
visible element count.

## Program Contract
- `label(select_panel(candidate_surface_fixture_panels, extremum(total_visible_element_count, highest|lowest))); scene=surface_fixture; scope=element_count_extremum_label`

The `highest_element_count` query binds `extremum_kind=highest`; the
`lowest_element_count` query binds `extremum_kind=lowest`.

## Annotation Contract
Annotation is the pixel box around the selected option panel. Individual
repeated elements and the option label badge are trace metadata but are not
prompt-facing annotation.

## Prompt Bundle
- Prompt text is loaded from `prompts/three_d/surface_fixture/three_d_surface_fixture_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle
version. Answers and annotation come from the same finalized option-grid render
trace.

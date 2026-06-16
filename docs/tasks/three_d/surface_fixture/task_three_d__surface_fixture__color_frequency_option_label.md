# `task_three_d__surface_fixture__color_frequency_option_label`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query ids: `most_frequent_color`, `absent_color`
- Answer type: `option_letter`
- Annotation type: `bbox`

## Program Contract
- `label(select_color_option(option_swatches, color = argmax(count(surface_fixture_elements by color)))); scene=surface_fixture; scope=color_frequency_option_label; query=most_frequent_color`
- `label(select_color_option(option_swatches, color_count(surface_fixture_elements, option_color)=0)); scene=surface_fixture; scope=color_frequency_option_label; query=absent_color`

## Contract
The image shows one projected fixture surface containing repeated colored
surface elements, plus six labeled color swatch options `A` through `F`.

For `most_frequent_color`, every option color appears on the fixture and
exactly one option color has the highest visible element count.

For `absent_color`, exactly one option color has zero visible elements on the
fixture; the other five option colors appear at least once.

The answer is the capital letter of the matching color option. The answer is
not the color name.

## Annotation Contract
Annotation is the pixel box around the selected color option swatch. Counted
surface elements, the fixture panel, and the option label badge are trace
metadata but are not prompt-facing annotation.

## Prompt Bundle
- Prompt text is loaded from `prompts/three_d/surface_fixture/three_d_surface_fixture_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle
version. Answers and annotation come from the same finalized fixture trace.

# `task_puzzles__matchstick__matchstick_number_transform_label`

## Program Contract

- scene=`matchstick`
- scope=`source_number_and_candidate_options`
- Program schema: `select_option(matchstick_number.one_stick_transform, operation=add_one|remove_one, source=visible_source_number); scene=matchstick; scope=source_number_and_candidate_options`
- task contract: choose the single labeled candidate number reachable from the visible Source number by adding or removing exactly one matchstick.
- query ids: `add_one_stick`, `remove_one_stick`
- query ids are semantic mirrors of the same program contract; nonsemantic material style, font, and panel treatment are trace metadata.

## Answer And Annotation

- Answer type: `option_letter`.
- Annotation type: `bbox_map`.
- Annotation schema: `bbox_map`.
- Annotation keys:
  - `source_number`: bbox around the Source panel.
  - `selected_option`: bbox around the selected candidate panel.
- The answer and annotation are bound from the same sampled trace. The trace records the source number, answer number, changed digit index, added/removed segment keys, and per-option reachability.

## Rendering And Prompt

The `matchstick` scene renders one Source panel and six labeled candidate panels using wooden-match, colored-rod, chalk-stick, neon-rod, or metal-rod visual styles. Prompt prose comes from `prompts/puzzles/matchstick/puzzles_matchstick_v1.json`.

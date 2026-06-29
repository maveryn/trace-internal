# `task_puzzles__matchstick__matchstick_loose_endpoint_extremum_label`

## Program Contract

- scene=`matchstick`
- scope=`loose_endpoint_option_comparison`
- Program schema: `select_option(matchstick_arrangement.loose_endpoint_extremum, extremum=max|min); scene=matchstick; scope=loose_endpoint_option_comparison`
- task contract: choose the single labeled stick arrangement with the unique largest or smallest loose-endpoint count.
- query ids: `most_loose_endpoints`, `fewest_loose_endpoints`
- query ids are semantic mirrors of the same program contract; nonsemantic material style, font, and panel treatment are trace metadata.

## Answer And Annotation

- Answer type: `option_letter`.
- Annotation type: `bbox`.
- Annotation schema: `bbox`.
- Annotation target: one bbox around the selected option panel.
- The answer and annotation are bound from the same sampled trace. The trace records each option edge set, each loose-endpoint count, the selected extremum query, and grid size.

## Rendering And Prompt

The `matchstick` scene renders six labeled lattice-stick arrangements using wooden-match, colored-rod, chalk-stick, neon-rod, or metal-rod visual styles. Prompt prose comes from `prompts/puzzles/matchstick/puzzles_matchstick_v1.json`.

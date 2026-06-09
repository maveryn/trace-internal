# Misc Task Setup

## Purpose
Capture the active contract for the `misc` domain.

`misc` is a bounded parking domain for renderer families that are synthetic and useful, but do not yet justify a dedicated top-level domain. It currently contains abacus readouts, clocks/readouts, automata, music notation, Braille-cell notation, organic-structure notation, Boolean logic-gate notation, and probability-device scenes. For cross-domain rollups, use `docs/ACTIVE_TASK_INVENTORY.md`.

## Active families
1. Current active `task_group` values:
   - `automaton`
   - `abacus`
   - `clock`
   - `notation`
   - `probability`
2. Current active task ids and scene counts are generated in `docs/ACTIVE_TASK_INVENTORY.md`.

## Family contract
1. Public misc task ids use `task_misc__<scene_id>__<objective_contract>`.
2. `misc` should remain small. Promote a renderer family to a dedicated domain if it grows into a coherent domain-scale surface, roughly `20..30` tasks across `3+` scenes.
3. Do not place a task in `misc` when an existing renderer domain fits cleanly.
4. Annotation remains minimal and role-keyed when witness roles matter, especially for source/option panels, clocks, notation marks, transition tables, and probability trays.
5. Shared misc background variants live in `configs/domains/misc/base.yaml`; scene-local renderers own semantic colors, symbols, labels, markers, and annotation projection.

## Abacus tasks
1. Active task ids:
   - `task_misc__abacus_match_panel__target_value_match_label`
   - `task_misc__abacus_readout__displayed_value_readout`
2. Public contract:
   - readout records `query_id=displayed_value_readout` and asks for the integer represented by one three-column soroban-style abacus,
   - match-panel records `query_id=target_value_match_label` and asks which of six labeled abacus option cards represents the prompt-provided target integer.
3. Supported `scene_variant` values:
   - `clean_card`
   - `wood_frame`
   - `worksheet`
4. Answer contract:
   - displayed-value answers use `answer_gt.type = integer`,
   - target-value match answers use `answer_gt.type = option_letter`,
   - v1 numeric support is `0..999`.
5. Annotation contract:
   - readout prompt-facing annotation is `keyed_point_set_map`,
   - readout keys are `hundreds_active_beads`, `tens_active_beads`, and `ones_active_beads`,
   - each readout key maps to active bead center points in that place-value column and may be empty for digit `0`,
   - match-panel prompt-facing annotation is a one-box `bbox_set` around the selected option card.
6. Scene contract:
   - the readout scene shows exactly three columns labeled `100`, `10`, and `1`,
   - the match-panel scene shows exactly six labeled option cards, each containing a compact three-column abacus,
   - each abacus column has one upper bead worth `5` and four lower beads worth `1`,
   - active beads are represented by position near the center beam rather than by a prompt-facing color rule,
   - rods, frame, beam, and labels are render scaffolding or trace metadata, not prompt-facing annotation.

## Automaton tasks
1. Active task ids:
   - `task_misc__agent_automaton__agent_final_pose_label`
   - `task_misc__agent_automaton__agent_cell_flip_count`
   - `task_misc__life_automaton__life_future_grid_label`
   - `task_misc__life_automaton__life_population_count`
   - `task_misc__turing_tape__turing_written_symbol_count`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - agent final-pose records `query_id=binary_rule_final_pose|three_state_rule_final_pose`,
   - agent update-count records `query_id=marked_region_flip_count` and records the sampled turning rule in trace metadata,
   - Life future-grid records `query_id=one_step_future_grid|two_step_future_grid`,
   - Life population-count records `query_id=marked_line_live_count`,
   - Turing written-symbol count records `query_id=written_symbol_count`.
3. Supported `scene_variant` values:
   - `clean_grid`
   - `lab_panel`
   - `notebook_grid`
4. Answer contract:
   - final-pose and future-grid tasks use `answer_gt.type = option_letter`,
   - update-count, population-count, and Turing written-symbol tasks use `answer_gt.type = integer`.
5. Annotation contract:
   - final-pose and Life future-grid use `annotation_gt.type = keyed_bbox_map`; other automaton tasks use `bbox_set`,
   - final-pose annotation uses `keyed_bbox_map` with `start_marker` and `selected_option`,
   - update-count annotation contains the marked-region box,
   - future-grid annotation uses `keyed_bbox_map` with `source_grid` and `selected_option`,
   - population-count annotation contains the marked row or column box,
   - Turing written-symbol annotation contains the starting tape/head panel and transition-table boxes.
6. Scene contract:
   - agent automaton scenes show a state grid plus an arrow marker for the starting pose,
   - binary rules use light versus colored state cells, with the actual non-semantic cell palette sampled by the scene style; three-state rules draw state labels `0`, `1`, and `2`,
   - `agent_automaton` samples non-semantic treatment and palette axes through the global shared panel-style layer, using the shared 20-treatment and 20-palette puzzle/game canvas registry,
   - `agent_automaton` also samples a scene-local `agent_board.board_style` axis (`classic_grid`, `rounded_tiles`, `inset_cells`, `lab_matrix`, `notebook_cells`) and records the selected style under `render_spec.scene_style.agent_board`,
   - agent labels, step markers, and option labels sample one deterministic font family from the readout font pool,
   - Life scenes use dark cells for alive cells and light cells for empty cells,
   - Life scenes sample the shared puzzle/game panel-style layer, use deterministic annotation-safe layout jitter, and record the role-aware font family used for option labels in `render_spec.scene_style.font`,
   - Life scenes also sample a scene-local `life_board.board_style` axis (`classic_grid`, `rounded_tiles`, `inset_tiles`, `lab_matrix`, `notebook_cells`, `terminal_cells`) and `life_board.cell_palette_id` axis (`mono_ink`, `blueprint_cells`, `forest_cells`, `plum_cells`, `sepia_cells`, `teal_cells`, `burgundy_cells`, `carbon_cells`),
   - Life cell palettes vary alive/dead/grid/edge/mark/accent RGBs while preserving the semantic rule that alive cells are dark and empty cells are light; resolved RGBs and contrast checks are recorded under `render_spec.scene_style.life_board`,
   - Life future-grid option panels use the same grid cell scale as the source grid so the task is a state-comparison problem, not a resize-matching problem,
   - Turing scenes show the starting tape, head position, start state, step count, queried symbol, and complete transition table,
   - option tasks render exactly five labeled option panels.
7. Trace contract:
   - `scene_ir.entities` and `render_map.item_bboxes_px` expose grid, target, agent, and option bboxes,
   - `execution_trace` stores the visible rule branch, grid dimensions, initial grid, simulation step count, answer value, supporting item ids, and query-specific symbolic fields.

## Clock tasks
1. Active task ids:
   - `task_misc__analog_clock__offset_readout`
   - `task_misc__clock_collection__compare`
   - `task_misc__clock_match_panel__equivalent_time_label`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - readout tasks record `query_id=minutes_after|minutes_before` by default; seconds query ids are supported for explicit `offset_unit=seconds` generation,
   - compare records `query_id=earliest_time_label|latest_time_label`,
   - match-panel records `query_id=analog_reference_digital_options|digital_reference_analog_options`.
3. Supported `scene_variant` values:
   - `classic`
   - `minimal`
   - `outline`
4. Answer contract:
   - readout tasks answer with HH:MM or HH:MM:SS strings,
   - compare answers with the winning clock label string,
   - match-panel answers with the matching option label string.
5. Annotation contract:
   - readout annotation is a `keyed_point_map` over the clock center and visible hand tips,
   - compare annotation is a one-box `bbox_set` over the winning clock face,
   - match-panel annotation is a `keyed_bbox_map` with `reference` and `correct_option` visual bboxes.
6. Scene contract:
   - readout clock numerals use one deterministic font family from the readout font pool and record it in `render_spec.clock_style.font`,
   - clock-collection compare scenes use one deterministic font family for every clock numeral and visible clock label, record it in `render_spec.clock_style.font`, and use standard annotation-safe post-image noise with `apply_prob=0.5`,
   - clock-match panels use a top reference plus fixed `A..F` visual option cards; option annotation marks the matching visual, not the label badge,
   - clock-match digital displays sample a non-semantic high-contrast case/screen/text palette recorded in `render_spec.clock_style.digital_display_palette`.

## Dice probability tasks
1. Active task ids:
   - `task_misc__dice_probability__single_attribute_probability`
   - `task_misc__dice_probability__single_threshold_probability`
   - `task_misc__dice_probability__pair_attribute_combo_probability`
   - `task_misc__dice_probability__pair_difference_probability`
   - `task_misc__dice_probability__pair_sum_probability`
   - `task_misc__dice_probability__pair_sum_threshold_probability`
   - `task_misc__dice_probability__dice_conditional_event_value`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - the sampled probability event is recorded as `query_id`.
3. Supported `scene_variant` values:
   - `dice_tray_clean`
   - `dice_tray_felt`
   - `dice_tray_notebook`
4. Answer contract:
   - `answer_gt.type = string`,
   - answer values are reduced fraction strings such as `"3/8"`.
5. Annotation contract:
   - `annotation_gt.type = keyed_bbox_map`,
   - single and conditional annotation uses `dice_tray`,
   - pair annotation uses `tray_a` and `tray_b`.
6. Scene contract:
   - dice are rendered as individual rounded square dice with visible top-face pips,
   - probability is always over uniformly selecting from the shown dice, not rolling unseen dice,
   - the single task samples parity, threshold, value-set, color-and-value, and color-or-value events,
   - the pair task samples independent one-die selections from Tray A and Tray B with sum, threshold, difference, ordered parity-combo, and color/value events,
   - the conditional task samples one-die selections with image-grounded denominator filters,
   - all tray labels use one deterministic font family sampled from the readout font pool and recorded in `render_spec.label_style.font`,
   - post-image noise stays at `apply_prob=0.15` because die colors and pip counts are semantic and must remain separable.
7. Trace contract:
   - `scene_ir.entities` includes `dice_tray` and `probability_die` entities,
   - `render_map.die_bboxes_px`, `render_map.tray_bboxes_px`, and `render_map.item_bboxes_px` store die and tray boxes,
   - `execution_trace` stores `query_id`, `scene_id`, `scene_variant`, dice specs, event description, favorable outcome count, total outcome count, reduced fraction answer, tray annotation role ids, and die-level calculation support ids,
   - conditional tasks also store denominator support ids.

## Spinner probability tasks
1. Active task ids:
   - `task_misc__spinner_probability__single_attribute_probability`
   - `task_misc__spinner_probability__multi_attribute_and_probability`
   - `task_misc__spinner_probability__multi_attribute_or_probability`
   - `task_misc__spinner_probability__spinner_pair_event_value`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - the sampled probability event is recorded as `query_id`.
3. Supported `scene_variant` values:
   - `spinner_clean`
   - `spinner_card`
   - `spinner_notebook`
4. Answer contract:
   - `answer_gt.type = string`,
   - answer values are reduced fraction strings such as `"3/8"`.
5. Annotation contract:
   - `annotation_gt.type = bbox_set`,
   - single-spinner annotation contains the full spinner panel box,
   - pair-spinner annotation contains the full Spinner A panel box followed by the full Spinner B panel box.
6. Scene contract:
   - spinner sectors are equal-probability sectors,
   - single-spinner sectors have a color and a shape marker,
   - pair-spinner sectors are color-only,
   - the single-spinner task samples color, shape, color-and-shape, and color-or-shape events,
   - the pair-spinner task samples independent two-spinner color events such as both target color, at least one target color, and same color.
7. Trace contract:
   - `scene_ir.entities` includes `spinner_panel`, `spinner_sector`, and `spinner_pointer` entities,
   - `render_map.sector_bboxes_px` and `render_map.item_bboxes_px` store sector and panel boxes,
   - `execution_trace` stores `query_id`, `scene_id`, `scene_variant`, sector specs, event description, favorable outcome count, total outcome count, reduced fraction answer, panel annotation item ids, and sector-level calculation support ids.

## Prompt contract for dice probability tasks
1. Bundle: `misc_probability_v0`
2. `scene_key`: `dice_probability`
3. Task keys:
   - `single_dice_probability_query`
   - `pair_dice_probability_query`
   - `conditional_dice_probability_query`
4. Public task ids:
   - `task_misc__dice_probability__single_attribute_probability`
   - `task_misc__dice_probability__single_threshold_probability`
   - `task_misc__dice_probability__pair_attribute_combo_probability`
   - `task_misc__dice_probability__pair_difference_probability`
   - `task_misc__dice_probability__pair_sum_probability`
   - `task_misc__dice_probability__pair_sum_threshold_probability`
   - `task_misc__dice_probability__dice_conditional_event_value`
5. Internal `query_key`: `single_parity_probability|single_threshold_probability|single_value_set_probability|single_color_and_value_probability|single_color_or_value_probability|pair_sum_probability|pair_sum_threshold_probability|pair_difference_probability|pair_parity_combo_probability|pair_color_value_combo_probability|conditional_value_property_given_color_probability|conditional_color_given_value_property_probability|conditional_color_given_value_set_probability`
6. Required slots:
   - scene: `object_description`
   - non-conditional probability query: `event_description`
   - conditional probability query: `given_description`, `event_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
7. Prompt wording must say selections are uniform over shown dice and must refer to visible top values, not rolling dice.
8. Public annotation uses role-keyed tray bboxes (`dice_tray` for single/conditional tasks, `tray_a` and `tray_b` for pair tasks).
9. Render metadata records the shared panel style, tray label font, reduced dice-readability noise policy, and `dice_visual_style.style_id` (`classic_rounded`, `flat_print`, `beveled_tokens`, `inked_pips`, `soft_shadow`).

## Prompt contract for spinner probability tasks
1. Bundle: `misc_probability_v0`
2. `scene_key`: `spinner_probability`
3. Task keys:
   - `single_spinner_probability_query`
   - `pair_spinner_probability_query`
4. Public task ids:
   - `task_misc__spinner_probability__single_attribute_probability`
   - `task_misc__spinner_probability__multi_attribute_and_probability`
   - `task_misc__spinner_probability__multi_attribute_or_probability`
   - `task_misc__spinner_probability__spinner_pair_event_value`
5. Internal `query_key`: `single_color_probability|single_shape_probability|single_color_and_shape_probability|single_color_or_shape_probability|pair_both_target_color_probability|pair_at_least_one_target_color_probability|pair_same_color_probability`
6. Required slots:
   - scene: `object_description`
   - probability query: `event_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
7. Prompt wording should state that sectors are equal-probability and ask for a reduced fraction answer.

## Music-staff notation tasks
1. Active task ids:
   - `task_misc__music_staff__interval_name_label`
   - `task_misc__music_staff__note_name_label`
   - `task_misc__music_staff__same_pitch_truth_label`
   - `task_misc__music_staff__transposed_pitch_truth_label`
   - `task_misc__music_staff__key_signature_label`
   - `task_misc__music_staff__scale_degree_function_label`
   - `task_misc__music_staff__scale_validation_truth_label`
   - `task_misc__music_staff__chord_harmony_label`
   - `task_misc__music_staff__dominant_chord_count`
   - `task_misc__music_staff__articulation_symbol_label`
   - `task_misc__music_staff__meter_type_label`
   - `task_misc__music_staff__time_signature_label`
   - `task_misc__music_staff__duration_equivalence_label`
   - `task_misc__music_staff__bar_count_value`
2. Public contract:
   - each task records branch metadata in `query_id`,
   - each task maps to scene id `music_staff`,
   - each public task id has its own stable notation contract; `query_id`
     records only narrow operand changes inside that contract.
   - active query ids cover note naming, interval naming, same-pitch checks,
     transposition checks, key-signature identification, scale-degree function,
     scale validation, chord/harmony labels, dominant-chord counting,
     articulation-mark labels, meter-type labels, time-signature labels,
     duration-equivalence option matching, and visible-bar counting.
3. Supported `scene_variant` values:
   - `engraved_sheet`
   - `exam_scan`
   - `notebook_staff`
4. Answer contract:
   - label tasks use string answers,
   - count tasks use integer answers,
   - duration-equivalence uses option-letter string answers.
5. Annotation contract:
   - prompt-facing annotation is `bbox_set`,
   - annotation stays local to marked notes, chords, key signatures, bars, time signatures, articulation marks, or option cards needed for the query.
6. The notation group keeps clef, pitch, rhythm, duration, key, chord, and bar metadata in trace; the verifier uses that metadata rather than OCR or pixel inference.

## Organic-structure notation tasks
1. Active task ids:
   - `task_misc__organic_structure__branch_point_count`
   - `task_misc__organic_structure__bond_order_count`
   - `task_misc__organic_structure__ring_size_count`
2. Public contract:
   - all organic-structure tasks map to scene id `organic_structure`,
   - `bond_order_count` records `target_bond_order=double|triple` and asks only for visible bond-order notation,
   - `branch_point_count` asks for skeletal vertices where three or more drawn bonds meet,
   - `ring_size_count` records `target_ring_size=5|6` and asks for visible pentagonal or hexagonal rings.
3. Supported `scene_variant` values:
   - `clean_worksheet`
   - `exam_scan`
   - `notebook_problem`
4. Answer contract:
   - `answer_gt.type = integer`,
   - bond-order values count visible bonds whose rendered order matches the requested target bond order,
   - branch-point values count line-angle vertices with topological degree at least three,
   - ring-size values count visible separated rings whose polygon has the requested vertex count,
   - v1 answer support is `1..4` for bond order, `0..4` for branch points, and `0..4` for ring-size counts.
5. Annotation contract:
   - bond-order prompt-facing annotation is `point_pair_set`,
   - bond-order annotation contains one endpoint point-pair for every matching bond,
   - each point-pair marks the semantic bond endpoints, not every parallel stroke in a double/triple bond,
   - branch-point prompt-facing annotation is `point_set`,
   - branch-point annotation contains one center point for every branch vertex and is empty for answer `0`,
   - ring-size prompt-facing annotation is `bbox_set`,
   - ring-size annotation contains one bounding box around every matching ring and is empty for answer `0`,
   - bond bboxes may remain render/debug metadata but are not the public annotation contract.
6. The organic-structure scene is notation-first but enforces basic reusable line-angle constraints:
   - scaffold metadata records the sampled chain/ring family,
   - carbon valence is kept at or below four,
   - triple-bond atoms are linear and unbranched,
   - branch vertices keep a minimum incident-bond angle,
   - pentagon/hexagon ring scaffolds and branches are sampled from curated geometry rather than arbitrary graph layouts,
   - ring-size scaffolds use separated rings connected by ordinary single bonds rather than fused rings,
   - atom/group letters are not rendered for these tasks,
   - implicit-carbon totals are not queried,
   - no molecular formula, IUPAC naming, stereochemistry, reaction, or product reasoning is part of this contract.

## Braille-cell notation tasks
1. Active task ids:
   - `task_misc__braille_cell__raised_dot_count`
   - `task_misc__braille_cell__matching_pattern_label`
2. Public contract:
   - all Braille tasks map to scene id `braille_cell`,
   - `raised_dot_count` asks for the number of raised dots in the marked target cell,
   - `matching_pattern_label` shows one reference cell and six labeled visual option cells, then asks which option matches the reference pattern.
3. Supported `scene_variant` values:
   - `clean_card`
   - `notebook_card`
   - `exam_scan`
4. Answer contract:
   - raised-dot count answers use `answer_gt.type = integer` with support `1..6`,
   - matching-pattern answers use `answer_gt.type = string` and answer labels `A..F`.
5. Annotation contract:
   - raised-dot count prompt-facing annotation is `point_set`,
   - raised-dot annotation contains one center point for every raised dot in the marked target cell,
   - matching-pattern prompt-facing annotation is `keyed_bbox_map`,
   - matching-pattern annotation uses keys `reference_cell` and `selected_option`.
6. Scene contract:
   - every Braille cell is rendered as a visible 2 x 3 dot grid,
   - filled dark dots are semantic raised dots,
   - faint empty-dot guides are render scaffolding and are not counted,
   - matching options are visual cells in the image, not prompt-only answer choices.

## Boolean logic-gate notation tasks
1. Active task ids:
   - `task_misc__logic_gate_circuit__output_value_count`
   - `task_misc__logic_gate_circuit__satisfying_assignment_label`
2. Public contract:
   - all logic-gate tasks map to scene id `logic_gate_circuit`,
   - output-value count shows six independent circuits with visible input values and hidden final output values, then asks how many circuits evaluate to `0` or `1`,
   - satisfying-assignment label shows one source circuit and six visual assignment-option rows, then asks which option makes the final output `0` or `1`.
3. Supported gate symbols:
   - `AND`
   - `OR`
   - `NOT`
   - `XOR`
   - `NAND`
   - `NOR`
4. Supported `scene_variant` values:
   - `clean_worksheet`
   - `notebook_problem`
   - `exam_scan`
5. Answer contract:
   - output-value count answers use `answer_gt.type = integer` with support `0..6`,
   - satisfying-assignment answers use `answer_gt.type = option_letter` with labels `A..F`.
6. Annotation contract:
   - output-value count prompt-facing annotation is `point_set`,
   - output-value annotation contains the center point of every final `OUT` node matching the queried output value,
   - satisfying-assignment prompt-facing annotation is `keyed_bbox_map`,
   - satisfying-assignment annotation uses keys `source_circuit` and `selected_option`.
7. Scene contract:
   - input values are visible for count tasks,
   - assignment tasks show input-variable names in the source circuit and all candidate values in the option table,
   - final output values are not printed in the image,
   - option assignments are visual rows in the image, not prompt-only answer choices.

## Prompt contract for organic-structure notation tasks
1. Bundle: `misc_v0`
2. `scene_key`: `organic_structure`
3. `task_key`: `organic_structure_bond_order_count`, `organic_structure_branch_point_count`, or `organic_structure_ring_size_count`
4. Query keys:
   - `bond_order_count`
   - `branch_point_count`
   - `ring_size_count`
5. Required slots:
   - scene: `object_description`
   - query: `target_bond_order` only for `bond_order_count`
   - query: `target_ring_name` only for `ring_size_count`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Prompt wording should say visible double/triple bonds for bond-order counts, define branch points as vertices where three or more bonds meet for branch-point counts, ask for pentagonal or hexagonal rings for ring-size counts, and should not ask for implicit-carbon totals or chemical identity.

## Prompt contract for Braille-cell notation tasks
1. Bundle: `misc_v0`
2. `scene_key`: `braille_cell`
3. `task_key`: `braille_raised_dot_count` or `braille_matching_pattern_label`
4. Query keys:
   - `raised_dot_count`
   - `matching_pattern_label`
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Prompt wording should ask for raised dots or matching raised-dot patterns and should not require knowing literary Braille letters.

## Prompt contract for Boolean logic-gate notation tasks
1. Bundle: `misc_v0`
2. `scene_key`: `logic_gate_circuit`
3. `task_key`: `logic_gate_output_value_count` or `logic_gate_satisfying_assignment_label`
4. Query keys:
   - `output_one_count`
   - `output_zero_count`
   - `assignment_outputs_one_label`
   - `assignment_outputs_zero_label`
5. Required slots:
   - scene: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Prompt wording should ask from visible gate labels, wires, and input/assignment values; it should not rely on hidden output values.

## Prompt contract for music-staff notation tasks
1. Bundle: `misc_v0`
2. `scene_key`: `music_staff`
3. `task_key`: `music_notation_query`
4. Query keys match the public `query_id` values in the active task docs and `configs/domains/misc/notation.yaml`.
5. Required slots:
   - scene: `object_description`
   - query-specific notation slots when declared by the prompt bundle
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. Prompt wording should ask from the visible staff notation and avoid exposing hidden symbolic metadata.

## Visual policy
1. Misc tasks use the same light solid background baseline as the other clean synthetic domains.
2. Logic-grid winning option panels, spatial fold-result winning option images, polyomino/overlay winning option panels, cube/voxel visible regions, solid-view query-grid cells, and topology counted items should stay visually salient relative to the other boxes.

## Determinism + review
1. Deterministic generation/rendering from `instance_seed`.
2. `query_id` and `scene_variant` are sampled independently at the task policy level.
3. No semantic auto-relaxation: every generated misc instance has exactly one valid answer under its declared answer type.
4. Review/sample overlays should use the recorded bbox/point maps (`render_map.slot_bboxes_px[query_slot_id]`, `render_map.box_bboxes_px[query_box_id]`, `render_map.cell_bboxes_px[query_cell_id]`, `render_map.item_bboxes_px[item_id]`, `render_map.option_panel_bboxes_px[correct_option_panel_id]`, `render_map.option_choice_bboxes_px[correct_option_choice_id]`, `render_map.structure_bboxes_px[structure_bbox_id]`, `render_map.component_bboxes_px[component_id]`, `render_map.crossing_bboxes_px[crossing_id]`, `render_map.piece_card_bboxes_px[piece_id]`, `render_map.point_bboxes_px[point_label]`, or `render_map.atom_points_px[atom_id]`) for the prompt-facing witness. Maze shortest-path overlays use ordered centers from `projected_annotation.pixel_point_sequence`.

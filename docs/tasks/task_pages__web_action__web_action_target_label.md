# `task_pages__web_action__web_action_target_label`

## Contract
1. Domain: `pages`
2. Task group: `relation`
3. Task id: `task_pages__web_action__web_action_target_label`
4. Objective: identify the labeled web control that satisfies a visible action instruction by using a cue-to-key guide on a browser-like page.
5. Answer type: `option_letter`
6. Evidence type: ordered `bbox_set`

## Variants
1. `click_target_label`: choose a clickable button/link control for the item card whose visible category/status pair matches the instruction, after matching the instruction cue to the guide key.
2. `type_field_label`: choose the input field matching a named form section and guide key.
3. `select_option_label`: choose the option chip matching a named option group and guide key.

## Scene
1. The screen renders a synthetic browser page with URL chrome, site navigation, an action-instruction banner, a visible cue-to-key guide, and candidate labels on targetable controls.
2. `scene_variant`: `shop_catalog|travel_booking|support_center|learning_portal|finance_portal|content_cms`
3. `style_variant`: `standard|compact|contrast|cool|warm|sage`
4. Click scenes sample `4..6` item cards and `3..4` actions per card; each card has a unique visible category/status pair used by the instruction instead of the item title.
5. Type-field scenes sample `3..4` sections and `3..4` fields per section.
6. Select-option scenes sample `3..4` option groups and `3..4` options per group.
7. Every candidate target control has a visible candidate-label badge.

## Answer And Evidence
1. Answer is the candidate label of the target web control.
2. Evidence contains four boxes in order: the instruction banner bbox, the matching guide-card bbox, the supporting page context bbox, then the target control bbox.
3. Candidate-label badge bboxes are trace metadata only; prompt-facing evidence uses full support/control bboxes.

## Prompt
1. `prompt_bundle_id`: `pages_relation_v0`
2. `scene_key`: `gui_web_action_targets`
3. `task_key`: `web_action_query`
4. Both answer-only and answer-and-evidence modes provide task-specific JSON examples.

## Determinism
1. Generation is deterministic for `instance_seed` plus params.
2. seeded sampling balances query ids, scene variants, style variants, target controls, and answer-label support.
3. The answer and evidence come from the same symbolic control/support trace.

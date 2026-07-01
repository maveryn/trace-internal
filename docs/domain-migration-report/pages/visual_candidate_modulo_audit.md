# Visual Candidate-Set Modulo Audit

This report audits modulo use around visual attributes such as colors, styles, labels, shapes, themes, symbols, and option layouts. Random candidate-set selection should use RNG sampling from an explicit support or range. Modulo is acceptable only for deterministic assignment from an already-selected list or for intentional repeat cycling.

## Summary

- Total visual modulo sites: 114
- Random candidate selection needs refactor: 26
- Sampling-time assignment needs review: 45
- Needs manual review: 20
- Likely safe deterministic assignment: 23

## Random Candidate Selection Needs Refactor

| File | Line | Reason | Snippet |
| --- | ---: | --- | --- |
| `trace/tasks/pages/calendar/shared/rendering.py` | 86 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `resolve_selection_index(` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 478 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `resolve_selection_index(` |
| `trace/tasks/pages/calendar_event_grid/shared/rendering.py` | 68 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `index = resolve_selection_index(` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 168 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `index = resolve_selection_index(` |
| `trace/tasks/pages/concept_map/ordered_child_label.py` | 68 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `task_params["layout_variant"] = SCENE_VARIANTS[abs(int(instance_seed)) % len(SCENE_VARIANTS)]` |
| `trace/tasks/pages/concept_map/shared/rendering.py` | 220 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `branch_color = branch_fills[int(branch_index) % len(branch_fills)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 84 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `profile = NODE_SHAPE_PROFILES[abs(int(instance_seed)) % len(NODE_SHAPE_PROFILES)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 105 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `child_offset = abs(int(instance_seed // 17)) % len(CHILD_NODE_SHAPES)` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 107 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `branch_shape = branch_cycle[(branch_index + abs(int(instance_seed))) % len(branch_cycle)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 112 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `child["shape"] = CHILD_NODE_SHAPES[(branch_index + child_index + child_offset) % len(CHILD_NODE_SHAPES)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 300 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `forced_marker = MARKERS[abs(int(sampling_index)) % len(MARKERS)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 346 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `marker_ids.append(str(MARKERS[(branch_index + child_index + abs(int(instance_seed))) % len(MARKERS)]["marker_id"]))` |
| `trace/tasks/pages/hero_callout_infographic/_lifecycle.py` | 319 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `offset = (int(callout_index) * 7 + int(field_index) * 13 + int(rng.randrange(len(values)))) % len(values)` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 109 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `field_index = resolve_selection_index(` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 274 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `field_index = resolve_selection_index(` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 695 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `item_name = f"{_ITEM_STEMS[int(global_index) % len(_ITEM_STEMS)]}-{100 + ((int(instance_seed) + int(global_index) * 17) % 900)}"` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 513 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:overlap_event_count") % len(feasible_event_counts))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 726 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:maximum_compatible_set") % len(feasible_support))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 945 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:day_label") % len(day_label_support))` |
| `trace/tasks/pages/schema/_lifecycle.py` | 1177 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `int(abs(int(answer_index)) + rng.randrange(max(1, len(low_overlap_candidates)))) % len(low_overlap_candidates)` |
| `trace/tasks/pages/schema/_lifecycle.py` | 1233 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `int(abs(int(answer_index)) + rng.randrange(max(1, len(pool)))) % len(pool)` |
| `trace/tasks/pages/schema/join_path_length_value.py` | 51 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `index = int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.context")) % len(context_ids)` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 205 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `color = _PALETTE[(label_index + int(rng.randrange(len(_PALETTE)))) % len(_PALETTE)]` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 209 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `icon_kind = _ICON_KINDS[(label_index + int(rng.randrange(len(_ICON_KINDS)))) % len(_ICON_KINDS)]` |
| `trace/tasks/pages/web_action/_lifecycle.py` | 676 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `index = _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"instruction.{control_family_key}") % len(templates)` |
| `trace/tasks/pages/web_action/_lifecycle.py` | 860 | visual candidate or attribute is selected with seed/hash/cursor/RNG plus modulo | `target_index = _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"target.{prompt_key}") % len(coded_controls)` |

## Sampling-Time Assignment Needs Review

| File | Line | Reason | Snippet |
| --- | ---: | --- | --- |
| `trace/tasks/pages/calendar/shared/sampling.py` | 473 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `% len(feasible_counts)` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 483 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `% len(interval_options)` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 130 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `return str(tuple(values)[int(index) % len(values)]), dict(probabilities)` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 148 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `return int(support[int(index) % len(support)]), uniform_probability(support)` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 173 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `return int(support[int(index) % len(support)]), uniform_probability(support)` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 213 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `return tuple(int(value) for value in CHIP_FILL_PALETTE[int(index) % len(CHIP_FILL_PALETTE)])` |
| `trace/tasks/pages/category_grid/shared/sampling.py` | 175 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `accent_rgb=tuple(int(value) for value in ACCENTS[(int(category_index) + int(accent_offset)) % len(ACCENTS)]),` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 296 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `selected_branch_items = [branch_items[(branch_offset + idx) % len(branch_items)] for idx in range(branch_count)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 648 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `branch = eligible[abs(int(answer_index)) % len(eligible)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 653 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `rank = int(allowed_ranks[abs(int(answer_index)) % len(allowed_ranks)])` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 682 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `branch = eligible[abs(int(answer_index)) % len(eligible)]` |
| `trace/tasks/pages/hero_callout_infographic/_lifecycle.py` | 340 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `accent_rgb=_ACCENTS[int(callout_index) % len(_ACCENTS)],` |
| `trace/tasks/pages/instruction_panel/_lifecycle.py` | 294 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `accent = _CONTROL_ACCENTS[(int(index) + int(color_offset)) % len(_CONTROL_ACCENTS)]` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 83 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `) % len(candidates)` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 135 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `) % len(candidates)` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 247 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `display_text=str(_NAV_COMMAND_SYMBOLS[int(command_index) % len(_NAV_COMMAND_SYMBOLS)]),` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 264 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `display_text=str(_SIDEBAR_ITEM_SYMBOLS[int(item_index) % len(_SIDEBAR_ITEM_SYMBOLS)]),` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 282 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `display_text=str(_NAV_COMMAND_SYMBOLS[int(command_index) % len(_NAV_COMMAND_SYMBOLS)]),` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 406 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `) % len(controls_without_labels)` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 417 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `% len(candidate_label_pool)` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 257 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `label = labels[index % len(labels)]` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 261 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `label = labels[9 % len(labels)]` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 335 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `label = str(extra_labels[extra_idx % len(extra_labels)] if extra_labels else f"Step {extra_idx + 1}")` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 431 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `"label": str(labels[index % len(labels)]),` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 113 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `) % len(field_labels)` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 207 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `accent_rgb=ACCENTS[(int(index) + int(color_offset)) % len(ACCENTS)],` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 278 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `) % len(field_labels)` |
| `trace/tasks/pages/schema/_lifecycle.py` | 554 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `cardinality_kind = _CARDINALITY_ORDER[int(rel_index) % len(_CARDINALITY_ORDER)]` |
| `trace/tasks/pages/schema/_lifecycle.py` | 1228 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `target_kind = str(_CARDINALITY_ORDER[abs(int(answer_index)) % len(_CARDINALITY_ORDER)])` |
| `trace/tasks/pages/sectioned_infographic/_lifecycle.py` | 338 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `marker = _BULLET_MARKS[(int(marker_offset) + int(item_index)) % len(_BULLET_MARKS)]` |
| `trace/tasks/pages/sectioned_infographic/_lifecycle.py` | 351 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `accent_rgb=tuple(int(value) for value in _ACCENTS[(int(section_index) + int(accent_offset)) % len(_ACCENTS)]),` |
| `trace/tasks/pages/step_list/_lifecycle.py` | 171 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `selected = int(support[int(index) % len(support)])` |
| `trace/tasks/pages/step_list/_lifecycle.py` | 423 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `accent = _CARD_PALETTE[(int(index) + int(color_offset)) % len(_CARD_PALETTE)]` |
| `trace/tasks/pages/web_action/_lifecycle.py` | 868 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `% len(candidate_label_pool)` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 501 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `display_text=str(_ACTION_SYMBOLS[int(action_index) % len(_ACTION_SYMBOLS)]),` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 506 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `code_label=str(_GUIDE_CODES[int(action_index) % len(_GUIDE_CODES)]),` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 571 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `) % len(controls_without_labels)` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 588 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `% len(candidate_label_pool)` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 630 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `) % len(instruction_templates)` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 794 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `fill = _ACCENT_FILLS[int(context_index) % len(_ACCENT_FILLS)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 795 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `outline = _ACCENT_LINES[int(context_index) % len(_ACCENT_LINES)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 834 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `fill = _ACCENT_FILLS[int(action_index) % len(_ACCENT_FILLS)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 835 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `outline = _ACCENT_LINES[int(action_index) % len(_ACCENT_LINES)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 890 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `fill = _ACCENT_FILLS[int(action_index) % len(_ACCENT_FILLS)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 891 | sampling code assigns visual attributes by index/cycle; verify candidate set is sampled first | `outline = _ACCENT_LINES[int(action_index) % len(_ACCENT_LINES)]` |

## Needs Manual Review

| File | Line | Reason | Snippet |
| --- | ---: | --- | --- |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 50 | visual modulo found, but candidate-set vs assignment role is unclear | `text = str(paragraph_phrases[int(index) % len(paragraph_phrases)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 66 | visual modulo found, but candidate-set vs assignment role is unclear | `kind = str(kinds[int(index) % len(kinds)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 69 | visual modulo found, but candidate-set vs assignment role is unclear | `text = str(note_phrases[int(note_cursor) % len(note_phrases)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 77 | visual modulo found, but candidate-set vs assignment role is unclear | `placement_region=str(placement_regions[int(index) % len(placement_regions)]),` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 231 | visual modulo found, but candidate-set vs assignment role is unclear | `module_kind = str(kinds[int(module_index) % len(kinds)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 244 | visual modulo found, but candidate-set vs assignment role is unclear | `label = str(field_banks[(bank_offset + field_index) % len(field_banks)][0])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 295 | visual modulo found, but candidate-set vs assignment role is unclear | `accent_rgb=tuple(int(value) for value in _ACCENTS[int(module_index) % len(_ACCENTS)]),` |
| `trace/tasks/pages/schema/join_path_length_value.py` | 56 | visual modulo found, but candidate-set vs assignment role is unclear | `return str(_RELATION_LABELS[int(index) % len(_RELATION_LABELS)])` |
| `trace/tasks/pages/shared/diagram/hierarchy_common.py` | 472 | visual modulo found, but candidate-set vs assignment role is unclear | `% len(_TEMPLATES)` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 207 | visual modulo found, but candidate-set vs assignment role is unclear | `icon_kind = _ICON_KINDS[(int(local_index) + int(repeated_icon_offset)) % len(_ICON_KINDS)]` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 612 | visual modulo found, but candidate-set vs assignment role is unclear | `) % len(eligible_sections)` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 361 | visual modulo found, but candidate-set vs assignment role is unclear | `section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.08)` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 365 | visual modulo found, but candidate-set vs assignment role is unclear | `fill=_PALETTE[section_index % len(_PALETTE)],` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 478 | visual modulo found, but candidate-set vs assignment role is unclear | `section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.07)` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 487 | visual modulo found, but candidate-set vs assignment role is unclear | `outline=_blend_rgb(_PALETTE[section_index % len(_PALETTE)], page_outline, 0.45),` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 514 | visual modulo found, but candidate-set vs assignment role is unclear | `fill=_blend_rgb((255, 255, 255), _PALETTE[section_index % len(_PALETTE)], 0.05),` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 515 | visual modulo found, but candidate-set vs assignment role is unclear | `outline=_blend_rgb(page_outline, _PALETTE[section_index % len(_PALETTE)], 0.22),` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 543 | visual modulo found, but candidate-set vs assignment role is unclear | `slot_col, slot_row_inner = ring_slot_order[int(slot_indices[int(local_index) % len(slot_indices)])]` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 620 | visual modulo found, but candidate-set vs assignment role is unclear | `section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.08)` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 691 | visual modulo found, but candidate-set vs assignment role is unclear | `section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.06)` |

## Likely Safe Deterministic Assignment

| File | Line | Reason | Snippet |
| --- | ---: | --- | --- |
| `trace/core/review_overlays.py` | 282 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 290 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 300 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 309 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 329 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 336 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 345 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 350 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 353 | render/review code cycles through an already-selected palette or repeated style list | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/tasks/pages/calendar/shared/rendering.py` | 91 | render/review code cycles through an already-selected palette or repeated style list | `% len(GENERIC_TITLE_TEXTS)` |
| `trace/tasks/pages/calendar_event_grid/shared/rendering.py` | 73 | render/review code cycles through an already-selected palette or repeated style list | `return str(GENERIC_TITLE_TEXTS[int(index) % len(GENERIC_TITLE_TEXTS)]), {"mode": "generic"}` |
| `trace/tasks/pages/map/shared/rendering.py` | 309 | render/review code cycles through an already-selected palette or repeated style list | `fill = ZONE_FILLS[index % len(ZONE_FILLS)]` |
| `trace/tasks/pages/mixed_infographic_page/shared/rendering.py` | 138 | render/review code cycles through an already-selected palette or repeated style list | `str(module.module_id): str(title_families[int(index) % len(title_families)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/rendering.py` | 358 | render/review code cycles through an already-selected palette or repeated style list | `fill = tuple(int(value) for value in colors[int(index) % len(colors)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/rendering.py` | 508 | render/review code cycles through an already-selected palette or repeated style list | `accent = tuple(int(value) for value in accent_cycle[int(index) % len(accent_cycle)])` |
| `trace/tasks/pages/process_flow/shared/rendering.py` | 385 | render/review code cycles through an already-selected palette or repeated style list | `route_offset = route_offsets[int(edge_index) % len(route_offsets)]` |
| `trace/tasks/pages/process_flow/shared/rendering.py` | 505 | render/review code cycles through an already-selected palette or repeated style list | `fill = tuple(int(value) for value in lane_fills[index % len(lane_fills)])` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 696 | render/review code cycles through an already-selected palette or repeated style list | `type_label = str(type_label_pool[(int(global_index) + int(section_index)) % len(type_label_pool)])` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 697 | render/review code cycles through an already-selected palette or repeated style list | `status_label = str(status_label_pool[(int(global_index) + int(order_in_section)) % len(status_label_pool)])` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 698 | render/review code cycles through an already-selected palette or repeated style list | `action_label = str(action_label_pool[(int(global_index) + int(section_index)) % len(action_label_pool)])` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 708 | render/review code cycles through an already-selected palette or repeated style list | `status_label = non_target_statuses[int(global_index) % len(non_target_statuses)]` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 723 | render/review code cycles through an already-selected palette or repeated style list | `type_label = non_target_types[int(global_index) % len(non_target_types)]` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 728 | render/review code cycles through an already-selected palette or repeated style list | `action_label = non_target_actions[int(global_index) % len(non_target_actions)]` |

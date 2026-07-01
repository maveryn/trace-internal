# Semantic Sampling Modulo Audit: First Pass

This report flags source patterns where modulo/index cycling may be standing in for semantic random sampling. Task random sampling should draw from an explicit support or bounded range with uniform or weighted probabilities. It is a static first pass; each refactor site still needs source-level confirmation before editing.

## Summary

- Raw line findings: 178
- Grouped selection sites: 153
- Needs refactor: 79
- Needs manual review: 3
- Review harness stratification / round-robin: 1
- Allowed deterministic visual/layout enumeration: 70

## Needs Refactor

| File | Lines | Kind | Raw Lines | Reason | Snippets |
| --- | ---: | --- | ---: | --- | --- |
| `trace/tasks/pages/calendar/shared/sampling.py` | 188-193 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(year_support)` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 198 | resolve_selection_index_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 363-368 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(target_support)` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 383-388 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(distractor_support)` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 468-473 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(feasible_counts)` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 478-483 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(interval_options)` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 533-538 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(feasible)` |
| `trace/tasks/pages/calendar/shared/sampling.py` | 573-578 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(feasible_pairs)` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 125-130 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(<br>return str(tuple(values)[int(index) % len(values)]), dict(probabilities)` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 143-148 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(<br>return int(support[int(index) % len(support)]), uniform_probability(support)` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 168-173 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(<br>return int(support[int(index) % len(support)]), uniform_probability(support)` |
| `trace/tasks/pages/concept_map/ordered_child_label.py` | 68 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `task_params["layout_variant"] = SCENE_VARIANTS[abs(int(instance_seed)) % len(SCENE_VARIANTS)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 154 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `return int(eligible[abs(int(answer_index)) % len(eligible)]), int(target)` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 296 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `selected_branch_items = [branch_items[(branch_offset + idx) % len(branch_items)] for idx in range(branch_count)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 300 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `forced_marker = MARKERS[abs(int(sampling_index)) % len(MARKERS)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 648 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `branch = eligible[abs(int(answer_index)) % len(eligible)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 653 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `rank = int(allowed_ranks[abs(int(answer_index)) % len(allowed_ranks)])` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 682 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `branch = eligible[abs(int(answer_index)) % len(eligible)]` |
| `trace/tasks/pages/control_board/shared/sampling.py` | 253 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(answer_support)` |
| `trace/tasks/pages/control_board/shared/sampling.py` | 263 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(group_names)` |
| `trace/tasks/pages/instruction_panel/_lifecycle.py` | 331-336 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(<br>return controls[int(index) % len(controls)]` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 66 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `kind = str(kinds[int(index) % len(kinds)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 69 | cursor_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `text = str(note_phrases[int(note_cursor) % len(note_phrases)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 231 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `module_kind = str(kinds[int(module_index) % len(kinds)])` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 406 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `) % len(controls_without_labels)` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 417 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(candidate_label_pool)` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 279 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `next_index = (list(CONDITION_POOLS).index(tuple(cond_pair_a)) + 2) % len(CONDITION_POOLS)` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 109-113 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `field_index = resolve_selection_index(<br>) % len(field_labels)` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 274-278 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `field_index = resolve_selection_index(<br>) % len(field_labels)` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 287-292 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(cards)` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 358 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `lane_index = int(answer_lane_indices[int(index) % len(answer_lane_indices)])` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 513 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:overlap_event_count") % len(feasible_event_counts))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 526 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:overlap_answer_count") % len(feasible_answer_support))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 532 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:overlap_reference_duration") % len(reference_support))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 630 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:longer_event_count") % len(feasible_event_counts))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 636 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:longer_reference_duration") % len(reference_support))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 645 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:longer_answer_count") % len(feasible_answer_support))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 726 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:maximum_compatible_set") % len(feasible_support))` |
| `trace/tasks/pages/schedule/_lifecycle.py` | 945 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(_resolve_support_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_NAMESPACE}:day_label") % len(day_label_support))` |
| `trace/tasks/pages/schema/_lifecycle.py` | 554 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `cardinality_kind = _CARDINALITY_ORDER[int(rel_index) % len(_CARDINALITY_ORDER)]` |
| `trace/tasks/pages/schema/_lifecycle.py` | 1177 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(abs(int(answer_index)) + rng.randrange(max(1, len(low_overlap_candidates)))) % len(low_overlap_candidates)` |
| `trace/tasks/pages/schema/_lifecycle.py` | 1228 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `target_kind = str(_CARDINALITY_ORDER[abs(int(answer_index)) % len(_CARDINALITY_ORDER)])` |
| `trace/tasks/pages/schema/_lifecycle.py` | 1233 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `int(abs(int(answer_index)) + rng.randrange(max(1, len(pool)))) % len(pool)` |
| `trace/tasks/pages/schema/field_role_count.py` | 65 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `table = dict(eligible[int(rng.randrange(max(1, len(eligible)))) % len(eligible)])` |
| `trace/tasks/pages/schema/join_path_length_value.py` | 41 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `return int(PATH_LENGTH_SUPPORT[int(abs(int(instance_seed))) % len(PATH_LENGTH_SUPPORT)])` |
| `trace/tasks/pages/schema/join_path_length_value.py` | 51 | hash_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.context")) % len(context_ids)` |
| `trace/tasks/pages/sectioned_infographic/_lifecycle.py` | 338 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `marker = _BULLET_MARKS[(int(marker_offset) + int(item_index)) % len(_BULLET_MARKS)]` |
| `trace/tasks/pages/shared/diagram/hierarchy_common.py` | 455 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `return int(values[int(selection_index + int(offset)) % len(values)])` |
| `trace/tasks/pages/shared/diagram/hierarchy_common.py` | 850 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `return tuple(feasible[int(selection_index) % len(feasible)])` |
| `trace/tasks/pages/shared/diagram/hierarchy_common.py` | 954-959 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(pool)` |
| `trace/tasks/pages/shared/diagram/hierarchy_common.py` | 1014-1019 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `resolve_selection_index(<br>% len(pair_pool)` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 103-104 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))<br>selected = int(support[int(index) % len(support)])` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 162-167 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(<br>selected = int(support[int(index) % len(support)])` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 180 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `second = alphabet[int(index) % len(alphabet)]` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 205 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `color = _PALETTE[(label_index + int(rng.randrange(len(_PALETTE)))) % len(_PALETTE)]` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 207 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `icon_kind = _ICON_KINDS[(int(local_index) + int(repeated_icon_offset)) % len(_ICON_KINDS)]` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 209 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `icon_kind = _ICON_KINDS[(label_index + int(rng.randrange(len(_ICON_KINDS)))) % len(_ICON_KINDS)]` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 393-398 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(<br>selected = str(_RANK_DIRECTIONS[int(index) % len(_RANK_DIRECTIONS)])` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 422-427 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(<br>selected = int(support[int(index) % len(support)])` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 608-612 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `section_index = resolve_selection_index(<br>) % len(eligible_sections)` |
| `trace/tasks/pages/step_list/_lifecycle.py` | 166-171 | resolve_selection_index_support_modulo | 2 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = resolve_selection_index(<br>selected = int(support[int(index) % len(support)])` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 335 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(year_support)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 410 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(feasible_answers)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 423 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(feasible_event_counts)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 436 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(left_index_support)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 454 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(feasible_answers)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 467 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(feasible_event_counts)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 480 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(left_outside_support)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 525 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(feasible_gaps)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 537 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(feasible_event_counts)` |
| `trace/tasks/pages/timeline/_lifecycle.py` | 550 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(start_day_support)` |
| `trace/tasks/pages/web_action/_lifecycle.py` | 676 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `index = _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"instruction.{control_family_key}") % len(templates)` |
| `trace/tasks/pages/web_action/_lifecycle.py` | 860 | seed_support_modulo | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `target_index = _support_selection_index(params, instance_seed=int(instance_seed), namespace=f"target.{prompt_key}") % len(coded_controls)` |
| `trace/tasks/pages/web_action/_lifecycle.py` | 868 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(candidate_label_pool)` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 571 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `) % len(controls_without_labels)` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 588 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `% len(candidate_label_pool)` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 630 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `) % len(instruction_templates)` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 890 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `fill = _ACCENT_FILLS[int(action_index) % len(_ACCENT_FILLS)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 891 | modulo_index | 1 | replace with explicit support/range sampling and uniform or weighted RNG draw | `outline = _ACCENT_LINES[int(action_index) % len(_ACCENT_LINES)]` |

## Needs Manual Review

| File | Lines | Kind | Raw Lines | Reason | Snippets |
| --- | ---: | --- | ---: | --- | --- |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 50 | modulo_index | 1 | manual source review needed before deciding whether this is random sampling | `text = str(paragraph_phrases[int(index) % len(paragraph_phrases)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 77 | modulo_index | 1 | manual source review needed before deciding whether this is random sampling | `placement_region=str(placement_regions[int(index) % len(placement_regions)]),` |
| `trace/tasks/pages/shared/infographic_metric_dataset.py` | 179 | modulo_index | 1 | manual source review needed before deciding whether this is random sampling | `first = alphabet[(int(index) // len(alphabet)) % len(alphabet)]` |

## Review Harness Stratification / Round-Robin

| File | Lines | Kind | Raw Lines | Reason | Snippets |
| --- | ---: | --- | ---: | --- | --- |
| `trace/core/task_review_sampling.py` | 188 | modulo_index | 1 | allowed only because this is explicit review/dataset coverage, not task randomness | `query_id_value = str(pending_query_ids[int(query_id_index) % len(pending_query_ids)])` |

## Allowed Deterministic Visual/Layout Enumeration

| File | Lines | Kind | Raw Lines | Reason | Snippets |
| --- | ---: | --- | ---: | --- | --- |
| `trace/core/review_overlays.py` | 282 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 290 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 300 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 309 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 329 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 336 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 345 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 350 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/core/review_overlays.py` | 353 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `color = _ANNOTATION_COLORS[idx % len(_ANNOTATION_COLORS)]` |
| `trace/tasks/pages/calendar/shared/rendering.py` | 86-91 | resolve_selection_index_support_modulo | 2 | allowed deterministic visual/layout/example enumeration | `resolve_selection_index(<br>% len(GENERIC_TITLE_TEXTS)` |
| `trace/tasks/pages/calendar_event_grid/shared/rendering.py` | 68-73 | resolve_selection_index_support_modulo | 2 | allowed deterministic visual/layout/example enumeration | `index = resolve_selection_index(<br>return str(GENERIC_TITLE_TEXTS[int(index) % len(GENERIC_TITLE_TEXTS)]), {"mode": "generic"}` |
| `trace/tasks/pages/calendar_event_grid/shared/sampling.py` | 213 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `return tuple(int(value) for value in CHIP_FILL_PALETTE[int(index) % len(CHIP_FILL_PALETTE)])` |
| `trace/tasks/pages/category_grid/shared/sampling.py` | 175 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `accent_rgb=tuple(int(value) for value in ACCENTS[(int(category_index) + int(accent_offset)) % len(ACCENTS)]),` |
| `trace/tasks/pages/concept_map/shared/rendering.py` | 220 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `branch_color = branch_fills[int(branch_index) % len(branch_fills)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 84 | seed_support_modulo | 1 | allowed deterministic visual/layout/example enumeration | `profile = NODE_SHAPE_PROFILES[abs(int(instance_seed)) % len(NODE_SHAPE_PROFILES)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 105 | seed_support_modulo | 1 | allowed deterministic visual/layout/example enumeration | `child_offset = abs(int(instance_seed // 17)) % len(CHILD_NODE_SHAPES)` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 107 | seed_support_modulo | 1 | allowed deterministic visual/layout/example enumeration | `branch_shape = branch_cycle[(branch_index + abs(int(instance_seed))) % len(branch_cycle)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 112 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `child["shape"] = CHILD_NODE_SHAPES[(branch_index + child_index + child_offset) % len(CHILD_NODE_SHAPES)]` |
| `trace/tasks/pages/concept_map/shared/sampling.py` | 346 | seed_support_modulo | 1 | allowed deterministic visual/layout/example enumeration | `marker_ids.append(str(MARKERS[(branch_index + child_index + abs(int(instance_seed))) % len(MARKERS)]["marker_id"]))` |
| `trace/tasks/pages/hero_callout_infographic/_lifecycle.py` | 319 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `offset = (int(callout_index) * 7 + int(field_index) * 13 + int(rng.randrange(len(values)))) % len(values)` |
| `trace/tasks/pages/hero_callout_infographic/_lifecycle.py` | 340 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `accent_rgb=_ACCENTS[int(callout_index) % len(_ACCENTS)],` |
| `trace/tasks/pages/instruction_panel/_lifecycle.py` | 294 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `accent = _CONTROL_ACCENTS[(int(index) + int(color_offset)) % len(_CONTROL_ACCENTS)]` |
| `trace/tasks/pages/map/shared/rendering.py` | 309 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = ZONE_FILLS[index % len(ZONE_FILLS)]` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 244 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `label = str(field_banks[(bank_offset + field_index) % len(field_banks)][0])` |
| `trace/tasks/pages/mixed_infographic_page/shared/assets.py` | 295 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `accent_rgb=tuple(int(value) for value in _ACCENTS[int(module_index) % len(_ACCENTS)]),` |
| `trace/tasks/pages/mixed_infographic_page/shared/layout.py` | 343 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `region = footer_regions[int(index) % len(footer_regions)]` |
| `trace/tasks/pages/mixed_infographic_page/shared/rendering.py` | 138 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `str(module.module_id): str(title_families[int(index) % len(title_families)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/rendering.py` | 358 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = tuple(int(value) for value in colors[int(index) % len(colors)])` |
| `trace/tasks/pages/mixed_infographic_page/shared/rendering.py` | 508 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `accent = tuple(int(value) for value in accent_cycle[int(index) % len(accent_cycle)])` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 83 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `) % len(candidates)` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 135 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `) % len(candidates)` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 247 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `display_text=str(_NAV_COMMAND_SYMBOLS[int(command_index) % len(_NAV_COMMAND_SYMBOLS)]),` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 264 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `display_text=str(_SIDEBAR_ITEM_SYMBOLS[int(item_index) % len(_SIDEBAR_ITEM_SYMBOLS)]),` |
| `trace/tasks/pages/navigation_flow/shared/sampling.py` | 282 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `display_text=str(_NAV_COMMAND_SYMBOLS[int(command_index) % len(_NAV_COMMAND_SYMBOLS)]),` |
| `trace/tasks/pages/process_flow/shared/rendering.py` | 385 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `route_offset = route_offsets[int(edge_index) % len(route_offsets)]` |
| `trace/tasks/pages/process_flow/shared/rendering.py` | 505 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = tuple(int(value) for value in lane_fills[index % len(lane_fills)])` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 257 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `label = labels[index % len(labels)]` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 261 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `label = labels[9 % len(labels)]` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 335 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `label = str(extra_labels[extra_idx % len(extra_labels)] if extra_labels else f"Step {extra_idx + 1}")` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 420 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `roles.append(str(middle_roles[(index + int(rng.randrange(0, len(middle_roles)))) % len(middle_roles)]))` |
| `trace/tasks/pages/process_flow/shared/sampling.py` | 431 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `"label": str(labels[index % len(labels)]),` |
| `trace/tasks/pages/profile_card_grid/shared/sampling.py` | 207 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `accent_rgb=ACCENTS[(int(index) + int(color_offset)) % len(ACCENTS)],` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 473 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `% len(support)` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 581 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `% len(answer_count_support)` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 695 | seed_support_modulo | 1 | allowed deterministic visual/layout/example enumeration | `item_name = f"{_ITEM_STEMS[int(global_index) % len(_ITEM_STEMS)]}-{100 + ((int(instance_seed) + int(global_index) * 17) % 900)}"` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 696 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `type_label = str(type_label_pool[(int(global_index) + int(section_index)) % len(type_label_pool)])` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 697 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `status_label = str(status_label_pool[(int(global_index) + int(order_in_section)) % len(status_label_pool)])` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 698 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `action_label = str(action_label_pool[(int(global_index) + int(section_index)) % len(action_label_pool)])` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 708 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `status_label = non_target_statuses[int(global_index) % len(non_target_statuses)]` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 723 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `type_label = non_target_types[int(global_index) % len(non_target_types)]` |
| `trace/tasks/pages/record_table/shared/rendering.py` | 728 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `action_label = non_target_actions[int(global_index) % len(non_target_actions)]` |
| `trace/tasks/pages/schema/join_path_length_value.py` | 56 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `return str(_RELATION_LABELS[int(index) % len(_RELATION_LABELS)])` |
| `trace/tasks/pages/sectioned_infographic/_lifecycle.py` | 351 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `accent_rgb=tuple(int(value) for value in _ACCENTS[(int(section_index) + int(accent_offset)) % len(_ACCENTS)]),` |
| `trace/tasks/pages/shared/diagram/hierarchy_common.py` | 467-472 | resolve_selection_index_support_modulo | 2 | allowed deterministic visual/layout/example enumeration | `resolve_selection_index(<br>% len(_TEMPLATES)` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 361 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.08)` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 365 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill=_PALETTE[section_index % len(_PALETTE)],` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 478 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.07)` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 487 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `outline=_blend_rgb(_PALETTE[section_index % len(_PALETTE)], page_outline, 0.45),` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 514 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill=_blend_rgb((255, 255, 255), _PALETTE[section_index % len(_PALETTE)], 0.05),` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 515 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `outline=_blend_rgb(page_outline, _PALETTE[section_index % len(_PALETTE)], 0.22),` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 543 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `slot_col, slot_row_inner = ring_slot_order[int(slot_indices[int(local_index) % len(slot_indices)])]` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 620 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.08)` |
| `trace/tasks/pages/shared/infographic_metric_rendering.py` | 691 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `section_fill_i = _blend_rgb(section_fill, _PALETTE[section_index % len(_PALETTE)], 0.06)` |
| `trace/tasks/pages/step_list/_lifecycle.py` | 423 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `accent = _CARD_PALETTE[(int(index) + int(color_offset)) % len(_CARD_PALETTE)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 501 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `display_text=str(_ACTION_SYMBOLS[int(action_index) % len(_ACTION_SYMBOLS)]),` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 506 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `code_label=str(_GUIDE_CODES[int(action_index) % len(_GUIDE_CODES)]),` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 794 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = _ACCENT_FILLS[int(context_index) % len(_ACCENT_FILLS)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 795 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `outline = _ACCENT_LINES[int(context_index) % len(_ACCENT_LINES)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 834 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `fill = _ACCENT_FILLS[int(action_index) % len(_ACCENT_FILLS)]` |
| `trace/tasks/pages/workspace/_lifecycle.py` | 835 | modulo_index | 1 | allowed deterministic visual/layout/example enumeration | `outline = _ACCENT_LINES[int(action_index) % len(_ACCENT_LINES)]` |

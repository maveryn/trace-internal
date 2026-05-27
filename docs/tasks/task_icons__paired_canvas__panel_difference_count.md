# `task_icons__paired_canvas__panel_difference_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `paired_canvas`
3. Task group: `counting`
4. Task id: `task_icons__paired_canvas__panel_difference_count`
5. Objective: count icons added to the Right panel or missing from the Right panel.

## 2) Scene + task contract
1. Entities/relations: two large icon panels labeled `Left` and `Right` with common icons plus panel-specific additions/removals.
2. Public `query_variant`: `default`.
3. Query id: `added_in_right_count|missing_from_right_count`.
4. Answer type: `answer_gt.type = integer`.
5. Evidence type: `evidence_gt.type = bbox_set`; added-icon queries box Right-panel icons, and missing-icon queries box Left-panel icons.
6. Unique-answer policy: common, added, and removed icons use distinct visual identities, so exact-match membership is unambiguous.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_counting_v0`
2. `scene_key`: `paired_canvas_counting`
3. `task_key`: `counting_query`
4. Answer+evidence JSON shape: `{"evidence":[[620,156,684,220],[834,338,902,406]],"answer":2}`
5. Prompt wording names the relevant panel for the active query branch.

## 4) Determinism + constraints
1. The common, added, and removed identity sets are recorded in trace metadata.
2. Evidence is computed from the panel that contains the visible witness icons.
3. Generation fails rather than relaxing exact-match or placement constraints.

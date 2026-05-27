# `task_icons__paired_canvas__panel_exact_match_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `paired_canvas`
3. Task group: `counting`
4. Task id: `task_icons__paired_canvas__panel_exact_match_count`
5. Objective: count Right-panel icons that exactly match at least one Left-panel icon.

## 2) Scene + task contract
1. Entities/relations: two large icon panels labeled `Left` and `Right`.
2. Branch metadata: `query_id`
3. Query id: `right_exact_match_count`.
4. Answer type: `answer_gt.type = integer`.
5. Evidence type: `evidence_gt.type = bbox_set` over every counted Right-panel icon.
6. Unique-answer policy: matching is exact over icon type, color, size, and rotation; right-side distractors use distinct sampled identities.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_counting_v0`
2. `scene_key`: `paired_canvas_counting`
3. `task_key`: `counting_query`
4. Answer+evidence JSON shape: `{"evidence":[[620,156,684,220],[834,338,902,406]],"answer":2}`
5. Prompt asks for Right-panel icons that exactly match a Left-panel icon.

## 4) Determinism + constraints
1. The sampled icon attributes, positions, and exact-match identities are recorded in trace metadata.
2. Evidence is computed from the same rendered Right-panel icons used to compute the answer.
3. Generation fails rather than relaxing placement, uniqueness, or exact-match constraints.

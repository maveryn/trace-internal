# `task_pages__map__navigation_label`

## 1) Identity
1. Domain: `pages`
2. Task group: `map`
3. Task id: `task_pages__map__navigation_label`
4. Objective: read one static printed map and return the exact visible landmark or zone label required by the query.

## 2) Scene + task contract
1. Supported `query_id` values:
   - `destination_after_directions`
   - `landmark_after_route_step`
2. Supported `scene_variant` values:
   - `campus_map`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_sequence`
5. Scene contract:
   - one rectangular printed campus/facility map is shown,
   - the map contains named zones, labeled landmarks, walking-path connections, a compass, and optional highlighted route segments,
   - landmark labels are unique within one image,
   - zone names are visible on the map and sampled from a broader support pool across instances,
   - the answer is the exact visible landmark or zone label requested by the prompt.
6. Generation guarantees:
   - `landmark_count` is always between `10` and `14`,
   - landmark cells form one connected path graph over a fixed grid-backed map layout,
   - direction queries follow adjacent path steps only,
   - highlighted-route queries use the visible highlighted route only,
   - the rendered map yields exactly one valid answer label.

## 3) Prompt contract
1. Bundle: `pages_map_v0`
2. `scene_key`: `printed_map`
3. `task_key`: `map_navigation_query`
4. `query_key`: one of `destination_after_directions|landmark_after_route_step`
5. Required slots:
   - scene: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/pages/map.yaml`,
   - deterministic bundle selection from `prompts/pages/map/pages_map_v0.json`,
   - task-local JSON examples keyed by the active map-query id.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is an exact visible landmark label; prompt-facing evidence is the ordered supporting route boxes.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_sequence`:
   - `destination_after_directions`: ordered landmark boxes from the start through the destination,
   - `landmark_after_route_step`: ordered landmark boxes from the highlighted-route start through the requested reached landmark.
2. `scene_ir.entities` stores:
   - `map_panel`
   - `map_title`
   - `printed_map`
   - `map_zone`
   - `map_zone_label`
   - `map_path_segment`
   - `map_highlighted_route_segment`
   - `map_landmark`
   - `map_landmark_label`
3. `render_map` includes:
   - `panel_bbox_px`
   - `title_bbox_px`
   - `map_bbox_px`
   - `landmark_bboxes_px`
   - `landmark_label_bboxes_px`
   - `zone_label_bboxes_px`
   - `path_bboxes_px`
   - `highlighted_route_bboxes_px`
4. `execution_trace` records:
   - `query_id`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `scene_title`
   - `question_text`
   - `grid_cols`
   - `grid_rows`
   - `landmark_count`
   - `answer_label`
   - `zone_specs`
   - `landmark_specs`
   - `path_specs`
   - `route_landmark_ids`
   - `highlighted_route_landmark_ids`
   - `evidence_bbox_ids`
   - `evidence_landmark_bbox_ids`
   - `evidence_zone_label_bbox_ids` as an empty list for the active route variants
5. `witness_symbolic` stores the supporting landmark ids, while `projected_evidence` stores the bbox sequence used by the verifier.

## 5) Visual policy
1. Background and post-image noise use the merged pages-domain visual defaults from `configs/domains/pages/base.yaml`.
2. Map scenes stay OCR-light:
   - short typed landmark labels,
   - short named zone labels,
   - visible path geometry,
   - a compass for direction queries,
   - no long paragraph text.
3. The first map scene variant is `campus_map`, a rectangular printed-map page with four broad named zones.
4. Evidence should stay on route landmarks or the queried landmark/zone label, not on the whole map or decorative panel.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `query_id` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact rendered landmark or zone label.
4. No semantic auto-relaxation.
5. If a sampled route cannot satisfy the requested step bounds, reject rather than silently changing the query contract.

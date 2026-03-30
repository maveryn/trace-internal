# `task_maps_region_association_label`

## 1) Identity
1. Domain: `maps`
2. Task group: `region`
3. Task id: `task_maps_region_association_label`
4. Objective: identify the labeled region that matches one legend-based category query on a stylized thematic map.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `max_category_region`
   - `min_category_region`
   - `matches_legend_bin`
2. Supported `scene_variant` values:
   - `map_strip`
   - `map_card`
   - `map_outline`
   - `region_map`
3. `answer_gt.type`: `option_letter`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one stylized choropleth-style map appears on the left,
   - one categorical legend appears on the right,
   - the hidden map geometry is a contiguous cell partition, but only the region boundaries are visible,
   - every region has one visible uppercase label,
   - the legend lists the ordered categories `Low`, `Moderate`, `High`, and `Very high`,
   - the answer is always one region label.
6. Generation guarantees:
   - the map uses `5..7` labeled regions,
   - the hidden partition grid defaults to `6..7` columns by `4..5` rows,
   - the legend palette uses four colors with Lab-space separation floor `ΔE*ab >= 60`,
   - `max_category_region` has exactly one region in the highest category,
   - `min_category_region` has exactly one region in the lowest category,
   - `matches_legend_bin` chooses a category that appears exactly once in the map.

## 3) Prompt contract
1. Bundle: `maps_region_v1`
2. `task_family_key`: `choropleth_region_map`
3. `task_key`: `region_association_query`
4. `task_variant_key`: one of `max_category_region|min_category_region|matches_legend_bin`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/maps/region.yaml`,
   - deterministic bundle selection from `prompts/maps/region/maps_region_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the region letter; prompt-facing evidence is the winning region bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is exactly one `bbox_set` item:
   - the bbox of the correct labeled region.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores:
   - `map_panel`
   - `map_region`
   - `map_region_cell`
   - `map_region_label`
   - `map_legend_panel`
   - `map_legend_entry`
   - `map_divider`
   - optional `map_compass` in the atlas-style `region_map` scene variant
4. `render_map` includes:
   - `region_bboxes_px`
   - `legend_entry_bboxes_px`
   - `map_bbox_px`
   - `legend_bbox_px`
   - `divider_bbox_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `grid_cols`
   - `grid_rows`
   - `region_count`
   - `category_count`
   - `category_labels`
   - `query_category_label`
   - `question_text`
   - `region_specs`
   - `legend_specs`
   - `answer_region_label`
   - `answer_region_id`
   - `answer_region_bbox_id`
   - `supporting_region_bbox_ids`
   - `color_min_distance`
   - `color_distance_space`
6. Prompt-facing evidence is projected from `answer_region_bbox_id`, not from legend entries.

## 5) Visual policy
1. Background and post-image noise use the merged maps-domain visual defaults from `configs/domains/maps/base.yaml`.
2. V1 map scenes use one stylized contiguous region partition rather than country-specific outlines, so later region/legend tasks can reuse the same topology without tying the domain to real geography.
3. Region boundaries remain visible while internal hidden-grid seams are suppressed, so the figure reads as a thematic map rather than a table or tile board.
4. The `region_map` scene variant reuses the same hidden region partition but renders it with atlas-style chrome: a water-colored map field, subtle graticule lines, and a north-arrow compass so the task family has a more recognizably map-native visual option without changing the answer/evidence contract.
5. Legend order is semantically meaningful and stable from low to high.
6. Color-bearing category palettes must be generated or validated through Lab-space separation, not hand-picked RGB guesses.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact region assignment and legend palette.
4. No semantic auto-relaxation.
5. Review overlays rely on the recorded region bbox projection, not on pixel-based region segmentation.

# `task_puzzles__pipe_flow__pipe_flow_repair_tile_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `pipe_flow`
3. Task group: `topology`
4. Task id: `task_puzzles__pipe_flow__pipe_flow_repair_tile_label`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id`: `flow_repair_tile_label`
3. Prompt asks for the labeled 2x2 pipe/conduit option that can be rotated to fill the black missing region and repair flow from the green start marker to the red triangular finish flag.
4. Internal variation:
   - `grid_size_variant`: `6x6|7x7|8x8|9x9|10x10`
   - `scene_variant`: `water_pipe|circuit_trace|industrial_conduit`
   - option labels: exactly six options `A..F`
   - rotations are allowed when testing whether an option fits.

## Answer And Evidence
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the capital-letter label on the correct 2x2 option panel.
3. `evidence_gt.type = bbox_set`
4. Evidence contains bboxes for the correct option panel and the black 2x2 missing-region.

## Trace Contract
1. `scene_ir.entities` includes one `pipe_flow_panel`, one `pipe_flow_missing_2x2_region`, one `pipe_flow_tile` per visible pipe/conduit tile, one `pipe_flow_start_marker`, one `pipe_flow_finish_flag`, and six `pipe_flow_option_panel` entities.
2. Internal `render_map.item_bboxes_px` contains all option panel ids and the missing-region id used for verifier projection.
3. Public review sidecars expose the projected pixel boxes through `evidence_gt` / `projected_evidence`; internal item ids may be sanitized from persisted `execution_trace`.
4. `execution_trace.tiles` records each visible tile's current openings, required path openings, and whether it belongs to the main path or an offshoot branch.
5. Offshoot branches are generated from the main path and terminate on a grid side; `execution_trace.branch_terminal_cells` records those side cells.
6. `execution_trace.option_specs` records the six 2x2 option pieces, records that rotation is allowed, and identifies the unique correct option under rotation.

## Prompt Contract
1. Bundle: `puzzles_topology_v0`
2. Scene key: `topology_pipe_flow_puzzle`
3. Task key: `pipe_flow_repair_query`
4. Query key: `flow_repair_tile_label`
5. Prompt wording should explain that flow passes through matching tile-edge openings, that options may be rotated before placement, and that exactly one 2x2 option fills the black gap to connect the green start marker to the red triangular finish flag.

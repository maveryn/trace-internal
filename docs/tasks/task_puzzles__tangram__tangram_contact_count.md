# `task_puzzles__tangram__tangram_contact_count`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__tangram__tangram_contact_count`
4. Scene id: `tangram`
5. Goal: count the marked tangram-style piece or pieces plus every unmarked piece touching them by sharing an edge.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `contact_count`
3. Answer type: `integer`
4. Evidence type: `bbox_set`
5. Evidence targets: marked piece bbox or bboxes followed by bboxes of all unmarked edge-touching pieces; every evidence box is counted
6. Scene variants: `tangram_square|tangram_diamond|tangram_tilted`

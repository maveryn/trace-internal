# `task_puzzles__tents__tents_valid_candidate_count`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles__tents__tents_valid_candidate_count`
4. Scene id: `tents`
5. Goal: count the labeled cells around the marked tree where a tent could legally be added.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `valid_candidate_count`
3. Grid size: `6x6..8x8`
4. Candidate cells: four labeled orthogonal neighbors of the marked tree
5. Answer type: `integer`
6. Answer range: `0..4`
7. Evidence type: `bbox_set`
8. Evidence target: marked tree followed by every legal labeled candidate cell; when the count is zero, the evidence contains only the marked tree
9. Scene variants: `tents_classic|tents_card|tents_blueprint`
10. Render palettes: `garden|autumn|lake|violet|slate`

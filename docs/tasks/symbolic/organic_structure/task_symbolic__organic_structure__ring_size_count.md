# `task_symbolic__organic_structure__ring_size_count`

## Contract
1. Domain: `symbolic`
2. Scene id: `organic_structure`
3. Scene: `notation`
4. Task id: `task_symbolic__organic_structure__ring_size_count`
5. Query id:
   - `ring_size_count`
6. Semantic parameter:
   - `target_ring_size`: `5` or `6`
   - prompts verbalize these as pentagonal or hexagonal rings.
7. Answer:
   - `answer_gt.type = integer`
   - answer support is `0..4`
   - count visible rings whose polygon has the requested vertex count.
8. Annotation:
   - `annotation_gt.type = bbox_set`
   - contains one bounding box around each matching ring
   - annotation is empty when the answer is `0`.

## Scene Constraints
1. The scene renders separated pentagonal and hexagonal rings connected by ordinary single bonds.
2. Fused-ring interpretation is intentionally out of scope for this task.
3. Atom/group letters, implicit-carbon totals, molecular identity, formulas, and chemistry naming are not queried.
4. Basic line-angle constraints are enforced: carbon valence at most four, no crossed bonds, and ring sizes limited to five and six.

## Trace Contract
1. `execution_trace.target_ring_size` records the requested ring size.
2. `execution_trace.matching_ring_item_ids` records the ring ids counted in the answer.
3. `execution_trace.rings` records each ring id, ring size, atom ids, atom indices, and target-ring membership.
4. `render_map.ring_bboxes_px` records ring bboxes used for annotation projection.
5. `projected_annotation.bbox_set` matches `annotation_gt.value`.

## Prompt Contract
1. Bundle: `symbolic_v0`
2. Scene key: `organic_structure`
3. Task key: `organic_structure_ring_size_count`
4. Query key: `ring_size_count`

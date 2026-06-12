# `task_symbolic__organic_structure__branch_point_count`

## Public Taxonomy
1. Domain: `symbolic`
2. Scene id: `organic_structure`
3. Scene: `notation`
4. Task id: `task_symbolic__organic_structure__branch_point_count`

## Query Contract
1. Query metadata: `query_id`
2. Supported `query_id` values:
   - `branch_point_count`
3. Prompts ask for the count of skeletal branch points.
4. A branch point is a line-angle vertex where three or more drawn bonds meet.
5. V1 answer support is `0..4`.
6. Internal variation includes unbranched chains, branched chains, ring side-chain scaffolds, and `clean_worksheet|exam_scan|notebook_problem` scene variants.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the number of line-angle vertices with topological degree at least three.
3. `annotation_gt.type = point_set`
4. Annotation contains one center point for every branch vertex.
5. The zero-answer case uses an empty annotation set.
6. Prompt-facing annotation excludes non-branch vertices, bonds, rings, panel marks, and annotations.

## Trace Contract
1. `execution_trace.organic_metadata` records the branch-point definition, scaffold id/family, and constraint policy.
2. `execution_trace.annotation_item_ids` and `execution_trace.branch_point_item_ids` record the atom ids used for point projection.
3. `render_map.atom_points_px` exposes atom-center points after final layout.
4. `execution_trace.atoms` records implicit line-angle atom vertices, degree, and branch-point status.
5. `execution_trace.bonds` records each drawn bond endpoint pair and order.
6. `execution_trace.organic_metadata.constraint_report` records valence, branch-point ids, minimum branch angle, ring-size, triple-linearity, and crossing-check metadata.

## Prompt Contract
1. Bundle: `symbolic_v0`
2. Scene key: `organic_structure`
3. Task key: `organic_structure_branch_point_count`
4. Query key: `branch_point_count`
5. Prompt wording must define branch points as vertices where three or more bonds meet. It must not ask for molecular formula, atom labels, implicit-carbon totals, stereochemistry, naming, or reaction reasoning.

## Determinism + Constraints
1. Deterministic generation and rendering from `instance_seed`.
2. Unique-answer policy: the answer is the exact count of rendered skeletal vertices with topological degree at least three.
3. Reject/resample conditions: generation fails rather than silently changing the semantic contract if the requested answer support cannot fit.
4. No-auto-relaxation guarantee: the task never changes answer bounds to force acceptance.
5. The reusable organic-structure scene grammar enforces basic line-angle plausibility:
   - carbon valence sum is at most four,
   - triple-bond atoms are linear and unbranched,
   - branch vertices keep a minimum incident-bond angle,
   - rings are curated pentagon/hexagon scaffolds,
   - nonadjacent bond segments do not cross.
6. The task remains notation-first and does not require identifying a real molecule.

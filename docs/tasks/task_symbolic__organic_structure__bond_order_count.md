# `task_symbolic__organic_structure__bond_order_count`

## Public Taxonomy
1. Domain: `symbolic`
2. Scene id: `organic_structure`
3. Scene: `notation`
4. Task id: `task_symbolic__organic_structure__bond_order_count`

## Query Contract
1. Query metadata: `query_id`
2. Supported `query_id` values:
   - `bond_order_count`
3. Prompts ask for the count of visible bonds matching a requested bond order.
4. Query argument axes:
   - `target_bond_order = double|triple`
5. V1 answer support is `1..4`.
6. Internal variation includes constrained skeletal chains, optional rings, branches, single bonds, double bonds, triple bonds, and `clean_worksheet|exam_scan|notebook_problem` scene variants.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the number of bonds whose rendered order matches `target_bond_order`.
3. `annotation_gt.type = point_pair_set`
4. Annotation contains one unordered endpoint point-pair for every matching bond.
5. Each point-pair marks the semantic bond endpoints, not every parallel stroke in a double/triple bond.
6. Bond bboxes may remain render/debug metadata, but prompt-facing annotation excludes vertices, rings, nonmatching bonds, panel marks, and annotations.

## Trace Contract
1. `execution_trace.organic_metadata` records the supported bond orders, scaffold id/family, and constraint policy.
2. `execution_trace.annotation_item_ids` records the rendered bond ids used for point-pair projection.
3. `render_map.bond_point_pairs_px` exposes bond endpoint pairs after final layout.
4. `execution_trace.bonds` records each bond endpoint pair and rendered order.
5. `execution_trace.atoms` records implicit line-angle atom vertices for downstream organic-structure tasks.
6. `execution_trace.organic_metadata.constraint_report` records valence, ring-size, triple-linearity, and crossing-check metadata.

## Prompt Contract
1. Bundle: `symbolic_v0`
2. Scene key: `organic_structure`
3. Task key: `organic_structure_bond_order_count`
4. Query key: `bond_order_count`
5. Prompt wording must ask for visible double or triple bond notation. It must not ask for molecular formula, atom labels, implicit-carbon counts, stereochemistry, naming, or reaction reasoning.

## Determinism + Constraints
1. Deterministic generation and rendering from `instance_seed`.
2. Unique-answer policy: `target_bond_order` is sampled explicitly, and the answer is the exact count of rendered bonds with that order.
3. Reject/resample conditions: generation fails rather than silently changing the semantic contract if the requested answer support cannot fit.
4. No-auto-relaxation guarantee: the task never changes target bond order or answer bounds to force acceptance.
5. The reusable organic-structure scene grammar enforces basic line-angle plausibility:
   - carbon valence sum is at most four,
   - triple-bond atoms are linear and unbranched,
   - rings are curated pentagon/hexagon scaffolds,
   - nonadjacent bond segments do not cross.
6. The task remains notation-first and does not require identifying a real molecule.

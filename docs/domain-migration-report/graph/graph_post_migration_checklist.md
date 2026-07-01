# Graph Post-Migration Checklist Issues

Audit date: 2026-06-27

Scope: `graph` domain only. This report records identified issues only.

Minimal provenance:

- Active graph tasks from `docs/ACTIVE_TASK_INVENTORY.md`: 60.
- Active graph scenes: 10.
- Scene migration status files: 10/10 scenes have `manual_code_audit_status.json`,
  `taxonomy_review_status.json`, and `migration_test_status.json` with
  `passed: true`; 0 scalar-annotation checklist misses.
- Review task folders under `review/task-reviews/graph`: 60 active, 0 missing,
  0 stale.
- Distribution reviews: 0 missing, 0 failing, 0 warning-bearing.
- `bbox_min_side_audit.md`: 60 tasks checked, 11 bbox-family runtime tasks,
  0 failing bbox tasks.
- `semantic_sampling_modulo_audit.md`: 0 needs-refactor and 0 manual-review
  semantic modulo sites.
- `visual_candidate_modulo_audit.md`: 0 random visual candidate modulo sites.
- `prompt_concision_audit.md`: 190 rendered prompts, 60 tasks covered, 95
  observed query ids covered, 0 incomplete query ids or generation errors.
- `prompt_annotation_contracts/prompt_annotation_contract_audit.md`: 95
  sampled query ids, 95 samples, 0 issues.

## Open Issues

No open graph post-migration checklist issues are currently recorded in this report.

## Resolved

### GPH-006 - Graph task docs used compact Program Contract sections

Severity: required_fix

Category: task docs / taxonomy review

Resolved on: 2026-07-01

Fix:

- Normalized all `60` graph task docs under `docs/tasks/graph/` so each
  `## Program Contract` section exposes:
  `Program:`, `Candidate set:`, `Operands:`, `Operation:`, `Output binding:`,
  `Annotation witnesses:`, and `Query ids:`.
- Used `scripts/normalize_reviewed_domain_program_contract_docs.py` to preserve
  each existing compact program expression and expand it into reviewable fields.
- This was docs-only; task code, configs, prompts, review artifacts, and solve
  rate were not changed.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 python -B scripts/normalize_reviewed_domain_program_contract_docs.py --check`
- Result: `reviewed-domain task docs scanned: 444`, `docs requiring normalization: 0`.
- Custom structural scan reports `graph docs 60`, `missing_any 0`, and no
  placeholder schema wording in normalized graph Program Contract sections.

### GPH-005 - Node-link annotation audit reported generation errors

Severity: required_fix

Category: generation

Resolved on: 2026-06-27

Scope:

- `task_graph__node_link__isolated_after_removal_count`
- `task_graph__node_link__reachable_count`
- `task_graph__node_link__degree_extremum_value`

Supporting artifact:

- `docs/domain-migration-report/graph/prompt_annotation_contracts/prompt_annotation_contract_audit.md`

Original issue:

- The refreshed prompt/annotation contract audit completed query-id coverage
  for all 60 graph tasks, but recorded generation errors for these two
  node-link tasks while collecting samples:
  `Generation errors while auditing task: {'RuntimeError': 3}`.
- Root cause:
  - `reachable_count` sampled `node_count` and source-excluding reachable count
    independently, allowing impossible pairs such as a requested reachable count
    larger than the available non-source nodes.
  - `isolated_after_removal_count` sampled impossible node-count/target-count
    pairs and then indexed an empty feasible-support tuple.
  - During full scene review regeneration, `degree_extremum_value` also exposed
    a replay mismatch: review params store public actual degree values, while
    the task wrapper expected an internal support index.

Fix:

- Added task-local feasible node-count selection for `reachable_count` and
  `isolated_after_removal_count`, preserving the sampled answer target while
  choosing the nearest feasible graph size.
- Restored zero-answer support and directed/undirected sampling for
  `isolated_after_removal_count`.
- Updated node-link trace export to record realized node counts, selected
  graph visual axes, resolved RGBs, removed-node metadata, and post-removal
  maps already present on samples.
- Added public-param normalization for `degree_extremum_value` so review replay
  treats `target_degree` as the actual public degree value and converts it to
  the internal support index.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_relation_reachable_count_tasks.py tests/test_graph_counting_isolated_node_count_after_node_removal_tasks.py`
  passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_node_link_visual_variants.py`
  passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_annotation_answer_consistency.py`
  passed.
- A 1000-seed sweep for `isolated_after_removal_count` and `reachable_count`
  produced 0 generation failures.
- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks "$TASKS" --samples-per-query-id 1 --output-dir docs/domain-migration-report/graph/prompt_annotation_contracts --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
  audited 60 tasks, 95 query ids, 95 samples, and found 0 issues.
- Regenerated the full `graph/node_link` scene review under
  `review/task-reviews` with 26 tasks and 2600 inspection rows.

### GPH-004 - Binary-tree prompts used an over-broad answer hint

Severity: required_fix

Category: prompt

Resolved on: 2026-06-27

Scope:

- `task_graph__binary_tree__bst_path_operation_label`
- `task_graph__binary_tree__child_structure_node_count`
- `task_graph__binary_tree__depth_level_node_count`
- `task_graph__binary_tree__heap_property_violation_label`
- `task_graph__binary_tree__local_relative_node_label`
- `task_graph__binary_tree__lowest_common_ancestor_label`
- `task_graph__binary_tree__traversal_kth_label`

Supporting artifact:

- `prompts/graph/binary_tree/graph_binary_tree_v1.json:315`
- `review/task-reviews/graph/binary_tree/task_graph__binary_tree__child_structure_node_count/data/two_child_node_count/0005.json`
- `review/task-reviews/graph/binary_tree/task_graph__binary_tree__local_relative_node_label/data/parent_label/0005.json`
- `review/task-reviews/graph/binary_tree/task_graph__binary_tree__traversal_kth_label/data/inorder_kth_node_label/0005.json`

Original issue:

- The binary-tree prompt bundle had one shared answer hint:
  `set "answer" to the requested count as an integer or the answer node label as a string exactly as shown`.
- That hint appears in both count tasks and label tasks.

Why this violates the contract:

- The answer hint should name the task-specific output value, not a union of
  unrelated answer schemas.
- This creates avoidable ambiguity for tasks whose answer schema is fixed by
  taxonomy and verifier payload.

Fix:

- Split the binary-tree answer hint by objective family in
  `prompts/graph/binary_tree/graph_binary_tree_v1.json` and wired each
  lifecycle branch to the matching prompt slot:
  - count tasks: integer count only;
  - node-label tasks: node label string exactly as shown;
  - numeric-key label tasks: node key/label exactly as shown.
- Added a regression test that rejects the old union-style answer hint and
  verifies the expected answer hint for count, node-label, and numeric-key
  binary-tree tasks.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_graph_binary_tree_tasks.py tests/test_graph_query_specific_annotation_prompts.py`
  passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_audit_prompt_annotation_contracts.py`
  passed.
- Regenerated all seven binary-tree task reviews and
  `review/task-reviews/graph/binary_tree/scene_review.xlsx`.
- Reran graph prompt concision and prompt/annotation contract audits. The old
  over-broad binary-tree answer hint no longer appears in regenerated
  binary-tree prompts or graph prompt-audit output.

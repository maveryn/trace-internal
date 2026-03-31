# TRACE RLVR Reward Contracts

Normative public metadata contract for RLVR-side answer/evidence scoring dispatch.

## 1) Goal
Every built TRACE instance should carry a small portable `reward_contract` payload so RLVR code can choose the correct scorer without task-specific branching.

The public contract should stay:
1. instance-local,
2. versioned,
3. derived from public answer/evidence types,
4. small enough to dispatch on directly.

## 2) ABI shape
`TrainInstance.reward_contract` and `TraceInstance.reward_contract` use:

```json
{
  "reward_contract_version": "v1",
  "answer": {
    "id": "answer_exact_match_v1",
    "type": "integer"
  },
  "evidence": {
    "id": "bbox_set_iou_v1",
    "type": "bbox_set"
  }
}
```

Rules:
1. `reward_contract_version` is required and currently fixed to `v1`.
2. `answer.id` is required and currently fixed to `answer_exact_match_v1`.
3. `answer.type` must exactly match `answer_gt.type`.
4. `evidence.id` is required and must be one supported public evidence reward id.
5. `evidence.type` must exactly match `evidence_gt.type`.
6. `evidence.id` must match the resolver output for `evidence.type`.

## 3) Public reward ids
### 3.1 Answer
- `answer_exact_match_v1`
  - exact match after answer-type normalization handled by the RLVR-side parser.

### 3.2 Evidence
- `bbox_set_iou_v1`
  - for box sets scored by Hungarian matching + IoU aggregation
- `numeric_exact_v1`
  - for exact scalar/list numeric witnesses
- `symbolic_set_exact_v1`
  - for unordered symbolic sets
- `sequence_exact_v1`
  - for ordered symbolic or coordinate sequences/paths
- `point_set_match_v1`
  - for unordered coordinate-point witnesses

## 4) Resolver policy
Builder-owned resolver is the source of truth for the public metadata contract.

Current mapping:
- `bbox_set` -> `bbox_set_iou_v1`
- `integer`, `integer_list` -> `numeric_exact_v1`
- `label_set`, `edge_set`, `id_set` -> `symbolic_set_exact_v1`
- `label_sequence`, `label_path`, `id_path`, `grid_point_path`, `point_path` -> `sequence_exact_v1`
- `graph_point`, `graph_point_set`, `grid_point_set`, `point_set` -> `point_set_match_v1`

Notes:
1. `graph_point` is normalized to a singleton point set at reward time.
2. `integer` is normalized to a length-1 numeric list at reward time.
3. Evidence types not covered by this resolver are unsupported for RLVR metadata until the contract doc and resolver are updated together.

## 5) Ownership and update rules
When a public answer/evidence contract changes:
1. update `trace/core/reward_contracts.py`,
2. update this document,
3. update `task-reviews/RLVR_EVIDENCE_REWARD_MAPPING.md`,
4. refresh affected task reviews/tests in the same patch.

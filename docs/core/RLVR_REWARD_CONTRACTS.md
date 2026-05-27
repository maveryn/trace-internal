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
  "reward_contract_version": "v0",
  "answer": {
    "id": "answer_exact_match_v0",
    "type": "integer"
  },
  "evidence": {
    "id": "bbox_set_soft_iou_v0",
    "type": "bbox_set"
  }
}
```

Rules:
1. `reward_contract_version` is required and currently fixed to `v0`.
2. `answer.id` is required and currently fixed to `answer_exact_match_v0`.
3. `answer.type` must exactly match `answer_gt.type`.
4. `evidence.id` is required and must be one supported public evidence reward id.
5. `evidence.type` must exactly match `evidence_gt.type`.
6. `evidence.id` must match the resolver output for `evidence.type`.

## 3) Public reward ids
### 3.1 Answer
- `answer_exact_match_v0`
  - exact match after answer-type normalization handled by the RLVR-side parser.
  - ordered answer types such as `index_list` are sequence-sensitive; a permutation with the same members is not an exact match.

### 3.2 Evidence
- `bbox_set_soft_iou_v0`
  - for unordered box witnesses scored by Hungarian matching + IoU aggregation
- `bbox_sequence_soft_iou_v0`
  - for ordered box witnesses scored by index-aligned IoU aggregation
- `point_set_soft_distance_v0`
  - for unordered pixel-point witnesses scored by Hungarian matching + soft distance aggregation
- `point_sequence_soft_distance_v0`
  - for ordered pixel-point witnesses scored by index-aligned soft distance aggregation
- `point_pair_set_soft_distance_v0`
  - for unordered pixel endpoint-pair witnesses scored by Hungarian matching + soft distance aggregation

## 4) Resolver policy
Builder-owned resolver is the source of truth for the public metadata contract.

Current mapping:
- `bbox_sequence` -> `bbox_sequence_soft_iou_v0`
- `bbox_set` -> `bbox_set_soft_iou_v0`
- `point_set` -> `point_set_soft_distance_v0`
- `point_sequence` -> `point_sequence_soft_distance_v0`
- `point_pair_set` -> `point_pair_set_soft_distance_v0`

Notes:
1. Public evidence contracts are image-level only.
2. Box set matching uses raw IoU values directly; there is no acceptance threshold.
3. Pixel point similarity is `exp(-ln(2) * (distance / half_life_px)^2)`.
   When source image size is available, `half_life_px = clamp(0.035 * sqrt(width^2 + height^2), 20, 80)`.
   A supplied `point_half_life_px` overrides this policy, and missing image-size metadata falls back to 32 px.
4. Set contracts divide matched similarity by `max(pred_count, gt_count, 1)`, so missing and extra witnesses are penalized.
5. Sequence contracts compare by position and divide by the max sequence length.
6. `point_pair_set_soft_distance_v0` treats each endpoint pair as undirected for matching, so reversed endpoints score as the same edge witness.
7. Evidence types not covered by this resolver are unsupported for RLVR metadata until the contract doc and resolver are updated together.

## 5) Ownership and update rules
When a public answer/evidence contract changes:
1. update `trace/core/reward_contracts.py`,
2. update this document,
3. update `task-reviews/RLVR_EVIDENCE_REWARD_MAPPING.md`,
4. refresh affected task reviews/tests in the same patch.

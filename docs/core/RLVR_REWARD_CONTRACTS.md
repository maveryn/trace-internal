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
  - exact match after answer-type normalization handled by the shared TRACE scorer.
  - ordered answer types such as `index_list` are sequence-sensitive; a permutation with the same members is not an exact match.

### 3.2 Evidence
- `bbox_set_soft_iou_v0`
  - for unordered box witnesses scored by Hungarian matching + IoU aggregation
- `bbox_sequence_soft_iou_v0`
  - for ordered box witnesses scored by index-aligned IoU aggregation
- `keyed_bbox_map_soft_iou_v0`
  - for role-aware box witnesses scored by exact key matching + IoU aggregation
- `keyed_point_map_soft_distance_v0`
  - for role-aware pixel-point witnesses scored by exact key matching + soft distance aggregation
- `point_set_soft_distance_v0`
  - for unordered pixel-point witnesses scored by Hungarian matching + soft distance aggregation
- `point_sequence_soft_distance_v0`
  - for ordered pixel-point witnesses scored by index-aligned soft distance aggregation
- `point_pair_set_soft_distance_v0`
  - for unordered pixel endpoint-pair witnesses scored by Hungarian matching + soft distance aggregation

### 3.3 Keyed Evidence Names
Role-aware evidence must use one of these global names when a task needs a
dictionary keyed by semantic witness role. Do not create domain-specific keyed
evidence names such as `physics_keyed_points` or `geometry_named_bboxes`.
Prefer keyed evidence over unordered set evidence whenever the reward should
verify that each witness is bound to the correct semantic role, or whenever an
unordered evidence set would make otherwise distinct witnesses ambiguous.
Unordered sets are for counting or homogeneous witness collections where role
identity and order do not matter.

- `keyed_point_map` -> `keyed_point_map_soft_distance_v0`
  - model-facing evidence value is an object mapping role keys to pixel points,
    for example `{"A": [123, 245], "B": [310, 240]}`.
  - scoring requires exact string-key agreement and scores each shared key with
    the existing pixel-point soft-distance rule; missing and extra keys are
    penalized over the union of keys.
- `keyed_bbox_map` -> `keyed_bbox_map_soft_iou_v0`
  - model-facing evidence value is an object mapping role keys to pixel boxes,
    for example `{"source": [40, 80, 120, 160], "target": [220, 90, 300, 170]}`.
  - scoring requires exact string-key agreement and scores each shared key with
    the existing bbox IoU rule; missing and extra keys are penalized over the
    union of keys.

Defer `keyed_point_pair_map` and any mixed point/box evidence type unless a
task genuinely cannot be expressed with one homogeneous geometry type; consider
changing the task evidence contract first.

## 4) Resolver policy
Builder-owned resolver is the source of truth for the public metadata contract.

Current mapping:
- `bbox_sequence` -> `bbox_sequence_soft_iou_v0`
- `bbox_set` -> `bbox_set_soft_iou_v0`
- `keyed_bbox_map` -> `keyed_bbox_map_soft_iou_v0`
- `keyed_point_map` -> `keyed_point_map_soft_distance_v0`
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
7. Keyed map contracts divide shared-key similarity by the union of predicted
   and target keys, so missing and extra role keys are penalized.
8. Evidence types not covered by this resolver are unsupported for RLVR metadata until the contract doc and resolver are updated together.

## 5) Scorer Ownership
TRACE owns the generic answer/evidence scoring implementation in
`trace/core/reward_scoring.py`. RLVR-side code should import or wrap that module
instead of maintaining a separate TRACE evidence scorer. The scorer dispatches
from the public `v0` contract ids above and accepts legacy RLVR `*_v1` evidence
ids as compatibility aliases for older exported rows.

## 6) Ownership and update rules
When a public answer/evidence contract changes:
1. update `trace/core/reward_contracts.py`,
2. update this document,
3. update `trace/core/reward_scoring.py` if scoring behavior changes,
4. refresh affected task reviews/tests in the same patch.

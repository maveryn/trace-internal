# TRACE RLVR Reward Contracts

Normative contract for TRACE answer and annotation reward dispatch.

TRACE v0 uses **annotation** as the public grounding term. Active prompts,
outputs, review artifacts, and reward contracts must use `annotation` /
`annotation_gt`; do not add alternate public grounding keys, prompt wording, or
compatibility aliases.

## 1) Purpose
Every built TRACE instance carries a compact `reward_contract` payload so RLVR
code can select the generic scorer without task-specific branching. The payload
is instance-local, versioned, and derived from the public `answer_gt.type` and
`annotation_gt.type`.

Task code must not hand-author `reward_contract`. The builder resolves it through
`trace/core/reward_contracts.py`; scoring lives in
`trace/core/reward_scoring.py`.

## 2) ABI Shape
`TrainInstance.reward_contract` and `TraceInstance.reward_contract` use:

```json
{
  "reward_contract_version": "v0",
  "answer": {
    "id": "answer_exact_match_v0",
    "type": "integer"
  },
  "annotation": {
    "id": "bbox_set_soft_iou_v0",
    "type": "bbox_set"
  }
}
```

Rules:

1. `reward_contract_version` is required and currently fixed to `v0`.
2. `answer.id` is required and currently fixed to `answer_exact_match_v0`.
3. `answer.type` must exactly match `answer_gt.type`.
4. `annotation.id` must be the resolver output for `annotation_gt.type`.
5. `annotation.type` must exactly match `annotation_gt.type`.
6. Non-current public reward ids are rejected. Do not add compatibility aliases
   for retired public output contracts.

## 3) Current Resolver Table

| Public type | Reward id | Scoring rule |
| --- | --- | --- |
| any registered answer type | `answer_exact_match_v0` | Exact match after answer-type normalization. Ordered answer types remain sequence-sensitive. |
| `bbox` | `bbox_soft_iou_v0` | One scalar bbox scored by raw IoU. |
| `bbox_set` | `bbox_set_soft_iou_v0` | Unordered Hungarian matching over raw IoU. |
| `bbox_sequence` | `bbox_sequence_soft_iou_v0` | Index-aligned IoU aggregation. |
| `keyed_bbox_map` | `keyed_bbox_map_soft_iou_v0` | Exact key matching, then one bbox IoU per key. |
| `keyed_bbox_set_map` | `keyed_bbox_set_map_soft_iou_v0` | Exact key matching, then unordered bbox-set IoU matching inside each key. |
| `point` | `point_soft_distance_v0` | One scalar point scored by soft pixel distance. |
| `point_set` | `point_set_soft_distance_v0` | Unordered Hungarian matching over soft pixel distance. |
| `point_sequence` | `point_sequence_soft_distance_v0` | Index-aligned soft pixel distance. |
| `segment` | `segment_soft_distance_v0` | One undirected segment scored by endpoint distance. |
| `segment_set` | `segment_set_soft_distance_v0` | Unordered matching of undirected segment witnesses. |
| `keyed_point_map` | `keyed_point_map_soft_distance_v0` | Exact key matching, then one point-distance score per key. |
| `keyed_point_set_map` | `keyed_point_set_map_soft_distance_v0` | Exact key matching, then unordered point-set distance matching inside each key. |

## 4) Annotation Contract Rules

Public annotation contracts are image-level only. Use these global homogeneous
annotation type names directly:

- `bbox`
- `bbox_set`
- `bbox_sequence`
- `keyed_bbox_map`
- `keyed_bbox_set_map`
- `point`
- `point_set`
- `point_sequence`
- `segment`
- `segment_set`
- `keyed_point_map`
- `keyed_point_set_map`

Do not create domain-specific keyed annotation names such as
`physics_keyed_points` or `geometry_named_bboxes`. Prefer keyed annotation when
the reward must verify semantic role binding, for example source versus target,
outer shape versus shaded region, or input versus output measurement. Unordered
sets are appropriate for counting tasks and homogeneous witness collections
where role identity and order do not matter.

Avoid mixed point/box annotation. If a task appears to need mixed geometry,
reconsider the task annotation contract first. Add a new public annotation type
only when the contract cannot be expressed with the current homogeneous types.

## 5) Scoring Semantics

1. Box-set matching uses raw IoU values directly; there is no acceptance
   threshold.
2. Pixel point similarity is
   `exp(-ln(2) * (distance / half_life_px)^2)`.
3. When source image size is available,
   `half_life_px = clamp(0.035 * sqrt(width^2 + height^2), 20, 80)`.
   A supplied `point_half_life_px` overrides this policy, and missing image-size
   metadata falls back to 32 px.
4. Set contracts divide matched similarity by `max(pred_count, gt_count, 1)`,
   so missing and extra witnesses are penalized.
5. Sequence contracts compare by position and divide by the max sequence length.
6. Keyed map contracts divide shared-key similarity by the union of predicted
   and target keys, so missing and extra role keys are penalized.
7. `segment_soft_distance_v0` and `segment_set_soft_distance_v0` treat each
   segment as undirected, so reversed endpoints score as the same witness.

## 6) Update Rules
When a public answer or annotation reward contract changes:

1. update `trace/core/reward_contracts.py`,
2. update `trace/core/reward_scoring.py` if scoring behavior changes,
3. update this document,
4. refresh affected tests and task reviews in the same patch.

#!/bin/bash

set -x

export PYTHONUNBUFFERED=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RLVR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${RLVR_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${RLVR_ROOT}"

CURRICULUM_ORDER="${CURRICULUM_ORDER:-mydata/curriculum/bucket_order.json}"
CURRICULUM_STATS="${CURRICULUM_STATS:-mydata/curriculum/bucket_stats.json}"
CURRICULUM_ALPHA0="${CURRICULUM_ALPHA0:-0.995}"
CURRICULUM_EPS_FLOOR="${CURRICULUM_EPS_FLOOR:-}"
CURRICULUM_BETA="${CURRICULUM_BETA:-2.0}"
FREEZE_VISION_TOWER="${FREEZE_VISION_TOWER:-true}"

BBOX_IOU_THRESHOLD="${BBOX_IOU_THRESHOLD:-0.5}"
BBOX_CONSISTENCY_FACTOR="${BBOX_CONSISTENCY_FACTOR:-0.0}"
BBOX_RCNT_MODE="${BBOX_RCNT_MODE:-hard}"
BBOX_SET_MODE="${BBOX_SET_MODE:-soft_iou_mass}"
BBOX_GATE_SET_LAMBDA="${BBOX_GATE_SET_LAMBDA:-0.5}"
LAMBDA_TAG="${BBOX_GATE_SET_LAMBDA//./p}"
BETA_TAG="${CURRICULUM_BETA//./p}"
FREEZE_TAG="${FREEZE_VISION_TOWER}"

ARGS=(
  python3 -m verl.trainer.main
  config=examples/config.yaml
  worker.actor.model.model_path=Qwen/Qwen2.5-VL-3B-Instruct
  worker.actor.model.freeze_vision_tower="${FREEZE_VISION_TOWER}"
  worker.rollout.tensor_parallel_size=1
  trainer.experiment_name="qwen2_5-3b-vl-bbox-curriculum-ema-freeze${FREEZE_TAG}-lam${LAMBDA_TAG}-beta${BETA_TAG}"
  trainer.n_gpus_per_node=8
  data.dataset_mode=bbox
  data.curriculum_mode=self_paced_ema
  data.curriculum_backend=prebuilt
  data.curriculum_bucket_order_path="${CURRICULUM_ORDER}"
  data.curriculum_mu_init_path="${CURRICULUM_STATS}"
  data.curriculum_alpha0="${CURRICULUM_ALPHA0}"
  data.curriculum_beta="${CURRICULUM_BETA}"
  data.curriculum_log_interval=10
  worker.reward.reward_function_kwargs.dataset_mode=auto
  worker.reward.reward_function_kwargs.bbox_iou_threshold="${BBOX_IOU_THRESHOLD}"
  worker.reward.reward_function_kwargs.bbox_set_mode="${BBOX_SET_MODE}"
  worker.reward.reward_function_kwargs.bbox_gate_set_lambda="${BBOX_GATE_SET_LAMBDA}"
  worker.reward.reward_function_kwargs.bbox_consistency_factor="${BBOX_CONSISTENCY_FACTOR}"
  worker.reward.reward_function_kwargs.bbox_r_cnt_mode="${BBOX_RCNT_MODE}"
)

if [[ -n "${CURRICULUM_EPS_FLOOR}" ]]; then
  ARGS+=(data.curriculum_eps_floor="${CURRICULUM_EPS_FLOOR}")
fi

"${ARGS[@]}"

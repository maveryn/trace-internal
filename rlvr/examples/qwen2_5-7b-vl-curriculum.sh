#!/bin/bash

set -x

export PYTHONUNBUFFERED=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RLVR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${RLVR_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${RLVR_ROOT}"

CURRICULUM_ORDER="${CURRICULUM_ORDER:-mydata/prism_curriculum/bucket_order.json}"
BBOX_IOU_THRESHOLD="${BBOX_IOU_THRESHOLD:-0.5}"
BBOX_CONSISTENCY_FACTOR="${BBOX_CONSISTENCY_FACTOR:-0.0}"
BBOX_RCNT_MODE="${BBOX_RCNT_MODE:-soft}"
BBOX_GATE_SET_LAMBDA="${BBOX_GATE_SET_LAMBDA:-0.2}"

python3 -m verl.trainer.main \
  config=examples/config.yaml \
  worker.actor.model.model_path=Qwen/Qwen2.5-VL-7B-Instruct \
  worker.rollout.tensor_parallel_size=1 \
  trainer.experiment_name=qwen2_5-7b-vl-bbox-curriculum \
  trainer.n_gpus_per_node=8 \
  data.prism_mode=bbox \
  data.curriculum_mode=offline_fixed \
  data.curriculum_backend=prebuilt \
  data.curriculum_bucket_order_path="${CURRICULUM_ORDER}" \
  worker.reward.reward_function_kwargs.prism_mode=auto \
  worker.reward.reward_function_kwargs.bbox_iou_threshold="${BBOX_IOU_THRESHOLD}" \
  worker.reward.reward_function_kwargs.bbox_gate_set_lambda="${BBOX_GATE_SET_LAMBDA}" \
  worker.reward.reward_function_kwargs.bbox_consistency_factor="${BBOX_CONSISTENCY_FACTOR}" \
  worker.reward.reward_function_kwargs.bbox_r_cnt_mode="${BBOX_RCNT_MODE}"

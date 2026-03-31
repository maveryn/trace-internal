#!/bin/bash

set -x

export PYTHONUNBUFFERED=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RLVR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${RLVR_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${RLVR_ROOT}"

BBOX_GATE_SET_LAMBDA="${BBOX_GATE_SET_LAMBDA:-0.2}"
LAMBDA_TAG="${BBOX_GATE_SET_LAMBDA//./p}"

python3 -m verl.trainer.main \
  config=examples/config.yaml \
  worker.actor.model.model_path=Qwen/Qwen2.5-VL-7B-Instruct \
  worker.rollout.tensor_parallel_size=1 \
  trainer.experiment_name="qwen2_5-7b-vl-bbox-rcnt-hard-lam${LAMBDA_TAG}" \
  trainer.n_gpus_per_node=8 \
  data.prism_mode=bbox \
  worker.reward.reward_function_kwargs.prism_mode=auto \
  worker.reward.reward_function_kwargs.bbox_iou_threshold=0.5 \
  worker.reward.reward_function_kwargs.bbox_set_mode=soft_iou_mass \
  worker.reward.reward_function_kwargs.bbox_gate_set_lambda="${BBOX_GATE_SET_LAMBDA}" \
  worker.reward.reward_function_kwargs.bbox_consistency_factor=0.0 \
  worker.reward.reward_function_kwargs.bbox_r_cnt_mode=hard

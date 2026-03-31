#!/bin/bash

set -x

export PYTHONUNBUFFERED=1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RLVR_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${RLVR_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
cd "${RLVR_ROOT}"

CURRICULUM_ORDER="${CURRICULUM_ORDER:-mydata/prism_curriculum/bucket_order.json}"
CURRICULUM_STATS="${CURRICULUM_STATS:-mydata/prism_curriculum/bucket_stats.json}"
CURRICULUM_ALPHA0="${CURRICULUM_ALPHA0:-0.995}"
CURRICULUM_EPS_FLOOR="${CURRICULUM_EPS_FLOOR:-}"
CURRICULUM_BETA="${CURRICULUM_BETA:-2.0}"
LIST_REWARD_MODE="${LIST_REWARD_MODE:-exact}"
BETA_TAG="${CURRICULUM_BETA//./p}"

ARGS=(
  python3 -m verl.trainer.main
  config=examples/config.yaml
  worker.actor.model.model_path=Qwen/Qwen2.5-VL-3B-Instruct
  worker.actor.model.freeze_vision_tower=true
  worker.rollout.tensor_parallel_size=1
  trainer.experiment_name="qwen2_5-3b-vl-integer-curriculum-ema-frozen-beta${BETA_TAG}"
  trainer.n_gpus_per_node=8
  data.prism_mode=integer
  data.curriculum_mode=self_paced_ema
  data.curriculum_backend=prebuilt
  data.curriculum_bucket_order_path="${CURRICULUM_ORDER}"
  data.curriculum_mu_init_path="${CURRICULUM_STATS}"
  data.curriculum_alpha0="${CURRICULUM_ALPHA0}"
  data.curriculum_beta="${CURRICULUM_BETA}"
  data.curriculum_log_interval=10
  worker.reward.reward_function_kwargs.prism_mode=integer
  worker.reward.reward_function_kwargs.list_reward_mode="${LIST_REWARD_MODE}"
)

if [[ -n "${CURRICULUM_EPS_FLOOR}" ]]; then
  ARGS+=(data.curriculum_eps_floor="${CURRICULUM_EPS_FLOOR}")
fi

"${ARGS[@]}"

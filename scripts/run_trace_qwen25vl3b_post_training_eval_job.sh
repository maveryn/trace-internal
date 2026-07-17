#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TRAINING_REPO_ROOT="${TRAINING_REPO_ROOT:-/home/shadeform/trace}"
PYTHON_BIN="${PYTHON_BIN:-/home/shadeform/venv/bin/python}"
RUN_STAMP="${RUN_STAMP:-20260716T225857Z}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-trace_qwen25vl3b_easyr1_all1000_answer_nokl_step500_bsz128_rollout8_iidval2000_rerun_${RUN_STAMP}}"
CHECKPOINT_ROOT="${CHECKPOINT_ROOT:-/dev/shm/trace_rlvr/easyr1_checkpoints/${EXPERIMENT_NAME}}"
TEMPORARY_REPO="${TEMPORARY_REPO:-maveryn/trace-qwen25vl3b-rlvr-answer-step500-rerun-${RUN_STAMP}}"
CANONICAL_REPO="${CANONICAL_REPO:-maveryn/trace-qwen2.5-vl-3b}"
SOURCE_MODEL_SLUG="${SOURCE_MODEL_SLUG:-trace-qwen25vl3b-answer-step500-20260716}"
RUN_TAG="${RUN_TAG:-trace_eval_v1_temp06_seed42_43_44_trace-qwen25vl3b-step500-20260716}"
PUBLIC_RUN_ID="${PUBLIC_RUN_ID:-trace-qwen2.5-vl-3b-eval-v1}"
STATE_ROOT="${STATE_ROOT:-${REPO_ROOT}/logs/handoff/${PUBLIC_RUN_ID}}"
TRAINING_SOURCE_COMMIT="${TRAINING_SOURCE_COMMIT:-847e9f5279f8111fdbfef1c8b8631fc621c23456}"

args=(
  --experiment-name "${EXPERIMENT_NAME}"
  --training-status "${TRAINING_REPO_ROOT}/logs/rlvr/${EXPERIMENT_NAME}.status"
  --training-pid-file "${TRAINING_REPO_ROOT}/logs/rlvr/${EXPERIMENT_NAME}.pid"
  --training-script-name run_trace_qwen25vl3b_easyr1_all1000_answer_nokl_step500_job.sh
  --checkpoint-root "${CHECKPOINT_ROOT}"
  --checkpoint-step 500
  --world-size 8
  --temporary-repo "${TEMPORARY_REPO}"
  --canonical-repo "${CANONICAL_REPO}"
  --source-model-slug "${SOURCE_MODEL_SLUG}"
  --public-model-id trace-qwen2.5-vl-3b
  --display-name "TRACE Qwen2.5-VL 3B"
  --run-tag "${RUN_TAG}"
  --public-run-id "${PUBLIC_RUN_ID}"
  --paper-repo maveryn/trace-eval-runs
  --token-file "${TRAINING_REPO_ROOT}/hf-token.txt"
  --state-root "${STATE_ROOT}"
  --dataset-manifest /dev/shm/trace_rlvr/LMUData/trace_eval_v1_dataset_manifest.json
  --judge-model /dev/shm/trace_rlvr/final25_models/qwen3-32b-judge
  --judge-revision 9216db5781bf21249d130ec9da846c4624c16137
  --python-bin "${PYTHON_BIN}"
  --eval-deps-root "${TRAINING_REPO_ROOT}/.tmp/eval_deps"
  --vlmeval-root "${TRAINING_REPO_ROOT}/external/VLMEvalKit"
  --seed 42 --seed 43 --seed 44
  --gpu-group 0 --gpu-group 1 --gpu-group 2 --gpu-group 3
  --gpu-group 4 --gpu-group 5 --gpu-group 6 --gpu-group 7
  --training-source-commit "${TRAINING_SOURCE_COMMIT}"
  --base-model-id Qwen/Qwen2.5-VL-3B-Instruct
  --base-model-revision 66285546d2b821cf421d4f5eb2576359d3770cd3
  --dataset-id maveryn/trace
  --dataset-revision e317b746b258630682367cc6a9d87dedd195113c
  --wandb-url https://wandb.ai/llm-reasoning-rl/trace_easyr1/runs/kijsydl8
)

if [[ "${TRACE_3B_HANDOFF_PRINT_CONFIG:-0}" == "1" ]]; then
  args+=(--print-config)
fi
if [[ "${TRACE_3B_HANDOFF_DRY_RUN:-0}" == "1" ]]; then
  args+=(--dry-run)
fi

exec "${PYTHON_BIN}" "${REPO_ROOT}/scripts/run_trace_eval_after_training.py" "${args[@]}" "$@"

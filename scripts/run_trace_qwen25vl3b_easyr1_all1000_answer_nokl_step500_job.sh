#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-trace_qwen25vl3b_easyr1_all1000_answer_nokl_step500_bsz128_rollout8_iidval2000_rerun_${RUN_STAMP}}"

MODEL_PATH="${MODEL_PATH:-/dev/shm/trace_rlvr/final25_models/qwen25vl3b-base}"
BASE_MODEL_ID="${BASE_MODEL_ID:-Qwen/Qwen2.5-VL-3B-Instruct}"
BASE_MODEL_REVISION="${BASE_MODEL_REVISION:-66285546d2b821cf421d4f5eb2576359d3770cd3}"
DATASET_ROOT="${DATASET_ROOT:-/dev/shm/trace_rlvr/datasets/maveryn-trace-e317b746b258}"
DATASET_ID="${DATASET_ID:-maveryn/trace}"
DATASET_REVISION="${DATASET_REVISION:-e317b746b258630682367cc6a9d87dedd195113c}"
TRAIN_FILES="${TRAIN_FILES:-${DATASET_ROOT}/data/train}"
VAL_FILES="${VAL_FILES:-${DATASET_ROOT}/data/validation/trace_rlvr_validation_iid_2000_all1000_seed1042.parquet}"

CHECKPOINT_ROOT="${SAVE_CHECKPOINT_PATH:-/dev/shm/trace_rlvr/easyr1_checkpoints/${EXPERIMENT_NAME}}"
LOG_PATH="${LOG_PATH:-/dev/shm/trace_rlvr/logs/${EXPERIMENT_NAME}.log}"
STATUS_PATH="${STATUS_PATH:-${REPO_ROOT}/logs/rlvr/${EXPERIMENT_NAME}.status}"
PID_PATH="${PID_PATH:-${REPO_ROOT}/logs/rlvr/${EXPERIMENT_NAME}.pid}"
LOG_POINTER_PATH="${LOG_POINTER_PATH:-${REPO_ROOT}/logs/rlvr/${EXPERIMENT_NAME}.log.path}"
PYTHON_BIN="${PYTHON_BIN:-/home/shadeform/venv/bin/python}"

HF_REPO_ID="${HF_REPO_ID:-maveryn/trace-qwen25vl3b-rlvr-answer-step500-rerun-${RUN_STAMP}}"
HF_TOKEN_FILE="${HF_TOKEN_FILE:-${REPO_ROOT}/hf-token.txt}"
PUBLISH_TO_HF="${PUBLISH_TO_HF:-true}"

MAX_STEPS="${MAX_STEPS:-500}"
SAVE_FREQ="${SAVE_FREQ:-100}"
VAL_FREQ="${VAL_FREQ:-100}"
SAVE_LIMIT="${SAVE_LIMIT:-1}"
VAL_BEFORE_TRAIN="${VAL_BEFORE_TRAIN:-false}"
FIND_LAST_CHECKPOINT="${FIND_LAST_CHECKPOINT:-false}"
LOAD_CHECKPOINT_PATH="${LOAD_CHECKPOINT_PATH:-null}"

ROLLOUT_BATCH_SIZE="${ROLLOUT_BATCH_SIZE:-128}"
ACTOR_GLOBAL_BATCH_SIZE="${ACTOR_GLOBAL_BATCH_SIZE:-128}"
ROLLOUT_N="${ROLLOUT_N:-8}"
VAL_BATCH_SIZE="${VAL_BATCH_SIZE:-1024}"
MAX_PROMPT_LENGTH="${MAX_PROMPT_LENGTH:-2048}"
MAX_RESPONSE_LENGTH="${MAX_RESPONSE_LENGTH:-2048}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.6}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-8192}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-2}"
N_GPUS="${N_GPUS:-8}"
ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE="${ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE:-2}"
ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE="${ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE:-1}"

PROJECT_NAME="${PROJECT_NAME:-trace_easyr1}"
WANDB_ENTITY="${WANDB_ENTITY:-llm-reasoning-rl}"
WANDB_MODE="${WANDB_MODE:-online}"
CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0,1,2,3,4,5,6,7}"
TRACE_RLVR_DRY_RUN="${TRACE_RLVR_DRY_RUN:-0}"

case "${TRACE_RLVR_DRY_RUN,,}" in
  1|true|yes|on) TRACE_RLVR_DRY_RUN=1 ;;
  0|false|no|off) TRACE_RLVR_DRY_RUN=0 ;;
  *)
    echo "TRACE_RLVR_DRY_RUN must be a boolean; got ${TRACE_RLVR_DRY_RUN}" >&2
    exit 2
    ;;
esac
case "${PUBLISH_TO_HF,,}" in
  1|true|yes|on) PUBLISH_TO_HF=true ;;
  0|false|no|off) PUBLISH_TO_HF=false ;;
  *)
    echo "PUBLISH_TO_HF must be a boolean; got ${PUBLISH_TO_HF}" >&2
    exit 2
    ;;
esac

if [[ -L "$CHECKPOINT_ROOT" ]]; then
  echo "SAVE_CHECKPOINT_PATH must not be a symlink: ${CHECKPOINT_ROOT}" >&2
  exit 2
fi
REPO_ROOT="$(realpath -m -- "$REPO_ROOT")"
CHECKPOINT_ROOT="$(realpath -m -- "$CHECKPOINT_ROOT")"
LOG_PATH="$(realpath -m -- "$LOG_PATH")"
STATUS_PATH="$(realpath -m -- "$STATUS_PATH")"
PID_PATH="$(realpath -m -- "$PID_PATH")"
LOG_POINTER_PATH="$(realpath -m -- "$LOG_POINTER_PATH")"
MODEL_PATH="$(realpath -m -- "$MODEL_PATH")"
TRAIN_FILES="$(realpath -m -- "$TRAIN_FILES")"
VAL_FILES="$(realpath -m -- "$VAL_FILES")"
HF_TOKEN_FILE="$(realpath -m -- "$HF_TOKEN_FILE")"
if [[ "$PYTHON_BIN" == */* ]]; then
  PYTHON_BIN="$(realpath -m -s -- "$PYTHON_BIN")"
else
  resolved_python="$(command -v -- "$PYTHON_BIN" || true)"
  if [[ -z "$resolved_python" ]]; then
    echo "Python executable not found on PATH: ${PYTHON_BIN}" >&2
    exit 2
  fi
  PYTHON_BIN="$resolved_python"
fi
if [[ "$CHECKPOINT_ROOT" != /dev/shm/* ]]; then
  echo "SAVE_CHECKPOINT_PATH must resolve under /dev/shm; got ${CHECKPOINT_ROOT}" >&2
  exit 2
fi
if [[ "$TRACE_RLVR_DRY_RUN" == "0" && "$LOG_PATH" != /dev/shm/* ]]; then
  echo "LOG_PATH must resolve under /dev/shm for a training run; got ${LOG_PATH}" >&2
  exit 2
fi

mkdir -p \
  "$(dirname "$LOG_PATH")" \
  "$(dirname "$STATUS_PATH")" \
  "$(dirname "$PID_PATH")" \
  "$(dirname "$LOG_POINTER_PATH")"
touch "$LOG_PATH"
printf '%s\n' "$LOG_PATH" >"$LOG_POINTER_PATH"

record_status() {
  printf '%s\n' "$1" >"$STATUS_PATH"
}

log() {
  printf '%s\n' "$1" | tee -a "$LOG_PATH"
}

fail_job() {
  local exit_code="$1"
  trap - ERR
  record_status "failed exit_code=${exit_code} time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  exit "$exit_code"
}
trap 'fail_job $?' ERR

require_contract_value() {
  local name="$1"
  local actual="$2"
  local expected="$3"
  if [[ "$actual" != "$expected" ]]; then
    echo "${name} is fixed for this reproducibility job: expected ${expected}, got ${actual}" >&2
    exit 2
  fi
}

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python executable not found: ${PYTHON_BIN}" >&2
  exit 2
fi
if [[ ! -x "${REPO_ROOT}/scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh" ]]; then
  echo "TRACE 3B answer launcher not found under REPO_ROOT=${REPO_ROOT}" >&2
  exit 2
fi
require_contract_value MAX_STEPS "$MAX_STEPS" 500
require_contract_value SAVE_FREQ "$SAVE_FREQ" 100
require_contract_value VAL_FREQ "$VAL_FREQ" 100
require_contract_value SAVE_LIMIT "$SAVE_LIMIT" 1
require_contract_value VAL_BEFORE_TRAIN "$VAL_BEFORE_TRAIN" false
require_contract_value FIND_LAST_CHECKPOINT "$FIND_LAST_CHECKPOINT" false
require_contract_value LOAD_CHECKPOINT_PATH "$LOAD_CHECKPOINT_PATH" null
require_contract_value ROLLOUT_BATCH_SIZE "$ROLLOUT_BATCH_SIZE" 128
require_contract_value ACTOR_GLOBAL_BATCH_SIZE "$ACTOR_GLOBAL_BATCH_SIZE" 128
require_contract_value ROLLOUT_N "$ROLLOUT_N" 8
require_contract_value VAL_BATCH_SIZE "$VAL_BATCH_SIZE" 1024
require_contract_value MAX_PROMPT_LENGTH "$MAX_PROMPT_LENGTH" 2048
require_contract_value MAX_RESPONSE_LENGTH "$MAX_RESPONSE_LENGTH" 2048
require_contract_value GPU_MEMORY_UTILIZATION "$GPU_MEMORY_UTILIZATION" 0.6
require_contract_value MAX_NUM_BATCHED_TOKENS "$MAX_NUM_BATCHED_TOKENS" 8192
require_contract_value TENSOR_PARALLEL_SIZE "$TENSOR_PARALLEL_SIZE" 2
require_contract_value N_GPUS "$N_GPUS" 8
require_contract_value ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE \
  "$ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE" 2
require_contract_value ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE \
  "$ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE" 1
require_contract_value PROJECT_NAME "$PROJECT_NAME" trace_easyr1
require_contract_value WANDB_MODE "$WANDB_MODE" online
if [[ "$EXPERIMENT_NAME" != trace_* ]]; then
  echo "EXPERIMENT_NAME must keep the trace_ W&B run prefix; got ${EXPERIMENT_NAME}" >&2
  exit 2
fi
if [[ ! "$HF_REPO_ID" =~ ^[^/]+/trace-qwen25vl3b-[A-Za-z0-9._-]+$ ]]; then
  echo "HF_REPO_ID must be an owner/trace-qwen25vl3b-* model repository; got ${HF_REPO_ID}" >&2
  exit 2
fi
if [[ "$TRACE_RLVR_DRY_RUN" == "0" && ( -e "$CHECKPOINT_ROOT" || -L "$CHECKPOINT_ROOT" ) ]]; then
  echo "Checkpoint root already exists; choose a fresh RUN_STAMP or EXPERIMENT_NAME: ${CHECKPOINT_ROOT}" >&2
  exit 2
fi
if [[ "$TRACE_RLVR_DRY_RUN" == "0" && "$PUBLISH_TO_HF" == "true" && -z "${HF_TOKEN:-}" && ! -s "$HF_TOKEN_FILE" ]]; then
  echo "Hugging Face token not found in HF_TOKEN or ${HF_TOKEN_FILE}" >&2
  exit 2
fi
if [[ "$TRACE_RLVR_DRY_RUN" == "0" && "$PUBLISH_TO_HF" == "true" && -z "${HF_TOKEN:-}" ]]; then
  token_mode="$(stat -c '%a' "$HF_TOKEN_FILE")"
  if (( (8#${token_mode}) & 8#077 )); then
    echo "Hugging Face token file must have mode 600 or stricter: ${HF_TOKEN_FILE}" >&2
    exit 2
  fi
fi

"$PYTHON_BIN" - "$MODEL_PATH" "$BASE_MODEL_REVISION" "$TRAIN_FILES" "$VAL_FILES" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys

import pyarrow.parquet as pq

model_path = Path(sys.argv[1])
expected_revision = sys.argv[2]
train_path = Path(sys.argv[3])
val_path = Path(sys.argv[4])

if not (model_path / "config.json").is_file():
    raise SystemExit(f"missing model config: {model_path / 'config.json'}")
weights = sorted(model_path.glob("*.safetensors"))
if not weights or any(path.stat().st_size == 0 for path in weights):
    raise SystemExit(f"missing or empty model weights under {model_path}")
marker_path = model_path / ".trace_model_revision.json"
marker = json.loads(marker_path.read_text(encoding="utf-8"))
if marker.get("immutable_revision") != expected_revision:
    raise SystemExit(
        f"base revision mismatch: {marker.get('immutable_revision')} != {expected_revision}"
    )

train_parquets = sorted(train_path.glob("*.parquet")) if train_path.is_dir() else [train_path]
if not train_parquets or any(not path.is_file() for path in train_parquets):
    raise SystemExit(f"training parquet files not found: {train_path}")
if not val_path.is_file():
    raise SystemExit(f"validation parquet not found: {val_path}")

required_columns = {"images", "prompt_answer", "answer_gt", "instance_id", "task"}
train_rows = 0
for path in train_parquets:
    metadata = pq.read_metadata(path)
    train_rows += metadata.num_rows
    missing = required_columns.difference(pq.read_schema(path).names)
    if missing:
        raise SystemExit(f"missing train columns in {path}: {sorted(missing)}")
val_metadata = pq.read_metadata(val_path)
missing = required_columns.difference(pq.read_schema(val_path).names)
if missing:
    raise SystemExit(f"missing validation columns in {val_path}: {sorted(missing)}")
if train_rows != 64_000 or val_metadata.num_rows != 2_000:
    raise SystemExit(
        f"unexpected dataset rows: train={train_rows}, validation={val_metadata.num_rows}"
    )
print(
    f"Validated pinned inputs: model={model_path}, train_rows={train_rows}, "
    f"validation_rows={val_metadata.num_rows}"
)
PY

SOURCE_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD)"
printf '%s\n' "$$" >"$PID_PATH"
record_status "training pid=$$ time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

log "[trace-3b-final] experiment=${EXPERIMENT_NAME}"
log "[trace-3b-final] model=${MODEL_PATH}@${BASE_MODEL_REVISION}"
log "[trace-3b-final] train_files=${TRAIN_FILES}"
log "[trace-3b-final] val_files=${VAL_FILES}"
log "[trace-3b-final] checkpoint_path=${CHECKPOINT_ROOT} save_limit=${SAVE_LIMIT}"
log "[trace-3b-final] log_path=${LOG_PATH}"
log "[trace-3b-final] max_steps=${MAX_STEPS} n_gpus=${N_GPUS} tp=${TENSOR_PARALLEL_SIZE}"
log "[trace-3b-final] validation=batch${VAL_BATCH_SIZE},temp0.6,top_p0.95,n1,every${VAL_FREQ}"
log "[trace-3b-final] wandb=${WANDB_ENTITY}/${PROJECT_NAME}/${EXPERIMENT_NAME} mode=${WANDB_MODE}"
log "[trace-3b-final] hf_repo=${HF_REPO_ID} private=true publish=${PUBLISH_TO_HF}"

env \
  -u HF_TOKEN \
  -u REF_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE \
  -u WANDB_NAME \
  -u WANDB_PROJECT \
  -u WANDB_RESUME \
  -u WANDB_RUN_ID \
  RUN_STAMP="$RUN_STAMP" \
  EXPERIMENT_NAME="$EXPERIMENT_NAME" \
  SAVE_CHECKPOINT_PATH="$CHECKPOINT_ROOT" \
  MODEL_PATH="$MODEL_PATH" \
  TRAIN_FILES="$TRAIN_FILES" \
  VAL_FILES="$VAL_FILES" \
  MAX_STEPS="$MAX_STEPS" \
  SAVE_FREQ="$SAVE_FREQ" \
  VAL_FREQ="$VAL_FREQ" \
  SAVE_LIMIT="$SAVE_LIMIT" \
  VAL_BEFORE_TRAIN="$VAL_BEFORE_TRAIN" \
  FIND_LAST_CHECKPOINT="$FIND_LAST_CHECKPOINT" \
  LOAD_CHECKPOINT_PATH="$LOAD_CHECKPOINT_PATH" \
  ROLLOUT_BATCH_SIZE="$ROLLOUT_BATCH_SIZE" \
  ACTOR_GLOBAL_BATCH_SIZE="$ACTOR_GLOBAL_BATCH_SIZE" \
  ROLLOUT_N="$ROLLOUT_N" \
  VAL_BATCH_SIZE="$VAL_BATCH_SIZE" \
  MAX_PROMPT_LENGTH="$MAX_PROMPT_LENGTH" \
  MAX_RESPONSE_LENGTH="$MAX_RESPONSE_LENGTH" \
  GPU_MEMORY_UTILIZATION="$GPU_MEMORY_UTILIZATION" \
  MAX_NUM_BATCHED_TOKENS="$MAX_NUM_BATCHED_TOKENS" \
  TENSOR_PARALLEL_SIZE="$TENSOR_PARALLEL_SIZE" \
  N_GPUS="$N_GPUS" \
  ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE="$ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE" \
  ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE="$ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE" \
  TRACE_OUTPUT_MODE=answer \
  TRACE_REWARD_MODE=answer \
  TRACE_REWARD_SLUG=answer \
  TRACE_ANNOTATION_REWARD_FORMULA=gated \
  TRACE_ANNOTATION_FRACTION=0.0 \
  TRACE_ANSWER_WEIGHT=1.0 \
  TRACE_ANNOTATION_WEIGHT=0.0 \
  TRACE_FORMAT_WEIGHT=0.05 \
  PROMPT_KEY=prompt_answer \
  SYSTEM_PROMPT_FILE=../examples/prompts/trace_vero_json_system_prompt_answer.txt \
  REWARD_FUNCTION=examples/reward_function/trace_rlvr.py:compute_score \
  PROJECT_NAME="$PROJECT_NAME" \
  WANDB_ENTITY="$WANDB_ENTITY" \
  WANDB_MODE="$WANDB_MODE" \
  CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES" \
  TRACE_RLVR_DRY_RUN="$TRACE_RLVR_DRY_RUN" \
  "${REPO_ROOT}/scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh" \
  >>"$LOG_PATH" 2>&1

if [[ "$TRACE_RLVR_DRY_RUN" == "1" ]]; then
  record_status "dry_run_complete time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  log "[trace-3b-final] dry run complete; training, merge, and upload were not started"
  trap - ERR
  exit 0
fi

record_status "verifying final checkpoint time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

"$PYTHON_BIN" - "$CHECKPOINT_ROOT" "$MAX_STEPS" "$N_GPUS" <<'PY' >>"$LOG_PATH" 2>&1
from pathlib import Path
import json
import sys

root = Path(sys.argv[1])
step = int(sys.argv[2])
world_size = int(sys.argv[3])
expected_step = root / f"global_step_{step}"
if not expected_step.is_dir() or expected_step.is_symlink():
    raise SystemExit(f"final checkpoint is missing or unsafe: {expected_step}")
actor = expected_step / "actor"
for prefix in ("model", "optim", "extra_state"):
    expected_names = {
        f"{prefix}_world_size_{world_size}_rank_{rank}.pt" for rank in range(world_size)
    }
    files = {path.name: path for path in actor.glob(f"{prefix}_world_size_{world_size}_rank_*.pt")}
    if set(files) != expected_names:
        raise SystemExit(
            f"unexpected final {prefix} shards: {sorted(files)} != {sorted(expected_names)}"
        )
    if any(path.stat().st_size == 0 for path in files.values()):
        raise SystemExit(f"empty final {prefix} shard under {actor}")
dataloader = expected_step / "dataloader.pt"
config = actor / "huggingface" / "config.json"
if not dataloader.is_file() or dataloader.stat().st_size == 0:
    raise SystemExit(f"missing or empty final dataloader state: {dataloader}")
if not config.is_file() or config.stat().st_size == 0:
    raise SystemExit(f"missing or empty final Hugging Face config: {config}")
json.loads(config.read_text(encoding="utf-8"))
tracker = json.loads((root / "checkpoint_tracker.json").read_text(encoding="utf-8"))
if int(tracker["last_global_step"]) != step:
    raise SystemExit(f"final checkpoint tracker mismatch: {tracker}")
print(f"Verified final checkpoint before merge: {expected_step}")
PY

record_status "merging time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cd "${REPO_ROOT}/rlvr/easyr1_backend"
"$PYTHON_BIN" scripts/model_merger.py \
  --local_dir "${CHECKPOINT_ROOT}/global_step_${MAX_STEPS}/actor" \
  >>"$LOG_PATH" 2>&1

record_status "pruning checkpoints time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

"$PYTHON_BIN" - "$CHECKPOINT_ROOT" "$MAX_STEPS" <<'PY' >>"$LOG_PATH" 2>&1
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1]).resolve()
step = int(sys.argv[2])
if not root.is_dir() or root == Path("/dev/shm") or Path("/dev/shm") not in root.parents:
    raise SystemExit(f"refusing to prune unsafe checkpoint root: {root}")
expected_step = root / f"global_step_{step}"
merged = expected_step / "actor" / "huggingface"
merged_weights = sorted(merged.glob("*.safetensors"))
if not merged_weights or any(path.stat().st_size == 0 for path in merged_weights):
    raise SystemExit(f"merged model is missing or empty under {merged}; refusing to prune")
for path in sorted(root.glob("global_step_*")):
    if path == expected_step:
        continue
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    print(f"Pruned non-final checkpoint: {path}")
retained_steps = sorted(path.name for path in root.glob("global_step_*") if path.is_dir())
if retained_steps != [expected_step.name]:
    raise SystemExit(f"unexpected retained checkpoints after pruning: {retained_steps}")
print(f"Retained only final checkpoint: {expected_step}")
PY

if [[ "$PUBLISH_TO_HF" == "false" ]]; then
  record_status "complete local_only checkpoint=${CHECKPOINT_ROOT}/global_step_${MAX_STEPS} time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  log "[trace-3b-final] complete without Hugging Face publication"
  trap - ERR
  exit 0
fi

record_status "uploading repo=${HF_REPO_ID} private=true time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

HF_REPO_ID="$HF_REPO_ID" \
HF_TOKEN_FILE="$HF_TOKEN_FILE" \
EXPERIMENT_NAME="$EXPERIMENT_NAME" \
CHECKPOINT_ROOT="$CHECKPOINT_ROOT" \
MAX_STEPS="$MAX_STEPS" \
SOURCE_COMMIT="$SOURCE_COMMIT" \
BASE_MODEL_ID="$BASE_MODEL_ID" \
BASE_MODEL_REVISION="$BASE_MODEL_REVISION" \
DATASET_ID="$DATASET_ID" \
DATASET_REVISION="$DATASET_REVISION" \
WANDB_ENTITY="$WANDB_ENTITY" \
PROJECT_NAME="$PROJECT_NAME" \
"$PYTHON_BIN" - <<'PY' >>"$LOG_PATH" 2>&1
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import stat

from huggingface_hub import HfApi
import wandb

repo_id = os.environ["HF_REPO_ID"]
run_name = os.environ["EXPERIMENT_NAME"]
checkpoint_root = Path(os.environ["CHECKPOINT_ROOT"])
step = int(os.environ["MAX_STEPS"])
merged = checkpoint_root / f"global_step_{step}" / "actor" / "huggingface"

token = os.environ.get("HF_TOKEN", "").strip()
token_file = Path(os.environ["HF_TOKEN_FILE"])
if not token:
    if not token_file.is_file():
        raise SystemExit(f"Hugging Face token file not found: {token_file}")
    if stat.S_IMODE(token_file.stat().st_mode) & 0o077:
        raise SystemExit(f"Hugging Face token file must have mode 600 or stricter: {token_file}")
    token = token_file.read_text(encoding="utf-8").strip()
if not token:
    raise SystemExit("Hugging Face token is empty")

wandb_url = None
try:
    project_path = f"{os.environ['WANDB_ENTITY']}/{os.environ['PROJECT_NAME']}"
    candidates = list(
        wandb.Api().runs(
            project_path,
            filters={"display_name": run_name},
            order="-created_at",
        )
    )
    if candidates:
        wandb_url = candidates[0].url
except Exception as exc:
    print(f"Could not resolve W&B URL during publication: {exc}")

hashes = {}
for path in sorted(merged.glob("*.safetensors")):
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    hashes[path.name] = digest.hexdigest()
if not hashes:
    raise SystemExit(f"no merged safetensor files found under {merged}")

provenance = {
    "run_name": run_name,
    "wandb_url": wandb_url,
    "source_commit": os.environ["SOURCE_COMMIT"],
    "base_model": os.environ["BASE_MODEL_ID"],
    "base_revision": os.environ["BASE_MODEL_REVISION"],
    "dataset": os.environ["DATASET_ID"],
    "dataset_revision": os.environ["DATASET_REVISION"],
    "checkpoint_step": step,
    "checkpoint_retention": 1,
    "merged_safetensor_sha256": hashes,
    "published_at": datetime.now(timezone.utc).isoformat(),
}
(merged / "trace_training_provenance.json").write_text(
    json.dumps(provenance, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)

api = HfApi(token=token)
api.create_repo(repo_id=repo_id, repo_type="model", private=True, exist_ok=True)
pre_upload_info = api.model_info(repo_id, files_metadata=False)
if pre_upload_info.private is not True:
    raise SystemExit(f"refusing to upload because repository is not private: {repo_id}")
api.upload_folder(repo_id=repo_id, repo_type="model", folder_path=merged)
info = api.model_info(repo_id, files_metadata=True)
if info.private is not True:
    raise SystemExit(f"uploaded repository is not private: {repo_id}")
publication = {
    "repo_id": repo_id,
    "private": True,
    "revision": str(info.sha),
    "url": f"https://huggingface.co/{repo_id}",
}
(checkpoint_root / "hf_publication.json").write_text(
    json.dumps(publication, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(f"Uploaded private model: {publication['url']}")
print(f"Remote revision: {publication['revision']}")
PY

REMOTE_REVISION="$(
  "$PYTHON_BIN" - "$CHECKPOINT_ROOT/hf_publication.json" <<'PY'
import json
from pathlib import Path
import sys

print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["revision"])
PY
)"
record_status "complete repo=${HF_REPO_ID} revision=${REMOTE_REVISION} time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "[trace-3b-final] complete repo=${HF_REPO_ID} revision=${REMOTE_REVISION}"
trap - ERR

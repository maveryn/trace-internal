#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/shadeform/trace}"
cd "$REPO_ROOT"

if [[ -f /home/shadeform/venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source /home/shadeform/venv/bin/activate
fi

if [[ "${SKIP_TOKEN_FILES:-false}" != "true" && -f hf-token.txt ]]; then
  export HF_TOKEN="$(tr -d '\r\n' < hf-token.txt)"
  export HUGGINGFACE_HUB_TOKEN="$HF_TOKEN"
  export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
fi
if [[ "${SKIP_TOKEN_FILES:-false}" != "true" && -f wandb-token.txt ]]; then
  export WANDB_API_KEY="$(tr -d '\r\n' < wandb-token.txt)"
fi

export WANDB_MODE="${WANDB_MODE:-online}"

mkdir -p logs/rlvr

RUN_STAMP="${RUN_STAMP:-$(date -u +%Y%m%dT%H%M%SZ)}"
MASTER_LOG="${MASTER_LOG:-logs/rlvr/annotation_prompt_stress_additive_ann0p50_25step_h200_${RUN_STAMP}.log}"
SCRATCH_ROOT="${SCRATCH_ROOT:-/dev/shm/trace_rlvr/easyr1_checkpoints/prompt_stress_scratch_${RUN_STAMP}}"
CLEAN_CHECKPOINTS="${CLEAN_CHECKPOINTS:-true}"
EARLY_STOP_ON_RESPONSE_LENGTH="${EARLY_STOP_ON_RESPONSE_LENGTH:-true}"
RESPONSE_LENGTH_MIN="${RESPONSE_LENGTH_MIN:-100}"
RESPONSE_LENGTH_CONSECUTIVE="${RESPONSE_LENGTH_CONSECUTIVE:-3}"
RESPONSE_LENGTH_POLL_SECONDS="${RESPONSE_LENGTH_POLL_SECONDS:-20}"

trap 'status=$?; printf "[prompt-stress] ERROR line=%s status=%s\n" "$LINENO" "$status" | tee -a "$MASTER_LOG" >&2' ERR
trap 'status=$?; printf "[prompt-stress] EXIT status=%s line=%s utc=%s\n" "$status" "$LINENO" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"' EXIT
trap 'printf "[prompt-stress] SIGNAL signal=TERM line=%s utc=%s\n" "$LINENO" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"; exit 143' TERM
trap 'printf "[prompt-stress] SIGNAL signal=HUP line=%s utc=%s\n" "$LINENO" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"; exit 129' HUP

PROMPT_SLUGS=(
  "sectioned_reasoning"
  "reasoning_before_json"
  "visual_checks"
)
PROMPT_FILES=(
  "$REPO_ROOT/rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_sectioned_reasoning.txt"
  "$REPO_ROOT/rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_reasoning_before_json.txt"
  "$REPO_ROOT/rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_visual_checks.txt"
)

extract_summary() {
  local log_path="$1"
  perl -ne '
    s/\e\[[0-9;?]*[ -\/]*[@-~]//g;
    s/\r/\n/g;
    for my $l (split /\n/) {
      $l =~ s/^\s*\([^)]*\)\s*//;
      next if $l =~ /Running step|Compute log probs|Train mini-batches|Update policy|Processed prompts|it\/s|█/;
      if ($l =~ /Step (25)\s*$/) {
        $cap=1; $step=$1; $val=0; $reward=0; $vresp=0; $ans=""; $ann=""; $overall=""; $resp="";
        next;
      }
      next unless $cap;
      if ($l =~ /^val:\s*$/) { $val=1; next; }
      if ($val && $l =~ /answer_reward_reward:\s*([0-9.eE+-]+)/) { $ans=$1; }
      if ($val && $l =~ /annotation_reward_reward:\s*([0-9.eE+-]+)/) { $ann=$1; }
      if ($val && $l =~ /overall_reward:\s*([0-9.eE+-]+)/) { $overall=$1; }
      if ($val && $l =~ /^reward:\s*$/) { $reward=1; next; }
      if ($reward && $l =~ /answer_reward:\s*([0-9.eE+-]+)/) { $ans=$1 if $ans eq ""; }
      if ($reward && $l =~ /annotation_reward:\s*([0-9.eE+-]+)/) { $ann=$1 if $ann eq ""; }
      if ($reward && $l =~ /overall:\s*([0-9.eE+-]+)/) { $overall=$1 if $overall eq ""; }
      if ($l =~ /^val_response_length:\s*$/) { $vresp=1; next; }
      if ($vresp && $l =~ /mean:\s*([0-9.eE+-]+)/) {
        $resp=$1;
        print "step=$step answer=$ans annotation=$ann overall=$overall val_resp_mean=$resp\n";
        exit;
      }
    }
  ' "$log_path" || true
}

extract_response_length_rows() {
  local log_path="$1"
  [[ -f "$log_path" ]] || return 0
  perl -pe 's/\e\[[0-9;?]*[ -\/]*[@-~]//g; s/\r/\n/g' "$log_path" | awk '
    /Step [0-9]+$/ {step=$NF; metric=""}
    /response_length:[[:space:]]*$/ {metric="resp"; mean=""; max=""; min=""; next}
    /(prompt_length:|global_seqlen:|reward:|timing_s:|annotation_assigned|val_response_length:)/ && $0 !~ /response_length:[[:space:]]*$/ {
      if (metric=="resp") metric=""
    }
    metric=="resp" && /mean:/ {mean=$NF}
    metric=="resp" && /max:/ {max=$NF}
    metric=="resp" && /min:/ {
      min=$NF
      if (step && mean) print step, mean, max, min
      metric=""
    }
  '
}

terminate_tree() {
  local pid="$1"
  local pgid
  pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d '[:space:]')"
  if [[ -n "$pgid" ]]; then
    kill -TERM "-$pgid" 2>/dev/null || true
    sleep 10
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL "-$pgid" 2>/dev/null || true
    fi
  else
    kill -TERM "$pid" 2>/dev/null || true
    sleep 5
    if kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  fi
}

monitor_response_length_guard() {
  local train_pid="$1"
  local run_log="$2"
  local slug="$3"
  local last_seen_step=0
  local below_count=0
  local rows step mean max_len min_len

  while kill -0 "$train_pid" 2>/dev/null; do
    rows="$(extract_response_length_rows "$run_log" | awk -v last="$last_seen_step" '$1 > last')"
    while read -r step mean max_len min_len; do
      [[ -n "${step:-}" ]] || continue
      last_seen_step="$step"
      if awk -v value="$mean" -v threshold="$RESPONSE_LENGTH_MIN" 'BEGIN { exit !(value < threshold) }'; then
        below_count=$((below_count + 1))
      else
        below_count=0
      fi
      printf '[prompt-stress] response_length slug=%s step=%s mean=%s max=%s min=%s below_count=%s threshold=%s\n' \
        "$slug" "$step" "$mean" "$max_len" "$min_len" "$below_count" "$RESPONSE_LENGTH_MIN" | tee -a "$MASTER_LOG"
      if [[ "$below_count" -ge "$RESPONSE_LENGTH_CONSECUTIVE" ]]; then
        printf '[prompt-stress] early_stop slug=%s reason=response_length_below_%s_for_%s_steps last_step=%s\n' \
          "$slug" "$RESPONSE_LENGTH_MIN" "$RESPONSE_LENGTH_CONSECUTIVE" "$step" | tee -a "$MASTER_LOG"
        terminate_tree "$train_pid"
        return 2
      fi
    done <<< "$rows"
    sleep "$RESPONSE_LENGTH_POLL_SECONDS"
  done
  return 0
}

printf '[prompt-stress] started_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"
printf '[prompt-stress] git_head=%s\n' "$(git rev-parse HEAD)" | tee -a "$MASTER_LOG"
printf '[prompt-stress] master_log=%s\n' "$MASTER_LOG" | tee -a "$MASTER_LOG"
printf '[prompt-stress] scratch_root=%s clean_checkpoints=%s\n' "$SCRATCH_ROOT" "$CLEAN_CHECKPOINTS" | tee -a "$MASTER_LOG"
printf '[prompt-stress] config=additive ann0.50 max_steps=25 val_freq=25 save_freq=25 h200 tp2 rollout128 n8 mb_update4 mb_exp8\n' | tee -a "$MASTER_LOG"
printf '[prompt-stress] early_stop_response_length enabled=%s threshold=%s consecutive_steps=%s poll_seconds=%s\n' \
  "$EARLY_STOP_ON_RESPONSE_LENGTH" "$RESPONSE_LENGTH_MIN" "$RESPONSE_LENGTH_CONSECUTIVE" "$RESPONSE_LENGTH_POLL_SECONDS" | tee -a "$MASTER_LOG"

for idx in "${!PROMPT_SLUGS[@]}"; do
  slug="${PROMPT_SLUGS[$idx]}"
  prompt_file="${PROMPT_FILES[$idx]}"
  run_stamp="${RUN_STAMP}_${slug}"
  experiment_name="trace_annotation_additive_ann0p50_${slug}_prompt_stress_h200_25step_${RUN_STAMP}"
  run_log="logs/rlvr/annotation_prompt_stress_additive_ann0p50_${slug}_25step_h200_${RUN_STAMP}.log"
  gpu_log="logs/rlvr/annotation_prompt_stress_additive_ann0p50_${slug}_25step_h200_${RUN_STAMP}_gpu.csv"
  ckpt_path="${SCRATCH_ROOT}/${experiment_name}"

  printf '\n[prompt-stress] run_start slug=%s utc=%s\n' "$slug" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"
  printf '[prompt-stress] prompt_file=%s\n' "$prompt_file" | tee -a "$MASTER_LOG"
  printf '[prompt-stress] run_log=%s\n' "$run_log" | tee -a "$MASTER_LOG"
  printf '[prompt-stress] gpu_log=%s\n' "$gpu_log" | tee -a "$MASTER_LOG"
  printf '[prompt-stress] checkpoint_scratch=%s\n' "$ckpt_path" | tee -a "$MASTER_LOG"

  printf 'timestamp,index,name,memory.used,utilization.gpu,utilization.memory,power.draw,temperature.gpu\n' > "$gpu_log"
  (
    while true; do
      nvidia-smi --query-gpu=timestamp,index,name,memory.used,utilization.gpu,utilization.memory,power.draw,temperature.gpu \
        --format=csv,noheader,nounits >> "$gpu_log" 2>/dev/null || true
      sleep 15
    done
  ) &
  gpu_sampler_pid=$!

  setsid env \
    RUN_STAMP="$run_stamp" \
    CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
    TRACE_ANNOTATION_FRACTION=0.50 \
    MAX_STEPS=25 \
    SAVE_FREQ=25 \
    VAL_FREQ=25 \
    SAVE_LIMIT=1 \
    VAL_BEFORE_TRAIN=false \
    FIND_LAST_CHECKPOINT=false \
    LOAD_CHECKPOINT_PATH=null \
    ROLLOUT_BATCH_SIZE=128 \
    ACTOR_GLOBAL_BATCH_SIZE=128 \
    ROLLOUT_N=8 \
    MAX_PROMPT_LENGTH=2048 \
    MAX_RESPONSE_LENGTH=2048 \
    VAL_BATCH_SIZE=1024 \
    N_GPUS=8 \
    TENSOR_PARALLEL_SIZE=2 \
    GPU_MEMORY_UTILIZATION=0.90 \
    MAX_NUM_BATCHED_TOKENS=32768 \
    ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE=8 \
    ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE=4 \
    REF_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE=8 \
    SYSTEM_PROMPT_FILE="$prompt_file" \
    EXPERIMENT_NAME="$experiment_name" \
    SAVE_CHECKPOINT_PATH="$ckpt_path" \
    scripts/run_trace_qwen25vl3b_easyr1_annotation_additive_nokl_tmpfs.sh \
    > "$run_log" 2>&1 &
  train_pid=$!

  early_stopped=false
  if [[ "$EARLY_STOP_ON_RESPONSE_LENGTH" == "true" ]]; then
    set +e
    monitor_response_length_guard "$train_pid" "$run_log" "$slug"
    monitor_status=$?
    set -e
    if [[ "$monitor_status" -eq 2 ]]; then
      early_stopped=true
    fi
  fi

  set +e
  wait "$train_pid"
  status=$?
  set -e
  if [[ "$early_stopped" == "true" ]]; then
    status=0
  fi

  kill "$gpu_sampler_pid" 2>/dev/null || true
  wait "$gpu_sampler_pid" 2>/dev/null || true

  summary="$(extract_summary "$run_log")"
  printf '[prompt-stress] run_done slug=%s status=%s early_stopped=%s utc=%s\n' "$slug" "$status" "$early_stopped" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"
  if [[ -n "$summary" ]]; then
    printf '[prompt-stress] summary slug=%s %s\n' "$slug" "$summary" | tee -a "$MASTER_LOG"
  else
    printf '[prompt-stress] summary slug=%s unavailable\n' "$slug" | tee -a "$MASTER_LOG"
  fi

  if [[ "$CLEAN_CHECKPOINTS" == "true" ]]; then
    rm -rf "$ckpt_path"
    printf '[prompt-stress] removed_checkpoint_scratch=%s\n' "$ckpt_path" | tee -a "$MASTER_LOG"
  fi

  if [[ "$status" -ne 0 ]]; then
    printf '[prompt-stress] aborting_after_failure slug=%s status=%s\n' "$slug" "$status" | tee -a "$MASTER_LOG"
    exit "$status"
  fi
done

printf '\n[prompt-stress] all_done utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$MASTER_LOG"

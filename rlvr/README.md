# RLVR Vero Port

This directory is the staged Vero-derived RLVR stack inside the TRACE repo.

Purpose:

- keep a Vero-derived RLVR stack at the canonical `rlvr/` path
- integrate TRACE-specific pieces into a Vero-shaped execution path
- preserve the previous TRACE RLVR stack under `rlvr_legacy/`

Current scope:

- vendored Vero training stack under `rlvr/verl/`
- vendored Vero reward code under `rlvr/vero_reward/`
- vendored prompt/config assets under `rlvr/examples/`
- TRACE dataset adapter under `rlvr/verl/utils/dataset/trace_rl_dataset.py`
- TRACE reward adapter under `rlvr/examples/reward_function/reward_trace.py`
- TRACE JSON system prompts under `rlvr/examples/prompts/`
- TRACE grouped solve metrics wired into the Vero PPO trainer path
- TRACE-style benchmark validation ported into the Vero PPO trainer path

TRACE-specific behavior now integrated on top of the Vero stack:

- `data.dataset_mode=trace` automatically selects the TRACE dataset adapter
- TRACE reward modes are `answer` and `answer_and_annotation`
- `TRACE_OUTPUT_MODE` is the common mode selector for prompt key, reward mode, and default system prompt
- `TRACE_OUTPUT_MODE=annotation` is accepted as a shorthand alias for `answer_and_annotation`
- TRACE outputs should end with a TRACE JSON object; reasoning may appear before that final object
- TRACE training metrics include grouped `zero_solve_*` and `perfect_solve_*`
- numeric TRACE reward breakdowns are surfaced as `reward/*` metrics in training

Temporary boundary:

- training-stack port work should happen here first
- the previous TRACE stack now lives in `rlvr_legacy/`
- TRACE benchmark-style validation assets and older launchers should be pulled over selectively as needed
- TRACE benchmark validation remains available through
  `data.validation_style=trace_benchmark`, but the default TRACE launcher now
  validates on the held-out TRACE split-v1 validation parquet.

Current EasyR1 paper-training path:

- active backend: `rlvr/easyr1_backend/`
- active reward adapter:
  `rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py`
- shared TRACE scorer: `trace/core/reward_scoring.py`
- reward-mode reference: `rlvr/TRACE_REWARD_MODES.md`
- generic no-KL Qwen2.5-VL-3B launcher:
  `scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh`
- answer-only wrapper:
  `scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh`
- answer-and-annotation gated wrapper:
  `scripts/run_trace_qwen25vl3b_easyr1_annotation_gated_nokl_tmpfs.sh`
- answer-and-annotation additive wrapper:
  `scripts/run_trace_qwen25vl3b_easyr1_annotation_additive_nokl_tmpfs.sh`
- all-1000-task IID tmpfs dataset builder:
  `scripts/prepare_trace_rlvr_all1000_iid_tmpfs.sh`
- the older `rlvr/verl/` path remains in-tree for legacy/reference runs; do not
  use it for new paper training unless explicitly requested

Current all-1000-task IID 500-step dataset recipe:

- train: `trace_rlvr_train_64000_all1000_seed42.parquet`
  - `1000` active tasks x `64` samples per task = `64,000` rows
  - supports `500` steps at `data.rollout_batch_size=128` before prompt reuse
- validation: `trace_rlvr_validation_iid_2000_all1000_seed1042.parquet`
  - `1000` active tasks x `2` samples per task = `2,000` rows
  - uses a different generation seed from train, so it is IID but non-overlapping by construction
- both parquets store answer-only and answer-and-annotation prompt columns, so
  the same files can drive answer-only, additive annotation, and gated annotation
  EasyR1 runs by changing `PROMPT_KEY` and reward-mode env vars
- these files are generated under `/dev/shm/trace_rlvr/datasets` by default;
  set `TRAIN_FILES` and `VAL_FILES` explicitly when launching training from them
- if a later run needs more than `500` steps without prompt reuse, build a new
  train parquet with a different `TRAIN_SEED` instead of continuing to cycle the
  same rows

Training launcher:

- generic TRACE VL RLVR launcher: `rlvr/examples/model_runs/run_trace_vl_rlvr.sh`
- experiment-plan wrapper: `scripts/run_trace_rlvr_experiment.sh`
- default Qwen2.5-VL-3B answer-mode split-v1 launcher:
  `rlvr/examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh`
- operational split-v1 training runbook:
  `docs/workflows/RLVR_TRAINING_RUNBOOK.md`
- compatibility 8-GPU Qwen3-VL-2B answer launcher: `rlvr/examples/model_runs/run_trace_qwen3vl_2b_answer.sh`
- generic launcher default model: `Qwen/Qwen2.5-VL-3B-Instruct`
- generic launcher default train split: `maveryn/trace@train`
- generic launcher default validation split: `maveryn/trace@validation`
- default `MAX_PROMPT_LENGTH` is model-aware in the launcher: `1536` for Qwen3-VL models and `2048` for Qwen2.5-VL models; set `MAX_PROMPT_LENGTH` explicitly to override
- default TRACE training `MAX_RESPONSE_LENGTH` is `4096`; set `MAX_RESPONSE_LENGTH` explicitly to override
- default validation generation `VAL_MAX_RESPONSE_LENGTH` is `2048`; set `VAL_MAX_RESPONSE_LENGTH` explicitly to override
- default reward mode: `answer`
- default prompt key: `prompt_answer`
- default output mode: `answer`
- default train batch: `256` prompts
- default rollouts per prompt: `8`
- default total training steps: `900`
- default checkpoint retention remains one actor checkpoint and one critic checkpoint
- default logging: `console` and `wandb` under project `trace`
- default W&B mode is `online`; set `WANDB_MODE=offline` only when you explicitly want a local offline run

Example:

```bash
cd /home/jovyan/work/trace/rlvr
bash examples/model_runs/run_trace_qwen25vl_3b_answer_split_v1.sh
```

Legacy curriculum probe:

- offline base-model rollout probe for curriculum construction: `rlvr/scripts/trace_curriculum_probe.py`
- legacy intended use: run the base Qwen3-VL-2B model over an older local
  TRACE train parquet with sampled rollouts, then use the emitted
  per-instance/per-task solve statistics to define task-wise or global
  curriculum bins
- defaults match the older curriculum answer-mode setup:
  - `prompt_key=prompt_answer`
  - `system_prompt=examples/prompts/trace_vero_json_system_prompt_answer.txt`
  - `trace_answer_scoring=legacy_strict`
  - `rollouts_per_prompt=32`
  - `tensor_parallel_size=1`
  - `replica_workers=0` meaning use all visible GPUs as single-GPU probe workers
  - `batch_size=1024` as the global prompt batch, split across replica workers
  - `prefetch_workers=1` to prepare the next batch while vLLM is generating the current one
- probe-only answer extraction is intentionally lenient:
  - first recover the final JSON object when present
  - otherwise fall back to valid JSON elsewhere in the response, including legacy `<answer>...</answer>` wrappers
  - the probe then scores the recovered payload with the same answer/annotation contracts used by training
  - this does not change training reward behavior

Example:

```bash
cd /home/jovyan/work/trace/rlvr
python scripts/trace_curriculum_probe.py \
  --parquet dataset/train/trace_rlvr_train_128k_all_tasks_verojson.parquet \
  --output-dir outputs/curriculum_probe/base_qwen3vl_2b_32x
```

Resume a partial sharded probe from the existing worker outputs under the same directory:

```bash
cd /home/jovyan/work/trace/rlvr
python scripts/trace_curriculum_probe.py \
  --parquet dataset/train/trace_rlvr_train_128k_all_tasks_verojson.parquet \
  --output-dir outputs/curriculum_probe/base_qwen3vl_2b_32x \
  --resume
```

Export a retained training subset from the completed probe using the current first-pass empirical band (`0.125 <= solve_rate <= 0.75`):

```bash
cd /home/jovyan/work/trace
python rlvr/scripts/export_curriculum_subset.py \
  --source-parquet rlvr/dataset/train/trace_rlvr_train_128k_all_tasks_verojson.parquet \
  --probe-jsonl rlvr/outputs/curriculum_probe/base_qwen3vl_2b_32x_tp1/per_instance.jsonl \
  --output-parquet rlvr/dataset/train/trace_rlvr_train_51k_solve_0125_0750_uniform.parquet \
  --min-solve-rate 0.125 \
  --max-solve-rate 0.75
```

The exported parquet keeps the original TRACE training rows plus probe metadata such as `solve_rate` and `positive_rollout_count`. The standard RLVR launcher already uses random dataloader sampling (`data.shuffle=true`), so pointing `TRAIN_FILES` at this retained parquet gives uniform random sampling inside the selected empirical range.

For the legacy retained-subset curriculum answer-mode setup, use:

```bash
cd /home/jovyan/work/trace/rlvr
TRACE_OUTPUT_MODE=answer \
TRAINER_EXPERIMENT_NAME=trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_$(date +%Y%m%d_%H%M%S) \
bash examples/model_runs/run_trace_qwen3vl_2b_answer_curriculum.sh
```

That launcher defaults to:

- `TRAIN_FILES=./dataset/train/trace_rlvr_train_51k_solve_0125_0750_uniform.parquet`
- `TRACE_ANSWER_SCORING=legacy_strict`
- `MAX_RESPONSE_LENGTH=4096`

Minimal TRACE knobs on the new stack:

- `data.dataset_mode=trace`
- `data.prompt_key=prompt_answer` or `data.prompt_key=prompt_answer_and_annotation`
- `data.trace_output_mode=answer` or `answer_and_annotation`
- `data.system_prompt=auto` uses the mode-specific system prompt under `./examples/prompts/`
- `custom_reward_function.path=./examples/reward_function/reward_trace.py`
- `custom_reward_function.name=compute_score`
- `custom_reward_function.reward_kwargs.trace_output_mode=answer` or `answer_and_annotation`
- `custom_reward_function.reward_kwargs.trace_reward_mode=auto` follows `trace_output_mode` by default
- `custom_reward_function.reward_kwargs.trace_answer_scoring=exact_json` by default; set `legacy_strict` to recover the older TRACE answer-matching semantics used by `strict_score_response(...)`
- `custom_reward_function.reward_kwargs.trace_format_weight=0.05` by default; set `TRACE_FORMAT_WEIGHT` to override it for both answer and answer-and-annotation modes
- RLVR export now strips the generic JSON-schema boilerplate line from `prompt_answer` and `prompt_answer_and_annotation`; the mode-specific system prompt carries the schema contract, while task-specific hints and examples stay in the user prompt
- RLVR export includes `query_id` and `scene_variant` when trace sidecars are available; retained curriculum parquets also keep per-question staged probe counts and solve rates
- TRACE format reward is binary: it is `1.0` only when the response ends with a JSON object whose keys match the expected mode-specific contract, otherwise `0.0`; it does not require `<think>` or `<answer>` tags.
- `reward/zero_reward` and grouped `rlvr_stats/zero_solve_*` / `perfect_solve_*` track task reward correctness, so a wrong but well-formed JSON answer does not count as a solve.
- `data.validation_style=standard`
- `data.val_files=maveryn/trace@validation`
- the default trace launcher config uses model-aware `data.max_prompt_length`
  and `data.max_response_length=4096` for TRACE training unless overridden
- external benchmark validation can still be enabled explicitly with
  `VALIDATION_STYLE=trace_benchmark` and benchmark parquet `VAL_FILES`.
- external benchmark validation uses the same answer-mode JSON system prompt as
  TRACE RLVR training: `data.val_prompt_key=prompt_answer`,
  `data.val_answer_key=answer_gt`, `data.val_disable_system_prompt=false`, and
  `data.val_format_prompt=null`; legacy rows still load through the dataset
  adapter's `prompt`/`ground_truth` fallback

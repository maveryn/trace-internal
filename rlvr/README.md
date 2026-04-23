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
- TRACE reward modes are `answer` and `answer_and_evidence`
- `TRACE_OUTPUT_MODE` is the common mode selector for prompt key, reward mode, and default system prompt
- `TRACE_OUTPUT_MODE=evidence` is accepted as a shorthand alias for `answer_and_evidence`
- TRACE outputs require TRACE JSON inside `<answer>...</answer>`; reasoning may appear outside the answer block
- TRACE training metrics include grouped `zero_solve_*` and `perfect_solve_*`
- numeric TRACE reward breakdowns are surfaced as `reward/*` metrics in training

Temporary boundary:

- training-stack port work should happen here first
- the previous TRACE stack now lives in `rlvr_legacy/`
- TRACE benchmark-style validation assets and older launchers should be pulled over selectively as needed
- TRACE benchmark validation is available through `data.validation_style=trace_benchmark`
- the active TRACE validation subset currently keeps 6 benchmarks under `rlvr/dataset/validation/`
- `mathverse_mini` and `countqa` are excluded for now
- launcher rebuild is in progress on top of this path; the 8-GPU answer launcher is available now

Training launcher:

- 8-GPU answer-reward launcher: `rlvr/examples/model_runs/run_trace_qwen3vl_2b_answer.sh`
- default model: `Qwen/Qwen3-VL-2B-Instruct`
- default reward mode: `answer`
- default prompt key: `prompt_answer`
- default output mode: `answer`
- default logging: `console` and `wandb` under project `trace_rlvr`
- default W&B mode is `online`; set `WANDB_MODE=offline` only when you explicitly want a local offline run

Example:

```bash
cd /home/jovyan/work/trace/rlvr
bash examples/model_runs/run_trace_qwen3vl_2b_answer.sh
```

Curriculum probe:

- offline base-model rollout probe for curriculum construction: `rlvr/scripts/trace_curriculum_probe.py`
- intended use: run the base Qwen3-VL-2B model over the TRACE train parquet with sampled rollouts, then use the emitted per-instance/per-task solve statistics to define task-wise or global curriculum bins
- defaults match the current answer-mode training setup:
  - `prompt_key=prompt_answer`
  - `system_prompt=examples/prompts/trace_vero_json_system_prompt_answer.txt`
  - `trace_answer_scoring=legacy_strict`
  - `rollouts_per_prompt=32`
  - `tensor_parallel_size=1`
  - `replica_workers=0` meaning use all visible GPUs as single-GPU probe workers
  - `batch_size=1024` as the global prompt batch, split across replica workers
  - `prefetch_workers=1` to prepare the next batch while vLLM is generating the current one
- probe-only answer extraction is intentionally lenient:
  - first recover JSON from `<answer>...</answer>` when present
  - otherwise fall back to valid JSON elsewhere in the response
  - the probe then normalizes that recovered payload back into `<answer>{...}</answer>` before scoring
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

For the current curriculum answer-mode training setup, use:

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
- `data.prompt_key=prompt_answer` or `data.prompt_key=prompt_answer_and_evidence`
- `data.trace_output_mode=answer` or `answer_and_evidence`
- `data.system_prompt=auto` uses the mode-specific system prompt under `./examples/prompts/`
- `custom_reward_function.path=./examples/reward_function/reward_trace.py`
- `custom_reward_function.name=compute_score`
- `custom_reward_function.reward_kwargs.trace_output_mode=answer` or `answer_and_evidence`
- `custom_reward_function.reward_kwargs.trace_reward_mode=auto` follows `trace_output_mode` by default
- `custom_reward_function.reward_kwargs.trace_answer_scoring=exact_json` by default; set `legacy_strict` to recover the older TRACE answer-matching semantics used by `strict_score_response(...)`
- `custom_reward_function.reward_kwargs.trace_format_weight=0.1`
- RLVR export now strips the generic JSON-schema boilerplate line from `prompt_answer` and `prompt_answer_and_evidence`; the mode-specific system prompt carries the schema contract, while task-specific hints and examples stay in the user prompt
- TRACE format reward checks for exactly one `<answer>...</answer>` block whose contents parse as JSON with the expected mode-specific keys; it no longer requires `<think>...</think>` tags.
- `reward/zero_reward` and grouped `rlvr_stats/zero_solve_*` / `perfect_solve_*` now track task reward correctness rather than format-weighted overall reward, so a wrong but well-formed JSON answer does not count as a solve.
- `data.validation_style=trace_benchmark`
- `data.val_files=[./dataset/validation/mathvista_mini.parquet, ./dataset/validation/mmstar.parquet, ./dataset/validation/charxiv_dq.parquet, ./dataset/validation/charxiv_rq.parquet, ./dataset/validation/embspatialbench.parquet, ./dataset/validation/blink.parquet]`
- external benchmark validation intentionally uses the legacy boxed validation prompt for comparability with prior TRACE numbers: `data.val_prompt_key=prompt`, `data.val_answer_key=ground_truth`, `data.val_disable_system_prompt=true`, and `data.val_format_prompt=./examples/format_prompt/math.jinja`

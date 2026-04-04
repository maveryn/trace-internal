# TRACE Training Scripts

This directory holds TRACE-specific RLVR launchers.

The shared TRACE training config lives here too:

- `trace-scripts/config_trace.yaml`

## Qwen2.5-VL 3B on the 128k TRACE parquet

Use `qwen2_5-3b-vl-trace-4gpu.sh` to train against the exported TRACE parquet with these defaults:

- `TRAIN_FILE=mydata/trace_train_128k_multivariant_hf.parquet`
- `HF_TRAIN_REPO=xashru/trace-rlvr-train-128k`
- `HF_TRAIN_SPLIT=train`
- `MODEL_PATH=Qwen/Qwen2.5-VL-3B-Instruct`
- `NUM_GPUS=4`
- `MAX_STEPS=10`
- `GPU_MEMORY_UTILIZATION=0.8`
- `WANDB_MODE=online`

TRACE train prompts stay dataset-native (`data.format_prompt=null`), while validation uses a separate runtime format prompt:

- `data.val_format_prompt=./examples/format_prompt/math.jinja`
- `data.val_format_prompt_variant=boxed_only`

The script runs a preflight check before launching training. It verifies:

- the local parquet exists, or the HF fallback repo can be loaded
- required TRACE columns are present
- sampled `answer_gt`, `evidence_gt`, and `reward_contract` values are valid JSON
- sampled images are usable, either from embedded bytes / HF `Image` payloads or from local paths on disk

If `TRAIN_FILE` points to a local parquet path and that file is missing, the launcher automatically falls back to:

- `${HF_TRAIN_REPO}@${HF_TRAIN_SPLIT}`

For a private HF dataset repo, export `HF_TOKEN` or `HUGGINGFACE_TOKEN` before launching.

If you want local-only logging for a run, override with `WANDB_MODE=offline`.

Example:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/qwen2_5-3b-vl-trace-4gpu.sh
```

Preflight only:

```bash
cd /home/jovyan/work/trace/rlvr
TRACE_PREFLIGHT_ONLY=1 bash trace-scripts/qwen2_5-3b-vl-trace-4gpu.sh
```

## Qwen3-VL 4B evidence+curriculum on 8 GPUs

Use `trace_qwen3_vl_4b_answer_evidence_curriculum_8gpu.sh` for the 8-GPU TRACE run with:

- `MODEL_PATH=Qwen/Qwen3-VL-4B-Instruct`
- `PROMPT_KEY=prompt_answer_and_evidence`
- `TRACE_REWARD_MODE=answer_and_evidence`
- `CURRICULUM_MODE=self_paced_ema`
- `NUM_GPUS=8`
- `MAX_STEPS=250`
- `VAL_FREQ=20`
- `SAVE_FREQ=20`

It defaults `CUDA_VISIBLE_DEVICES` to `0,1,2,3,4,5,6,7` if you do not set it yourself.

Example:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/trace_qwen3_vl_4b_answer_evidence_curriculum_8gpu.sh
```

## Qwen3-VL 2B Instruct evidence on 8 GPUs

Use `trace_qwen3_vl_2b_instruct_answer_evidence_8gpu.sh` for an 8-GPU TRACE run with:

- `MODEL_PATH=Qwen/Qwen3-VL-2B-Instruct`
- `PROMPT_KEY=prompt_answer_and_evidence`
- `TRACE_REWARD_MODE=answer_and_evidence`
- `NUM_GPUS=8`
- `GPU_MEMORY_UTILIZATION=0.8`
- `ROLLOUT_N=8`
- `MAX_RESPONSE_LENGTH=1024`
- `ACTOR_GLOBAL_BATCH_SIZE=128`
- `ACTOR_MICRO_BATCH_SIZE_UPDATE=4`
- `ACTOR_MICRO_BATCH_SIZE_EXPERIENCE=4`
- `PADDING_FREE=false`
- `USE_TORCH_COMPILE=false`

It defaults `CUDA_VISIBLE_DEVICES` to `0,1,2,3,4,5,6,7` if you do not set it yourself.

Example:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/trace_qwen3_vl_2b_instruct_answer_evidence_8gpu.sh
```

## Qwen3.5-2B-Base evidence on 8 GPUs

Use `trace_qwen3_5_2b_base_answer_evidence_8gpu.sh` for an 8-GPU TRACE run with:

- `MODEL_PATH=Qwen/Qwen3.5-2B-Base`
- `PROMPT_KEY=prompt_answer_and_evidence`
- `TRACE_REWARD_MODE=answer_and_evidence`
- `NUM_GPUS=8`
- `GPU_MEMORY_UTILIZATION=0.8`
- `ROLLOUT_N=8`
- `MAX_RESPONSE_LENGTH=1536`
- `VAL_MAX_TOKENS=2048`
- `PADDING_FREE=false`
- `USE_TORCH_COMPILE=false`

It defaults `CUDA_VISIBLE_DEVICES` to `0,1,2,3,4,5,6,7` if you do not set it yourself.

Example:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/trace_qwen3_5_2b_base_answer_evidence_8gpu.sh
```

## Qwen3.5-0.8B-Base evidence on 8 GPUs

Use `trace_qwen3_5_0p8b_base_answer_evidence_8gpu.sh` for an 8-GPU TRACE run with:

- `MODEL_PATH=Qwen/Qwen3.5-0.8B-Base`
- `PROMPT_KEY=prompt_answer_and_evidence`
- `TRACE_REWARD_MODE=answer_and_evidence`
- `NUM_GPUS=8`
- `GPU_MEMORY_UTILIZATION=0.8`
- `ROLLOUT_N=8`
- `MAX_RESPONSE_LENGTH=1536`
- `VAL_MAX_TOKENS=2048`
- `ACTOR_GLOBAL_BATCH_SIZE=128`
- `ACTOR_MICRO_BATCH_SIZE_UPDATE=4`
- `ACTOR_MICRO_BATCH_SIZE_EXPERIENCE=4`
- `PADDING_FREE=false`
- `USE_TORCH_COMPILE=false`

It defaults `CUDA_VISIBLE_DEVICES` to `0,1,2,3,4,5,6,7` if you do not set it yourself.

Example:

```bash
cd /home/jovyan/work/trace/rlvr
bash trace-scripts/trace_qwen3_5_0p8b_base_answer_evidence_8gpu.sh
```

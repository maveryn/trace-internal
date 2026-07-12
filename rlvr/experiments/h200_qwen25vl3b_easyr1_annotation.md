# 8x H200 Qwen2.5-VL-3B EasyR1 Annotation Profile

This profile records the 8x H200 configuration used for the TRACE
Qwen2.5-VL-3B answer-and-annotation EasyR1 ablation on 2026-07-12. Use it as
the starting point for similar fully NVLinked 8x H200 hosts.

The active runbook remains the source of truth for the launch workflow:

```text
docs/workflows/TRACE_ANNOTATION_ABLATION_RUNBOOK.md
```

## Machine Profile

Observed host:

```text
hostname: shadecloud
GPU count: 8
GPU model: NVIDIA H200
GPU memory: 143771 MiB per GPU, about 140 GiB usable
driver: 580.126.09
nvidia-smi CUDA version: 13.0
PyTorch CUDA version: 12.4
CPU: AMD EPYC 9654, 176 visible CPUs
NUMA nodes: 1
system memory: about 1.4 TiB
/dev/shm: 714 GiB tmpfs
```

GPU topology was a full H200 NVLink mesh: every GPU pair among GPU0-GPU7 showed
`NV18` in `nvidia-smi topo -m`. Treat this profile as an 8-GPU profile only for
hosts with similarly broad NVLink connectivity. If the topology is mostly
`PHB`, `PXB`, `PIX`, or `SYS`, do not assume these settings will perform well.

Software versions observed:

```text
torch 2.6.0+cu124
transformers 4.57.6
vllm 0.8.5
ray 2.47.1
```

## Training Profile

Model and backend:

```text
backend: rlvr/easyr1_backend
model: Qwen/Qwen2.5-VL-3B-Instruct
trainer: EasyR1 / verl.trainer.main
strategy: FSDP actor with vLLM rollout
algorithm: GRPO
KL: disabled
actor LR: 1e-6
LR schedule: constant, no warmup
vision tower: unfrozen
gradient checkpointing: enabled
torch compile: enabled
actor parameter offload: true
actor optimizer offload: true
```

Dataset and prompt mode:

```text
train: maveryn/trace@train
validation: maveryn/trace@validation
prompt_key: prompt_answer_and_annotation
system_prompt_file: rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation.txt
answer_key: answer_gt
max_prompt_length: 2048
max_response_length: 2048
```

GPU and rollout settings:

```text
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
trainer.n_gpus_per_node=8
worker.rollout.tensor_parallel_size=2
worker.rollout.gpu_memory_utilization=0.90
worker.rollout.max_num_batched_tokens=32768
data.rollout_batch_size=128
worker.rollout.n=8
worker.actor.global_batch_size=128
data.val_batch_size=1024
```

This yields:

```text
prompts per train step: 128
rollouts per prompt: 8
responses per train step: 1024
approx responses per GPU: 128
```

Selected H200 microbatch settings:

```text
worker.actor.micro_batch_size_per_device_for_update=4
worker.actor.micro_batch_size_per_device_for_experience=8
worker.ref.micro_batch_size_per_device_for_experience=8
```

Do not change these at the same time as rollout batch size, rollout count,
learning rate, reward weights, tensor parallel size, or vLLM memory settings.
Tune one axis at a time.

## Reward Settings

The additive 0.50 annotation ablation used:

```text
TRACE_OUTPUT_MODE=answer_and_annotation
TRACE_REWARD_MODE=answer_and_annotation
TRACE_ANNOTATION_REWARD_FORMULA=additive
TRACE_ANNOTATION_FRACTION=0.5
trace_answer_weight=0.5
trace_annotation_weight=0.5
trace_format_weight=0.05
```

The optimized scalar is:

```text
overall = 0.95 * (0.5 * answer_reward + 0.5 * annotation_reward) + 0.05 * format_reward
```

The same GPU and microbatch profile should also apply to gated annotation runs
with the same model, batch, rollout, and sequence-length settings, because only
the reward calculation changes.

## Actual Run Provenance

Original additive 0.50 run:

```text
experiment_name: trace_annotation_additive_ann0p50_h200_200step_20260712T005627Z
wandb project: trace_easyr1
wandb run id: bsu1ijpn
wandb url: https://wandb.ai/llm-reasoning-rl/trace_easyr1/runs/bsu1ijpn
original log: logs/rlvr/annotation_additive_ann0p50_200step_h200_20260712T005627Z.log
original checkpoint root: /dev/shm/trace_rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_h200_200step_20260712T005627Z
```

The first run produced a valid step-100 checkpoint:

```text
/dev/shm/trace_rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_h200_200step_20260712T005627Z/global_step_100
```

After microbatch smoke tests, training was resumed from `global_step_100` to
continue toward step 200 with the selected 4/8 actor microbatch settings:

```text
resume log: logs/rlvr/annotation_additive_ann0p50_200step_h200_mb4x8_resume100_to200_20260712T034801Z.log
resume checkpoint root: /dev/shm/trace_rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_h200_200step_20260712T005627Z_mb4x8_resume100_to200_20260712T034801Z
trainer.load_checkpoint_path: /dev/shm/trace_rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_h200_200step_20260712T005627Z/global_step_100
trainer.max_steps: 200
```

W&B was resumed into the original run with:

```text
WANDB_RUN_ID=bsu1ijpn
WANDB_RESUME=must
WANDB_MODE=online
```

`WANDB_RESUME=must` is intentional: if W&B cannot attach to the existing run, it
should fail instead of creating a separate dashboard run. The original W&B run
already had a few logged points after step 100 before the process was stopped,
so resuming from the step-100 checkpoint can overlap dashboard history around
steps 101-104.

## H200 Microbatch Tuning Result

The baseline H100-era actor microbatch settings were:

```text
worker.actor.micro_batch_size_per_device_for_update=1
worker.actor.micro_batch_size_per_device_for_experience=2
```

On this H200 host, update-side HBM headroom was large. Baseline around steps
90-99 of the original run:

```text
time_per_step: about 72.1s
generation: about 13.0s
reward: about 0.84s
update_actor: about 43.2s
max_memory_allocated_gb: about 11.0
max_memory_reserved_gb: about 45.8
```

Two-step resume smokes from the original step-100 checkpoint:

```text
4/8 smoke:
  actor update microbatch: 4
  actor experience microbatch: 8
  avg time_per_step: about 66.6s
  avg update_actor: about 33.6s
  avg max_memory_allocated_gb: about 27.9
  avg max_memory_reserved_gb: about 74.4
  result: stable

8/16 smoke:
  actor update microbatch: 8
  actor experience microbatch: 16
  avg time_per_step: about 66.8s
  avg update_actor: about 33.1s
  avg max_memory_allocated_gb: about 48.3
  avg max_memory_reserved_gb: about 97.8
  result: stable, but not materially faster than 4/8
```

Decision:

```text
Use 4/8 for the 8x H200 Qwen2.5-VL-3B profile.
```

Rationale: 8/16 used much more PyTorch reserved memory for only a negligible
update-time gain and no end-to-end step-time improvement. 4/8 preserved more
headroom for long image/token batches while still reducing actor update time by
roughly 9-10 seconds versus the original 1/2 settings.

## Launch Notes

The generic launcher used to hardcode the actor microbatch settings. It now
accepts environment overrides while preserving the same defaults:

```text
ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE=2
ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE=1
```

For H200 runs that use the selected 4/8 profile, set:

```text
ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_UPDATE=4
ACTOR_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE=8
REF_MICRO_BATCH_SIZE_PER_DEVICE_FOR_EXPERIENCE=8
```

Minimum override set for this profile:

```text
worker.actor.micro_batch_size_per_device_for_update=4
worker.actor.micro_batch_size_per_device_for_experience=8
worker.ref.micro_batch_size_per_device_for_experience=8
worker.rollout.gpu_memory_utilization=0.90
worker.rollout.max_num_batched_tokens=32768
worker.rollout.tensor_parallel_size=2
data.rollout_batch_size=128
worker.rollout.n=8
data.max_prompt_length=2048
data.max_response_length=2048
data.val_batch_size=1024
trainer.n_gpus_per_node=8
```

For a 200-step continuation from a known checkpoint:

```text
trainer.load_checkpoint_path=<checkpoint_root>/global_step_100
trainer.max_steps=200
trainer.find_last_checkpoint=true
```

When resuming a W&B run, set:

```text
WANDB_RUN_ID=<existing_run_id>
WANDB_RESUME=must
```

Prefer a fresh local `trainer.save_checkpoint_path` for resumed/tuned
continuations if preserving root-level `experiment_log.jsonl` and
`generations.log` from the original checkpoint directory matters. EasyR1 opens
those root-level files in write mode under the save checkpoint path.

## Monitoring Commands

```bash
cd /home/shadeform/trace
LOG=logs/rlvr/annotation_additive_ann0p50_200step_h200_mb4x8_resume100_to200_20260712T034801Z.log

tail -f "$LOG"
rg -n "Step [0-9]+$|Running step:" "$LOG" | tail -40
tail -n 300000 "$LOG" \
  | egrep "time_per_step|gen:|reward:|update_actor|max_memory_allocated_gb|max_memory_reserved_gb" \
  | tail -120
nvidia-smi
```

For a live utilization sample:

```bash
nvidia-smi dmon -s pucvmet -d 5 -c 12
```

## Stability Checks Before Reuse

Before using this profile on another host:

1. Confirm all 8 GPUs are H200-class devices with about 140 GiB each.
2. Confirm `nvidia-smi topo -m` shows broad `NV#` links across the selected
   GPU set, ideally `NV18` for all pairs.
3. Confirm `/dev/shm` has enough capacity for Ray, HF caches, W&B, and
   checkpoint staging.
4. Run a 1-2 step smoke with the intended reward mode and batch settings.
5. Check for OOM, NCCL, Ray, HF, and W&B errors before launching a full run.

# TRACE Annotation Ablation Summary, 2026-07-13

This report summarizes the 8x H200 Qwen2.5-VL-3B EasyR1 answer-and-annotation
ablations run around 2026-07-12 and 2026-07-13. The H200 machine and base
training profile are documented in:

```text
rlvr/experiments/h200_qwen25vl3b_easyr1_annotation.md
```

The common H200 profile for the later runs was:

```text
model: Qwen/Qwen2.5-VL-3B-Instruct
train: maveryn/trace@train
validation: maveryn/trace@validation
prompt_key: prompt_answer_and_annotation
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
N_GPUS=8
TENSOR_PARALLEL_SIZE=2
GPU_MEMORY_UTILIZATION=0.90
MAX_NUM_BATCHED_TOKENS=32768
ROLLOUT_BATCH_SIZE=128
ROLLOUT_N=8
MAX_PROMPT_LENGTH=2048
MAX_RESPONSE_LENGTH=2048
VAL_BATCH_SIZE=1024
actor microbatch update/experience: 4/8
ref microbatch experience: 8
```

Use `answer_reward` and `annotation_reward` for cross-run interpretation. The
optimized scalar `overall` also includes format reward and changes with reward
formula/weights.

## Completed Longer Runs

| run | prompt | reward | status | step 100 answer | step 100 annotation | step 100 val response mean | step 200 answer | step 200 annotation | step 200 val response mean | notes |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| additive 0.50 | old/default annotation prompt | additive, 0.50 annotation | complete to 200 | 0.308 | 0.268 | 76.483 | 0.325 | 0.347 | 64.904 | Best annotation reward among the completed longer runs, but validation response length stayed short. |
| gated 0.25 | old/default annotation prompt | gated, 0.25 annotation | stopped after step 100 checkpoint; last observed train step 116 | 0.330 | 0.145 | 50.588 | n/a | n/a | n/a | Response length collapsed early and stayed around 50 tokens. |
| gated 0.25 | prompt-A/default revised prompt | gated, 0.25 annotation | stopped after step 100 checkpoint | 0.292 | 0.074 | 337.927 | n/a | n/a | n/a | Response length stayed high, but annotation reward was weak. |
| gated 0.50 | old/default annotation prompt | gated, 0.50 annotation | reached global_step_200 checkpoint; final step-200 validation metrics not found | 0.328 | 0.179 | 55.156 | n/a | n/a | n/a | Step-200 checkpoint exists, but no complete step-200 validation block was found. |
| gated 0.50 | prompt-A/default revised prompt | gated, 0.50 annotation | complete to 200 | 0.320 | 0.162 | 48.908 | 0.343 | 0.283 | 50.850 | Better step-200 answer/annotation than step 100, but response length collapsed. |
| additive 0.25 | prompt-A/default revised prompt | additive, 0.25 annotation | complete to 100 | 0.287 | 0.245 | 83.348 | n/a | n/a | n/a | Annotation improved versus gated 0.25 prompt-A, but response length still shortened. |

Selected log/checkpoint provenance:

```text
additive 0.50 old/default:
  logs/rlvr/annotation_additive_ann0p50_200step_h200_20260712T005627Z.log
  logs/rlvr/annotation_additive_ann0p50_200step_h200_mb4x8_resume100_to200_20260712T034801Z.log

gated 0.25 old/default:
  logs/rlvr/annotation_gated_ann0p25_200step_h200_20260712T140421Z.log

gated 0.25 prompt-A:
  logs/rlvr/annotation_gated_ann0p25_prompt_a_200step_h200_20260712T161153Z.log

gated 0.50 old/default:
  logs/rlvr/annotation_gated_ann0p50_200step_h200_20260712T054048Z.log

gated 0.50 prompt-A:
  logs/rlvr/annotation_gated_ann0p50_prompt_a_200step_h200_20260712T182026Z.log

additive 0.25 prompt-A:
  logs/rlvr/annotation_additive_ann0p25_prompt_a_100step_h200_20260712T222318Z.log
```

## Prompt Stress Test, Additive 0.50

Because several annotation runs learned short responses, three alternate
annotation system prompts were tested for 25 steps with additive 0.50 reward.
The launcher was:

```text
scripts/run_trace_qwen25vl3b_easyr1_annotation_prompt_stress_additive_ann0p50_h200.sh
```

The master log was:

```text
logs/rlvr/annotation_prompt_stress_additive_ann0p50_25step_h200_20260713T005355Z.log
```

The launcher ran prompt variants sequentially and stopped a variant early if
the train response-length mean was below 100 for three consecutive steps.

| prompt variant | prompt file | status | final train step | final train response mean | train answer | train annotation | train overall | validation response mean | validation answer | validation annotation | validation overall | W&B run |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| sectioned_reasoning | `rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_sectioned_reasoning.txt` | completed | 25 | 180.801 | 0.203 | 0.068 | 0.177 | 205.709 | 0.258 | 0.086 | 0.212 | `dlad4ap9` |
| reasoning_before_json | `rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_reasoning_before_json.txt` | completed | 25 | 205.642 | 0.217 | 0.067 | 0.183 | 243.364 | 0.250 | 0.086 | 0.209 | `7goziv5o` |
| visual_checks | `rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_visual_checks.txt` | early-stopped | 16 | 92.681 | 0.207 | 0.058 | 0.174 | n/a | n/a | n/a | n/a | `1mgk48ig` |

Response-length behavior:

| prompt variant | early response means | final response means | interpretation |
| --- | --- | --- | --- |
| sectioned_reasoning | step 1: 138.478; step 5: 165.175 | train step 25: 180.801; validation: 205.709 | Best overall candidate: response length stayed healthy and validation reward was slightly best. |
| reasoning_before_json | step 1: 262.310; step 5: 271.789 | train step 25: 205.642; validation: 243.364 | Also viable, with longer responses, but train response length trended downward. |
| visual_checks | step 1: 207.584; step 5: 188.312 | stopped at step 16 after 97.611, 87.617, 92.681 | Not viable for full run; it crossed the response-length guard. |

Decision: use `sectioned_reasoning` for the next longer additive 0.50 run. It
preserved response length without sacrificing validation answer/annotation
relative to the other 25-step prompt variants.

The `sectioned_reasoning` prompt text is:

```text
You are a helpful, conversational assistant tasked with answering a question about an image.

Reason carefully from the image and the question to determine the answer and the requested annotation.

Write your response in two parts:
Reasoning: explain how you determine the answer and where the annotation should be placed.
Final JSON: provide only the final JSON object.

The annotation must follow the format requested by the prompt and use image pixel coordinates.

Final JSON format:
{"answer": ..., "annotation": ...}
```

## Current Follow-Up Run

The selected `sectioned_reasoning` prompt was started as a 100-step additive
0.50 run with a retained final checkpoint:

```text
experiment_name: trace_annotation_additive_ann0p50_sectioned_reasoning_h200_100step_20260713T023435Z
log: logs/rlvr/annotation_additive_ann0p50_sectioned_reasoning_100step_h200_20260713T023435Z.log
wandb: https://wandb.ai/llm-reasoning-rl/trace_easyr1/runs/4rblro95
checkpoint root: /dev/shm/trace_rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_sectioned_reasoning_h200_100step_20260713T023435Z
MAX_STEPS=100
SAVE_FREQ=100
VAL_FREQ=100
```

Initial health through step 9:

| step | response mean | response max | answer | annotation | overall |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 138.478 | 2048 | 0.169 | 0.053 | 0.146 |
| 2 | 164.575 | 2048 | 0.186 | 0.062 | 0.160 |
| 3 | 136.156 | 2048 | 0.161 | 0.050 | 0.143 |
| 4 | 142.590 | 2048 | 0.156 | 0.049 | 0.139 |
| 5 | 153.403 | 1984 | 0.158 | 0.048 | 0.140 |
| 6 | 139.472 | 2048 | 0.176 | 0.045 | 0.150 |
| 7 | 138.707 | 1977 | 0.188 | 0.064 | 0.166 |
| 8 | 146.316 | 1731 | 0.181 | 0.057 | 0.159 |
| 9 | 145.038 | 2048 | 0.158 | 0.069 | 0.153 |

No OOM, Ray, or traceback errors were observed during startup and the first
nine train steps.

## Recommendations

- Prefer `sectioned_reasoning` for the next 100/200-step additive 0.50
  annotation run.
- Do not use `visual_checks` for full training.
- Treat the old/default annotation prompt and gated 0.50 prompt-A runs as
  response-length-collapse baselines.
- Keep comparing answer reward and annotation reward separately; do not use
  `overall` alone when comparing answer-only, gated, and additive settings.
- If the 100-step `sectioned_reasoning` run maintains response length and
  improves validation reward, continue the same config to 200 steps before
  adding another reward-weight or prompt axis.

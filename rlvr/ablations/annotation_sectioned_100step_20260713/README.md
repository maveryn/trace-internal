# Annotation Sectioned-Reasoning 100-Step Ablation, 2026-07-13

This snapshot compares the latest Qwen2.5-VL-3B answer-and-annotation
100-step ablation pair run on the 8x H200 host with the sectioned-reasoning
annotation prompt. Both runs used the same model, dataset, prompt key, system
prompt, batch/rollout settings, and H200 microbatch profile; only the
annotation reward formula changed.

## Files

- `run_metadata.csv` - run IDs, logs, W&B IDs, checkpoint paths, and shared
  launch config.
- `train_metrics.csv` - per-step train metrics parsed from the EasyR1 logs.
- `train_window_summary.csv` - averaged train metrics for steps 1-10, 40-50,
  and 90-99.
- `validation_summary.csv` - final validation metrics at `global_step_100`.

The EasyR1 logs print complete train metric blocks through logged train step
`99`, then emit a terminal `Step 100` progress label and run validation/save at
`global_step_100`. The CSV keeps only complete train metric rows.

## Shared Config

```text
model: Qwen/Qwen2.5-VL-3B-Instruct
train: maveryn/trace@train
validation: maveryn/trace@validation
prompt_key: prompt_answer_and_annotation
system_prompt_file: rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_sectioned_reasoning.txt
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
SAVE_FREQ=100
VAL_FREQ=100
MAX_STEPS=100
```

The sectioned-reasoning prompt was:

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

## Run Provenance

| run | formula | W&B run | source log | checkpoint status |
| --- | --- | --- | --- | --- |
| additive 0.50 sectioned | additive | `4rblro95` | `logs/rlvr/annotation_additive_ann0p50_sectioned_reasoning_100step_h200_20260713T023435Z.log` | `global_step_100` present; same root later continued to `global_step_500` |
| gated 0.50 sectioned | gated | `7hfs7lb0` | `logs/rlvr/annotation_gated_ann0p50_sectioned_reasoning_100step_h200_20260713T043748Z.log` | `global_step_100` was saved during the run but later deleted during `/dev/shm` cleanup; log retained |

## Validation At Global Step 100

| run | answer reward | annotation reward | overall | val response mean | val response max | format reward | annotation parse ok | annotation IoU mean | annotation similarity mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| additive 0.50 sectioned | 0.304 | 0.179 | 0.279 | 159.046 | 2048 | 0.995 | 0.968 | 0.245 | 0.176 |
| gated 0.50 sectioned | 0.305 | 0.087 | 0.215 | 129.623 | 873 | 1.000 | 0.960 | 0.132 | 0.044 |

Validation interpretation: answer reward was effectively tied at step 100.
Additive 0.50 produced about 2.1x the annotation reward of gated 0.50
(`0.179` vs `0.087`) and kept longer validation responses
(`159.046` vs `129.623` mean tokens).

## Train Trend

Window values are averages over per-step EasyR1 metrics.

| run | window | response mean | answer reward | annotation reward | overall | gen sec | update sec | total sec/step |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| additive 0.50 sectioned | 1-10 | 145.305 | 0.172 | 0.056 | 0.152 | 19.237 | 36.572 | 71.197 |
| additive 0.50 sectioned | 40-50 | 160.215 | 0.215 | 0.076 | 0.188 | 15.649 | 36.232 | 66.759 |
| additive 0.50 sectioned | 90-99 | 155.745 | 0.267 | 0.126 | 0.236 | 15.320 | 35.627 | 65.452 |
| gated 0.50 sectioned | 1-10 | 161.256 | 0.175 | 0.054 | 0.133 | 19.082 | 37.015 | 71.402 |
| gated 0.50 sectioned | 40-50 | 163.054 | 0.217 | 0.061 | 0.163 | 14.653 | 36.241 | 66.076 |
| gated 0.50 sectioned | 90-99 | 131.854 | 0.275 | 0.065 | 0.195 | 11.103 | 35.522 | 62.148 |

Train interpretation: both runs improved answer reward over the first 100
steps. The additive run also increased annotation reward from `0.056` in steps
1-10 to `0.126` in steps 90-99. The gated run's annotation reward moved much
less, from `0.054` to `0.065`, while its response length dropped more sharply
late in training.

## Notes

- `overall` is not directly comparable as pure answer accuracy because it
  includes formula-dependent task reward plus format reward. Use
  `answer_reward` and `annotation_reward` for cross-run interpretation.
- Gated reward only credits annotation after a correct answer, so a lower
  annotation reward can reflect both weaker annotation behavior and fewer
  annotation-credit opportunities.
- The deleted gated checkpoint means the gated 0.50 sectioned model cannot be
  merged from this run unless the checkpoint is restored from backup or rerun.

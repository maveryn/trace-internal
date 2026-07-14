# Qwen2.5-VL-7B Additive Annotation 0.50 Sectioned Run, 2026-07-14

This snapshot records the Qwen2.5-VL-7B TRACE answer-and-annotation RLVR run
trained with additive annotation reward at annotation fraction `0.50` and the
sectioned-reasoning annotation system prompt. The run was executed on the 8x
H200 host as three resumed launches that shared the same W&B run ID and core
training config.

## Files

- `run_metadata.csv` - launch-level provenance, resume chain, checkpoint paths,
  W&B ID, and config values that distinguish the three launches.
- `resolved_config_by_stage.json` - selected fields parsed from each launch's
  resolved EasyR1 config block.
- `train_metrics.csv` - per-step train metrics parsed from the EasyR1 logs for
  logged train steps `1` through `499`.
- `train_window_summary.csv` - averaged train metrics for windows before the
  main validation checkpoints.
- `validation_summary.csv` - validation metrics at global steps `100`, `200`,
  `300`, `400`, plus checkpoint/HF status for step `500`.

The final `global_step_500` checkpoint was saved and merged to Hugging Face, but
the log only shows step-500 validation starting; it does not expose a completed
step-500 validation metric block. Use step `400` for the latest completed
validation metrics and step `499` or the `490-499` train window for terminal
training behavior.

## Shared Config

```text
model: Qwen/Qwen2.5-VL-7B-Instruct
train: maveryn/trace@train
validation: maveryn/trace@validation
prompt_key: prompt_answer_and_annotation
system_prompt_file: rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_sectioned_reasoning.txt
reward mode: answer_and_annotation
annotation reward formula: additive
annotation fraction / weight: 0.50
answer weight: 0.50
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
actor global batch size: 128
actor microbatch update/experience: 4/8
ref microbatch experience: 8
ppo_epochs: 1
learning rate: 1e-6
gradient checkpointing: true
torch compile: true
freeze vision tower: false
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

| stage | run id | W&B run | max steps | save limit | load checkpoint | save checkpoint |
| --- | --- | --- | ---: | ---: | --- | --- |
| 0-100 | `qwen25vl7b_additive_ann0p50_sectioned_step100` | `ym2gx1ne` | 100 | 1 | `null` | `/dev/shm/trace_rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_sectioned_reasoning_qwen25vl7b_h200_100step_20260713T140237Z` |
| 100-200 | `qwen25vl7b_additive_ann0p50_sectioned_resume100_to200` | `ym2gx1ne` | 200 | 1 | `/dev/shm/trace_rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_sectioned_reasoning_qwen25vl7b_h200_100step_20260713T140237Z/global_step_100` | `/home/shadeform/trace/checkpoints/rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_sectioned_reasoning_qwen25vl7b_h200_resume100_to200_20260713T173224Z` |
| 200-500 | `qwen25vl7b_additive_ann0p50_sectioned_resume200_to500` | `ym2gx1ne` | 500 | 2 | `/home/shadeform/trace/checkpoints/rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_sectioned_reasoning_qwen25vl7b_h200_resume100_to200_20260713T173224Z/global_step_200` | `/home/shadeform/trace/checkpoints/rlvr/easyr1_checkpoints/trace_annotation_additive_ann0p50_sectioned_reasoning_qwen25vl7b_h200_resume200_to500_20260713T201436Z` |

The resolved trainer `experiment_name` stayed
`trace_annotation_additive_ann0p50_sectioned_reasoning_qwen25vl7b_h200_100step_20260713T140237Z`
across resumed launches. The run IDs above are local summary identifiers used to
separate the physical launch configs.

## Validation Summary

| global step | status | answer reward | annotation reward | overall | val response mean | val response max | checkpoint present |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 100 | complete | 0.372 | 0.322 | 0.380 | 301.963 | 2048.0 | true |
| 200 | complete | 0.431 | 0.401 | 0.445 | 279.604 | 1558.5 | true |
| 300 | complete | 0.429 | 0.441 | 0.463 | 358.948 | 2048.0 | false |
| 400 | complete | 0.455 | 0.457 | 0.483 | 411.604 | 2048.0 | true |
| 500 | started_no_final_metrics | NA | NA | NA | NA | NA | true |

Step `300` validation completed, but its checkpoint was later removed by the
step `200-500` launch's `save_limit=2`. Step `400` and `500` checkpoints are
present locally. The merged step-500 Hugging Face model is:

```text
https://huggingface.co/maveryn/trace-qwen25vl7b-rlvr-ann-additive-0p50-sectioned-step500
```

That HF repo was verified private at upload time.

## Train Trend

Window values are averages over complete train metric rows. The terminal
`490-499` window is the best available end-of-run train view because no step-500
train metric row is emitted after checkpoint save.

| window | response mean | answer reward | annotation reward | overall | gen s | update actor s | total s/step |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1-10 | 207.103 | 0.283 | 0.116 | 0.238 | 19.557 | 48.257 | 85.470 |
| 90-99 | 301.828 | 0.343 | 0.283 | 0.347 | 18.533 | 49.070 | 85.556 |
| 190-199 | 277.737 | 0.433 | 0.399 | 0.445 | 19.716 | 47.857 | 85.432 |
| 290-299 | 359.056 | 0.451 | 0.447 | 0.477 | 20.715 | 49.872 | 88.927 |
| 390-399 | 402.020 | 0.446 | 0.444 | 0.472 | 21.618 | 50.014 | 88.813 |
| 490-499 | 340.018 | 0.455 | 0.471 | 0.490 | 20.378 | 49.787 | 87.003 |

Interpretation: answer reward improved sharply by step 200 and then moved more
slowly; annotation reward continued to improve through the terminal train
window. Validation response length grew through step 400, while train response
length in the final `490-499` window came back down from the `390-399` window.

## Notes

- Use `answer_reward` and `annotation_reward` for cross-run interpretation.
  `overall` includes the additive task reward plus format reward and is not a
  pure answer-accuracy metric.
- The run used the same W&B ID (`ym2gx1ne`) across all three launches so plots
  should be continuous in W&B.
- `validation_summary.csv` includes the step-500 checkpoint/HF artifact status
  even though step-500 validation metrics are not exposed.
- `run_metadata.csv` is the source of truth for differentiating physical launch
  configs; the only intentional config differences across the three launches
  were `max_steps`, `save_limit`, `load_checkpoint_path`, and
  `save_checkpoint_path`.

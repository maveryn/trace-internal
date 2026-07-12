# Annotation System Prompt Response-Length Note

This note records the annotation-mode system prompt change made during the
2026-07-12 H200 Qwen2.5-VL-3B EasyR1 annotation ablations and the observed
response-length behavior before and after the change.

The comparison below uses gated annotation reward with annotation fraction
`0.25` on the same 8x H200 profile:

```text
TRACE_OUTPUT_MODE=answer_and_annotation
TRACE_REWARD_MODE=answer_and_annotation
TRACE_ANNOTATION_REWARD_FORMULA=gated
TRACE_ANNOTATION_FRACTION=0.25
trace_answer_weight=0.75
trace_annotation_weight=0.25
trace_format_weight=0.05
data.rollout_batch_size=128
worker.rollout.n=8
worker.rollout.tensor_parallel_size=2
worker.rollout.gpu_memory_utilization=0.90
worker.rollout.max_num_batched_tokens=32768
worker.actor.micro_batch_size_per_device_for_update=4
worker.actor.micro_batch_size_per_device_for_experience=8
worker.ref.micro_batch_size_per_device_for_experience=8
```

## Previous Prompt

The previous annotation-mode system prompt was:

```text
You are a helpful, conversational assistant tasked with answering a question about an image.

Reason carefully from the image and the question to determine the answer.

Annotation coordinates must be pixel coordinates in the provided image. The origin is the top-left corner; x increases rightward and y increases downward. Do not use normalized coordinates. Use the exact annotation shape requested in the prompt.

End your response with a JSON object in this format:
{"answer": ..., "annotation": ...}
```

This prompt was used by the stopped gated 0.25 run:

```text
experiment_name: trace_annotation_gated_ann0p25_h200_200step_20260712T140421Z
log: logs/rlvr/annotation_gated_ann0p25_200step_h200_20260712T140421Z.log
wandb: https://wandb.ai/llm-reasoning-rl/trace_easyr1/runs/oadcl0kg
status: stopped after saving global_step_100; last observed train step was 116
```

Observed response-length means collapsed quickly:

| step window | steps | mean of per-step means | min per-step mean | max per-step mean | max observed response |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1-5 | 5 | 201.1 | 197.3 | 206.3 | 2048 |
| 20-25 | 6 | 115.4 | 100.0 | 130.1 | 2048 |
| 40-45 | 6 | 58.7 | 51.5 | 67.6 | 2048 |
| 50-56 | 7 | 48.4 | 46.5 | 51.1 | 1620 |
| 80-85 | 6 | 46.9 | 44.8 | 50.9 | 340 |
| 100-116 | 18 | 51.7 | 47.9 | 54.9 | 457 |

Selected per-step values from the same log:

| step | response mean | response max | response min |
| ---: | ---: | ---: | ---: |
| 1 | 199.151 | 1284 | 4 |
| 2 | 201.883 | 1880 | 4 |
| 3 | 197.260 | 1659 | 4 |
| 20 | 130.138 | 2048 | 12 |
| 23 | 99.996 | 1015 | 12 |
| 40 | 67.561 | 1360 | 12 |
| 45 | 59.487 | 1784 | 12 |
| 50 | 49.359 | 948 | 11 |
| 56 | 47.781 | 1620 | 12 |
| 80 | 45.177 | 274 | 12 |
| 100 | 51.921 | 236 | 16 |
| 116 | 53.890 | 357 | 16 |

Interpretation: with the coordinate-heavy prompt, RL rapidly discovered short,
mostly serialization-like responses. The first few steps averaged about 200
tokens, but by the 40s and 50s the run stabilized around 50-60 response tokens.

## Current Default Prompt

The default annotation-mode prompt is now:

```text
You are a helpful, conversational assistant tasked with answering a question about an image.

Reason carefully from the image and the question to determine the answer.

The response should include the reasoning, then the requested annotation and answer. The annotation must follow the format requested by the prompt and use image pixel coordinates.

End your response with a JSON object in this format:
{"answer": ..., "annotation": ...}
```

The active prompt-A run used the same text through an explicit prompt-A path:

```text
experiment_name: trace_annotation_gated_ann0p25_prompt_a_h200_200step_20260712T161153Z
log: logs/rlvr/annotation_gated_ann0p25_prompt_a_200step_h200_20260712T161153Z.log
wandb: https://wandb.ai/llm-reasoning-rl/trace_easyr1/runs/pl55czdg
prompt file used by run: rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation_prompt_a.txt
canonical default prompt file: rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation.txt
status when measured: active, through step 56
```

Observed response-length means stayed higher and increased through the same
early windows:

| step window | steps | mean of per-step means | min per-step mean | max per-step mean | max observed response |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1-5 | 5 | 219.9 | 204.4 | 230.1 | 2048 |
| 20-25 | 6 | 228.4 | 210.6 | 248.4 | 2048 |
| 40-45 | 6 | 252.3 | 243.2 | 275.6 | 2048 |
| 50-56 | 7 | 272.1 | 262.6 | 279.0 | 2048 |

Selected per-step values from the same log:

| step | response mean | response max | response min |
| ---: | ---: | ---: | ---: |
| 1 | 221.528 | 2048 | 9 |
| 2 | 204.436 | 2048 | 4 |
| 3 | 230.102 | 2048 | 12 |
| 20 | 217.103 | 2048 | 12 |
| 23 | 216.399 | 2048 | 18 |
| 40 | 245.741 | 2048 | 20 |
| 45 | 275.603 | 1605 | 20 |
| 50 | 278.987 | 2048 | 27 |
| 56 | 278.272 | 1990 | 31 |

Interpretation: the compact connector line changed the behavior materially. The
current prompt keeps the answer-mode reasoning instruction and explicitly says
the response should include reasoning before the requested annotation and
answer. In the comparable gated 0.25 run, response length did not collapse in
the first 56 steps; it rose from roughly 220 tokens in steps 1-5 to roughly 270
tokens in steps 50-56.

## Extraction Command

The tables above were extracted from EasyR1 console metrics. The log exposes
per-step `response_length` min, mean, and max, but not quantiles, so these are
window summaries over per-step aggregates rather than full token-length
histograms.

```bash
perl -pe 's/\e\[[0-9;?]*[ -\/]*[@-~]//g; s/\r/\n/g' "$LOG" | awk '
/Step [0-9]+$/ {step=$NF; metric=""}
/response_length:[[:space:]]*$/ {metric="response"; max=""; mean=""; min=""; next}
/(global_seqlen:|prompt_length:|reward:|timing_s:|annotation_assigned)/ && $0 !~ /response_length:[[:space:]]*$/ {if (metric=="response") metric=""}
metric=="response" && /max:/ {max=$NF}
metric=="response" && /mean:/ {mean=$NF}
metric=="response" && /min:/ {
  min=$NF
  if (step != "" && mean != "") print step, mean, max, min
  metric=""
}'
```

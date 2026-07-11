# TRACE EasyR1 Reward Modes

This document describes the TRACE reward modes used by the active EasyR1
training backend under `rlvr/easyr1_backend/`.

The active reward adapter is:

```text
rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py
```

It calls the shared TRACE scorer:

```text
trace/core/reward_scoring.py
```

All paper runs should use the EasyR1 launchers under `scripts/` unless a run is
explicitly marked as legacy.

## Shared Reward Convention

All three modes keep the final scalar reward bounded in `[0, 1]`:

```text
overall = (1 - format_weight) * task_reward + format_weight * format_reward
```

The current default is:

```text
format_weight = 0.05
overall = 0.95 * task_reward + 0.05 * format_reward
```

`format_reward` is binary. It is `1.0` only when the response ends with a JSON
object whose keys exactly match the expected mode:

```text
answer mode:
{"answer": ...}

answer_and_annotation mode:
{"answer": ..., "annotation": ...}
```

For paper curves, compare methods with `answer_reward` / `accuracy`, not
`overall`, because annotation-mode `overall` includes annotation reward.

## Mode 1: Answer-Only

Prompt key:

```text
prompt_answer_only
```

System prompt:

```text
rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt
```

Reward mode:

```text
trace_output_mode=answer
trace_reward_mode=answer
```

Task reward:

```text
task_reward = answer_reward
overall = 0.95 * answer_reward + 0.05 * format_reward
```

Launcher:

```bash
scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh
```

## Mode 2: Answer And Annotation, Additive

Prompt key:

```text
prompt_answer_and_annotation
```

System prompt:

```text
rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation.txt
```

Reward mode:

```text
trace_output_mode=answer_and_annotation
trace_reward_mode=answer_and_annotation
trace_annotation_reward_formula=additive
```

Task reward:

```text
answer_weight = 1 - annotation_fraction
annotation_weight = annotation_fraction

task_reward = answer_weight * answer_reward
            + annotation_weight * annotation_reward

overall = 0.95 * task_reward + 0.05 * format_reward
```

Launcher:

```bash
TRACE_ANNOTATION_FRACTION=0.5 \
scripts/run_trace_qwen25vl3b_easyr1_annotation_additive_nokl_tmpfs.sh
```

`TRACE_ANNOTATION_FRACTION=0.25` gives `0.75 answer + 0.25 annotation`.
`TRACE_ANNOTATION_FRACTION=0.50` gives `0.50 answer + 0.50 annotation`.

## Mode 3: Answer And Annotation, Gated

Prompt key:

```text
prompt_answer_and_annotation
```

System prompt:

```text
rlvr/examples/prompts/trace_vero_json_system_prompt_answer_and_annotation.txt
```

Reward mode:

```text
trace_output_mode=answer_and_annotation
trace_reward_mode=answer_and_annotation
trace_annotation_reward_formula=gated
```

Task reward:

```text
answer_weight = 1 - annotation_fraction
annotation_weight = annotation_fraction

task_reward = answer_reward * (answer_weight + annotation_weight * annotation_reward)

overall = 0.95 * task_reward + 0.05 * format_reward
```

This mode gives annotation credit only through a correct answer. If the answer is
wrong, `task_reward` is zero even when the annotation is correct.

Launcher:

```bash
TRACE_ANNOTATION_FRACTION=0.5 \
scripts/run_trace_qwen25vl3b_easyr1_annotation_gated_nokl_tmpfs.sh
```

## Generic EasyR1 Launcher

The three wrappers call the generic launcher:

```bash
scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh
```

Useful environment variables:

```text
TRACE_OUTPUT_MODE=answer|answer_and_annotation
TRACE_REWARD_MODE=answer|answer_and_annotation
TRACE_ANNOTATION_REWARD_FORMULA=gated|additive
TRACE_ANNOTATION_FRACTION=0.25|0.5
TRACE_FORMAT_WEIGHT=0.05
MAX_STEPS=500
SAVE_FREQ=100
VAL_FREQ=100
TRAIN_FILES=/path/to/train.parquet
VAL_FILES=/path/to/val.parquet
```

If `TRACE_ANSWER_WEIGHT` and `TRACE_ANNOTATION_WEIGHT` are both set, the
launcher passes them directly to the scorer. Otherwise it derives them from
`TRACE_ANNOTATION_FRACTION`. The scorer normalizes the answer and annotation
weights internally, so `0.75/0.25` and `3/1` are equivalent.

## Metrics For Analysis

Use these for training curves and ablations:

```text
reward/accuracy
reward/answer_reward
reward/annotation_reward
reward/format
reward/task_reward_raw
reward/overall
reward/zero_reward
```

Cross-method answer-quality comparison:

```text
reward/answer_reward or reward/accuracy
```

Annotation-specific analysis:

```text
reward/annotation_reward
```

Do not use `reward/overall` as the primary cross-method comparison between
answer-only and annotation-mode runs, because the task reward contains different
components.

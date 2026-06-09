# TRACE RLVR Experiment Plan

This note records the planned TRACE RLVR training sequence. The goal is to use a
small set of controlled ablations on Qwen3-VL-4B to choose the dataset and reward
configuration, then train the final model family for 800 steps.

## Models

We will train three vision-language models:

| Model | Role |
|---|---|
| `Qwen/Qwen3-VL-4B-Instruct` | Main ablation model and one final model. |
| `Qwen/Qwen3-VL-8B-Instruct` | Final larger Qwen3-VL model. |
| `Qwen/Qwen2.5-VL-7B-Instruct` | Final Qwen2.5-VL comparison model. |

Unless otherwise specified, Qwen3 models use `max_prompt_length=1536`; Qwen2.5-VL
uses `max_prompt_length=2048`. TRACE training uses `max_response_length=2048`.
The external validation benchmarks use `val_max_response_length=1536` and the
same JSON answer extraction protocol.

## Training Data

The main filtered dataset currently available is the alpha-0.5 retained subset:

```text
rlvr/dataset/train/trace_rlvr_train_102400_query_id_alpha0_5_answer_retained_seed20260504.parquet
```

It contains 102,400 answer-mode examples selected from the 117,680 retained
examples after staged base-model filtering. The subset is stratified by
`(task, query_id, bucket_id_str)` as closely as possible to the original
alpha-0.5 source distribution, subject to retained-example capacity.

For the dataset-weight ablation, analogous retained 102,400-example subsets will
be created for:

| Alpha | Meaning |
|---:|---|
| `0.0` | Equal task weighting. |
| `0.5` | Moderate query-id-aware weighting. |
| `1.0` | Fully variant-count-proportional task weighting. |

The alpha-0 and alpha-1 staged probes are run with the same Qwen3-VL-4B filtering
procedure as alpha-0.5. Their retained subsets should include `query_id`,
`scene_variant`, `source_dataset_index`, and per-instance probe solve metadata.

## Validation Benchmarks

The default validation suite is:

| Benchmark |
|---|
| `mathvista_mini` |
| `mmstar` |
| `charxiv_rq` |
| `embspatialbench` |
| `mmmu_pro_vision` |
| `countqa` |

Validation uses TRACE-style JSON answer prompting and extraction. The main model
selection metric is mean external validation accuracy, with per-benchmark
accuracy retained for diagnosis.

Each alpha dataset also has a 1,024-example TRACE holdout validation set for
within-distribution overfitting checks:

| Alpha | TRACE holdout parquet |
|---:|---|
| `0.0` | `rlvr/dataset/validation/trace_rlvr_validation_1024_query_id_alpha0_answer_seed20260506.parquet` |
| `0.5` | `rlvr/dataset/validation/trace_rlvr_validation_1024_query_id_alpha0_5_answer_seed20260507.parquet` |
| `1.0` | `rlvr/dataset/validation/trace_rlvr_validation_1024_query_id_alpha1_answer_seed20260508.parquet` |

These holdouts are independently generated from TRACE with fresh seeds and the
same alpha-specific task sampling policy as their matching training dataset.
They are not sampled from the staged-probe retained pool. They have no train
`uid` or `instance_id` overlap and should be interpreted only within the
matching alpha bucket, not as the primary cross-alpha selection metric.

## Stage 1: Dataset-Weight Ablation

Train Qwen3-VL-4B for 250 steps on each dataset-weight setting:

| Run | Model | Dataset | Steps | Reward mode |
|---|---|---|---:|---|
| A0 | Qwen3-VL-4B | alpha `0.0` retained 102,400 | 250 | answer-only |
| A05 | Qwen3-VL-4B | alpha `0.5` retained 102,400 | 250 | answer-only |
| A1 | Qwen3-VL-4B | alpha `1.0` retained 102,400 | 250 | answer-only |

The best alpha is selected by external validation accuracy after 250 steps. This
selected dataset becomes the default dataset for subsequent reward and final
training runs. If the top two alpha settings are too close to distinguish, only
those candidates should be continued to 400 steps with an explicit
`TOTAL_TRAINING_STEPS=400` override.

## Stage 2: Annotation-Reward Ablation

Using the selected alpha dataset, train Qwen3-VL-4B with answer+annotation prompts
for 250 steps under two annotation reward formulations.

### Gated Annotation Reward

```text
reward = answer_reward * (0.5 + 0.5 * annotation_reward)
```

Properties:

- wrong answer receives zero reward, regardless of annotation;
- correct answer with poor annotation receives `0.5`;
- correct answer with perfect annotation receives `1.0`.

This formulation is conservative and avoids rewarding annotation localization for
incorrect answers.

### Additive Annotation Reward

```text
reward = 0.5 * answer_reward + 0.5 * annotation_reward
```

Properties:

- answer and annotation receive equal nominal weight;
- wrong answer with useful annotation can receive partial credit;
- correct answer with poor annotation receives `0.5`;
- perfect answer and annotation receives `1.0`.

This formulation may improve annotation-format learning, but can reward annotation
behavior even when the answer is wrong.

We will not run a hyperparameter sweep over answer/annotation weights. Both
annotation variants use fixed `0.5 / 0.5` weighting.

## Stage 3: Final Training

After selecting the best alpha and reward setting, train final models for 800
steps.

| Model | Dataset | Steps | Reward setting |
|---|---|---:|---|
| Qwen3-VL-4B | selected retained 102,400 | 800 | selected setting |
| Qwen3-VL-8B | selected retained 102,400 | 800 | selected setting |
| Qwen2.5-VL-7B | selected retained 102,400 | 800 | selected setting |

For Qwen3-VL-4B, if the selected final configuration already has a completed
250-step run, the 800-step run should resume from `global_step_250` rather than
restart. For Qwen3-VL-8B and Qwen2.5-VL-7B, train directly to 800 steps.

## Checkpoint Policy

Validation runs before training and every 25 training steps. Checkpoints are
also saved every 25 training steps.

Checkpoint storage is limited, so we keep one actor checkpoint and one critic
checkpoint:

```yaml
max_actor_ckpt_to_keep: 1
max_critic_ckpt_to_keep: 1
```

This is sufficient because continuation is always from the final 250-step
checkpoint, not from the best intermediate validation checkpoint.

Experiment names should be stable for resumable runs. The run script should not
append timestamps for the runs that may be resumed. Continuing from a 250-step
run should use either the same experiment directory with automatic resume or an
explicit resume path:

```text
trainer.resume_mode=resume_path
trainer.resume_from_path=<checkpoint_dir>/global_step_250
trainer.total_training_steps=800
```

## Required Code/Config Support

The training stack now supports:

1. model selection through `MODEL_PATH` for Qwen3-VL-4B, Qwen3-VL-8B, and
   Qwen2.5-VL-7B;
2. model-specific default prompt length:
   - Qwen3-VL: `1536`;
   - Qwen2.5-VL: `2048`;
3. TRACE training response length `2048`;
4. answer-only and answer+annotation prompt modes through `TRACE_OUTPUT_MODE`;
5. configurable TRACE annotation reward formula:
   - `gated`;
   - `additive`;
6. first-class `query_id` in future RLVR parquets, rather than requiring
   sidecar recovery;
7. stable experiment-name and resume behavior for the 250-to-800 step
   continuation.

The generic launcher is:

```bash
rlvr/examples/model_runs/run_trace_vl_rlvr.sh
```

The experiment wrapper sets stable defaults for the planned runs:

```bash
# Alpha ablation, 250 steps each.
scripts/run_trace_rlvr_experiment.sh alpha_ablation 0
scripts/run_trace_rlvr_experiment.sh alpha_ablation 0.5
scripts/run_trace_rlvr_experiment.sh alpha_ablation 1

# Annotation ablation on the selected alpha dataset, 250 steps each.
TRACE_ALPHA=0_5 scripts/run_trace_rlvr_experiment.sh annotation_ablation gated
TRACE_ALPHA=0_5 scripts/run_trace_rlvr_experiment.sh annotation_ablation additive

# Final runs, 800 steps each.
TRACE_ALPHA=0_5 scripts/run_trace_rlvr_experiment.sh final qwen3vl4b
TRACE_ALPHA=0_5 scripts/run_trace_rlvr_experiment.sh final qwen3vl8b
TRACE_ALPHA=0_5 scripts/run_trace_rlvr_experiment.sh final qwen25vl7b
```

For a continuation from the Qwen3-VL-4B 250-step checkpoint:

```bash
TRACE_ALPHA=0_5 \
RESUME_FROM_PATH=checkpoints/trace_rlvr/<experiment>/global_step_250 \
scripts/run_trace_rlvr_experiment.sh final qwen3vl4b
```

## Planned Run Count

The Qwen3-VL-4B ablation stage includes:

| Ablation | Runs |
|---|---:|
| Alpha dataset ablation | 3 |
| Annotation reward ablation | 2 |

The final model stage includes:

| Final model | Runs |
|---|---:|
| Qwen3-VL-4B | 1 continuation or full 800-step run |
| Qwen3-VL-8B | 1 |
| Qwen2.5-VL-7B | 1 |

Total planned runs are therefore five Qwen3-VL-4B 250-step ablations plus three
800-step final trainings, with the Qwen3-VL-4B final run reusing the selected
250-step checkpoint when possible.

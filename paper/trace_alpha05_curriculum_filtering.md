# Trace Alpha-0.5 Curriculum Filtering

This note describes the construction of the Trace answer-mode curriculum subset
used for RLVR training. The process has two stages: first, we generate a
query-id-aware 200k Trace training pool; second, we run a staged base-model
rollout filter and retain a stratified 102,400-example training subset.

## Source Pool

The source pool contains 200,000 Trace answer-mode instances generated from the
100 accepted default Trace tasks. Task sampling used a query-id-aware weighting
scheme with alpha `0.5`. For a task with `v_t` active query ids, the task
weight was:

```text
w_t = 1 + alpha * (v_t - 1)
```

With `alpha = 0.5` and at most five query ids per task, the resulting task
weights ranged from `1.0` to `3.0`. This preserves task-level sampling while
giving broader tasks moderately higher representation. Within each task, task
variants were sampled by the task generator/configuration.

Source parquet:

```text
rlvr/dataset/train/trace_rlvr_train_200000_query_id_alpha0_5_answer_seed20260504.parquet
```

The source pool has 100 tasks and 263 observed `(task, query_id)` units. The
original RLVR parquet did not include `query_id` as a column; for downstream
stratification we recovered it from the sidecar trace using `trace_ref`.

## Staged Rollout Filter

We evaluated the 200k source pool using `Qwen/Qwen3-VL-4B-Instruct` in
answer-only JSON mode. The model was sampled with temperature `1.0` in blocks of
four rollouts per prompt. The maximum number of observed rollouts per prompt was
16.

Important inference and scoring settings:

```text
model: Qwen/Qwen3-VL-4B-Instruct
prompt mode: answer-only JSON
reward mode: answer
answer scoring: exact_json
format reward weight: 0.0
max_prompt_length: 1536
max_tokens: 2048
max_pixels: 1048576
stage_rollouts: 4
max_rollouts: 16
easy_rate: 0.875
```

The filter maintains an active set of prompts. After each 4-rollout stage, a
prompt is retained if its cumulative success count is neither exactly zero nor
above the easy threshold. Otherwise, it remains active for more rollouts, unless
the maximum rollout budget has been reached.

For cumulative rollout count `n`, the easy threshold is:

```text
ceil(0.875 * n)
```

The continuation rule before the final stage is therefore:

```text
continue if successes == 0 or successes >= ceil(0.875 * n)
retain otherwise
```

At the terminal 16-rollout stage, prompts with zero successes are filtered as
hard-zero prompts, prompts with at least 14 successes are filtered as easy-high
prompts, and the rest are retained.

Probe output:

```text
rlvr/outputs/curriculum_probe/qwen3vl4b_200k_query_id_alpha0_5_answer_staged4to16_seed20260504/
```

## Rollout Results

Across the staged probe, the 200,000 prompts consumed 2,060,660 model rollouts,
or 10.303 rollouts per prompt on average. The base model produced 558,528
correct rollouts, for a rollout-weighted positive rate of 27.10%. The
per-question mean observed solve rate was 32.43%.

Final filtering outcome:

| Outcome | Count | Fraction |
|---|---:|---:|
| Retained band | 117,680 | 58.84% |
| Filtered hard zero | 62,241 | 31.12% |
| Filtered easy high | 20,079 | 10.04% |

Stage-level active-set dynamics:

| Stage | Cumulative rollouts | Input prompts | Active for next stage | Newly retained for training |
|---|---:|---:|---:|---:|
| 1 | 4 | 200,000 | 123,820 | 76,180 |
| 2 | 8 | 123,820 | 102,330 | 21,490 |
| 3 | 12 | 102,330 | 89,015 | 13,315 |
| 4 | 16 | 89,015 | 0 | 6,695 |

The last row reports only prompts retained for training at the terminal stage.
The remaining terminal active prompts were split into 62,241 hard-zero prompts
and 20,079 easy-high prompts.

Accuracy among prompts newly retained at each stage:

| Retained at stage | Rollouts observed | Count | Mean solve rate |
|---|---:|---:|---:|
| Stage 1 | 4 | 76,180 | 45.94% |
| Stage 2 | 8 | 21,490 | 25.06% |
| Stage 3 | 12 | 13,315 | 30.11% |
| Stage 4 | 16 | 6,695 | 13.70% |

Later retained groups are lower-accuracy because they are increasingly composed
of prompts that initially had zero successes and only became nonzero after more
rollouts.

## Constructing the 102,400-Example Subset

For training, we selected 102,400 prompts from the 117,680 retained prompts. This
corresponds to 800 training steps at global batch size 128:

```text
800 * 128 = 102,400
```

The subset was designed to remain as close as possible to the original
alpha-0.5 source distribution while using only retained prompts. We stratified
by:

```text
(task, query_id, bucket_id_str)
```

Because `query_id` was not present in the original parquet, it was recovered
from the source sidecar trace by joining each row through `trace_ref.line_index`.
We verified that `query_spec.query_id` and `execution_trace.query_id`
matched for all 200,000 source rows.

Query-branch recovery checks:

| Check | Value |
|---|---:|
| Source rows matched to sidecar trace | 200,000 |
| Missing query ids | 0 |
| Query/execution query-id mismatches | 0 |
| Observed `(task, query_id)` units | 263 |

The stratified allocation was capped proportional allocation:

1. Count each stratum in the original 200k source pool.
2. Count retained rows available for each stratum.
3. Allocate the 102,400 target rows proportional to the original stratum counts.
4. Cap each stratum quota at its retained availability.
5. Redistribute any remaining quota across non-capped strata, again proportional
   to original stratum weights.
6. Sample rows deterministically within each selected stratum using seed
   `20260504`.

This procedure preserves the alpha-0.5 query-id-aware distribution wherever the
retained pool has sufficient capacity. Exact preservation is impossible when a
task or variant is heavily filtered. In those cases, all retained examples from
the capped stratum are used and the remaining quota is redistributed.

Subset output:

```text
rlvr/dataset/train/trace_rlvr_train_102400_query_id_alpha0_5_answer_retained_seed20260504.parquet
```

Subset construction summary:

| Quantity | Value |
|---|---:|
| Source rows | 200,000 |
| Retained rows available | 117,680 |
| Selected rows | 102,400 |
| Source strata | 686 |
| Retained strata | 685 |
| Selected strata | 685 |
| Capacity-capped strata | 362 |
| Tasks covered | 100 |
| `(task, query_id)` units covered | 263 |
| Mean selected probe solve rate | 38.02% |

The final selected subset has task-level total variation distance 0.096 from the
original alpha-0.5 task distribution. This deviation is due to capacity limits in
heavily filtered tasks and variants.

The output parquet keeps all original RLVR columns and adds the following
columns:

| Column | Meaning |
|---|---|
| `source_dataset_index` | Row index in the original 200k source parquet. |
| `query_id` | Recovered query id from the sidecar trace. |
| `scene_variant` | Recovered scene/rendering variant when available. |
| `curriculum_probe_rollout_count` | Number of staged rollouts observed for this exact prompt. |
| `curriculum_probe_positive_rollout_count` | Number of correct rollouts for this exact prompt. |
| `curriculum_probe_solve_rate` | Instance-level solve rate under the staged base-model probe. |

The subset was produced with:

```text
scripts/build_trace_retained_stratified_subset.py
```

This script is reusable for later alpha settings or for rebuilding subsets with
different target sizes. If complexity metadata is updated later, the subset can
be refreshed by joining through `source_dataset_index`, `trace_ref`, or `uid`
without regenerating prompts or images.

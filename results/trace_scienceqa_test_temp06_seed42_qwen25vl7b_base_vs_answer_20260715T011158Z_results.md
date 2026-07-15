# ScienceQA_TEST Temp0.6 Seed42 Results

Generation: temperature=0.6, top_p=1.0, top_k=-1, max_tokens=4096, seed=42.

Scoring: TRACE deterministic MCQ fallback on top of VLMEvalKit exact matching. The original exact matcher is retained as `vlmeval_exact_matching_accuracy`; fallback is only used for rows where exact matching logged a prefetch parse failure.

| model                        |   rows |   accuracy |   delta_vs_base_pp |   vlmeval_exact_matching_accuracy |   fallback_rows |   fallback_recovered |   mean_generated_tokens |   median_generated_tokens |   max_generated_tokens |
|:-----------------------------|-------:|-----------:|-------------------:|----------------------------------:|----------------:|---------------------:|------------------------:|--------------------------:|-----------------------:|
| Qwen2.5-VL-7B-Instruct base  |   2017 |      87.65 |               0    |                             61.97 |             613 |                  518 |                   47.82 |                         7 |                    658 |
| TRACE 7B answer GRPO step500 |   2017 |      89.04 |               1.39 |                             46.46 |             992 |                  859 |                  145.9  |                        79 |                   4022 |

Run root: `/dev/shm/trace_rlvr/trace_scienceqa_test_temp06_seed42_qwen25vl7b_base_vs_answer_20260715T011158Z/runs`

Benchmark root: `/dev/shm/trace_rlvr/trace_scienceqa_test_temp06_seed42_qwen25vl7b_base_vs_answer_20260715T011158Z/benchmark`

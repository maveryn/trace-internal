# Qwen2.5-VL-3B TRACE Selected8 Task-Conditioned Step100 Temp0.6 Comparison

Scores are normalized percentages. The task-conditioned model is the merged EasyR1 `global_step_100` checkpoint from the mixed answer/annotation run.

Decoding: `temperature=0.6`, `top_p=1.0`, `top_k=-1`, `max_tokens=4096`, `seed=42`.

| Benchmark                |   Rows | Prompt / Dataset                  |   3B Base |   3B Answer GRPO 500 |   3B Annotation GRPO 500 |   3B Task-Conditioned 100 |   Answer - Base |   Annotation - Base |   TaskCond - Base |   TaskCond - Answer |   TaskCond - Annotation |
|:-------------------------|-------:|:----------------------------------|----------:|---------------------:|-------------------------:|--------------------------:|----------------:|--------------------:|------------------:|--------------------:|------------------------:|
| Blink                    |   1901 | vlmevalkit_defaults               |     44.56 |                46.5  |                    47.03 |                     45.29 |            1.95 |                2.47 |              0.74 |               -1.21 |                   -1.74 |
| ChartQAPro               |   1948 | vlmevalkit_faithful_cot           |     32.49 |                33.27 |                    33.82 |                     32.38 |            0.78 |                1.32 |             -0.11 |               -0.89 |                   -1.43 |
| CountQA                  |   1528 | vlmevalkit_cot_boxed              |     15.71 |                16.69 |                    17.54 |                     15.45 |            0.98 |                1.83 |             -0.26 |               -1.24 |                   -2.09 |
| Game-QA-Lite             |   2633 | vlmevalkit_cot_boxed              |     18.99 |                20.77 |                    21.31 |                     18.88 |            1.79 |                2.32 |             -0.11 |               -1.9  |                   -2.43 |
| MathVerse                |    788 | vlmevalkit_defaults_qwen32b_judge |     19.04 |                21.32 |                    22.59 |                     19.54 |            2.28 |                3.55 |              0.51 |               -1.78 |                   -3.05 |
| WeMath                   |   1740 | vlmevalkit_cot_qwen32b_judge      |     47.7  |                59.2  |                    51.67 |                     49.6  |           11.49 |                3.97 |              1.9  |               -9.6  |                   -2.07 |
| VStarBench               |    191 | vlmevalkit_defaults               |     70.16 |                72.77 |                    71.73 |                     70.16 |            2.62 |                1.57 |             -0    |               -2.62 |                   -1.57 |
| ScreenSpot               |   1272 | vlmevalkit_defaults_sample200     |     50    |                54.32 |                    63.44 |                     56.84 |            4.32 |               13.44 |              6.84 |                2.52 |                   -6.6  |
| Average                  |        |                                   |     37.33 |                40.61 |                    41.14 |                     38.52 |            3.28 |                3.81 |              1.19 |               -2.09 |                   -2.62 |
| Average excl. ScreenSpot |        |                                   |     35.52 |                38.65 |                    37.95 |                     35.9  |            3.13 |                2.43 |              0.38 |               -2.75 |                   -2.05 |

Sources:
- Prior 3B base/answer/annotation numbers: `/home/shadeform/trace/results/trace_3b_base_answer_annotation_combined.xlsx` sheet `temp0.6`.
- Task-conditioned step100 generation root: `/dev/shm/trace_rlvr/trace_selected8_qwen25vl3b_task_conditioned_step100_temp06_4096_20260714T051330Z/runs`.
- Task-conditioned step100 scoring root: `/dev/shm/trace_rlvr/trace_selected8_qwen25vl3b_task_conditioned_step100_temp06_4096_20260714T051330Z_score/benchmark`.

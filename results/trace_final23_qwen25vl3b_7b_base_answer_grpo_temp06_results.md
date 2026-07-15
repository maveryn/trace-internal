# TRACE Final23 Qwen2.5-VL 3B/7B Base vs Answer GRPO Results

Decoding: temperature=0.6, max_tokens=4096.

Most rows are 3-seed means from the selected25 workbook. EvoChart is 7B seed42 direct-judge only; MME-Reasoning is 7B 3-seed only. Cached 3B results for EvoChart/MME-Reasoning were not found, so those 3B cells are marked `not run`.

## Category Summary
| Family                           |   Benchmarks |   3B Base Avg |   3B Answer GRPO 500 Avg |   3B Delta Avg |   7B Base Avg |   7B Answer GRPO 500 Avg |   7B Delta Avg |   Missing 3B Rows |
|:---------------------------------|-------------:|--------------:|-------------------------:|---------------:|--------------:|-------------------------:|---------------:|------------------:|
| Charts / Tables / Figures        |            5 |         37.06 |                    40.18 |           3.12 |         48.92 |                    54.39 |           5.48 |                 1 |
| Math / Science                   |            7 |         34.24 |                    39.38 |           5.14 |         42.67 |                    47.00 |           4.33 |                 0 |
| Spatial / Perception / Grounding |            7 |         48.13 |                    49.92 |           1.79 |         55.94 |                    59.71 |           3.77 |                 0 |
| Puzzle / Abstract Reasoning      |            4 |         29.45 |                    34.68 |           5.23 |         34.11 |                    37.97 |           3.86 |                 1 |
| Overall                          |           23 |         38.72 |                    42.37 |           3.65 |         46.58 |                    50.91 |           4.33 |                 2 |

## Detailed Results

### Charts / Tables / Figures
| Benchmark     |   Rows | 3B Base   | 3B Answer GRPO 500   | 3B Delta   |   7B Base |   7B Answer GRPO 500 |   7B Delta | Source                                        |
|:--------------|-------:|:----------|:---------------------|:-----------|----------:|---------------------:|-----------:|:----------------------------------------------|
| ChartMuseum   |   1000 | 17.83     | 21.3                 | 3.47       |     24.43 |                32.50 |       8.07 | temp0.6 3-seed mean                           |
| ChartQAPro    |   1948 | 32.08     | 33.27                | 1.19       |     46.55 |                49.03 |       2.48 | temp0.6 3-seed mean                           |
| CharXivReason |   1000 | 29.2      | 34.27                | 5.07       |     39.17 |                46.43 |       7.27 | temp0.6 3-seed mean                           |
| TableVQABench |   1500 | 69.12     | 71.88                | 2.76       |     74.92 |                77.99 |       3.08 | temp0.6 3-seed mean                           |
| EvoChart      |   1250 | not run   | not run              | not run    |     59.52 |                66.00 |       6.48 | temp0.6 seed42 direct Qwen3 judge; 3B not run |

### Math / Science
| Benchmark    |   Rows |   3B Base |   3B Answer GRPO 500 |   3B Delta |   7B Base |   7B Answer GRPO 500 |   7B Delta | Source              |
|:-------------|-------:|----------:|---------------------:|-----------:|----------:|---------------------:|-----------:|:--------------------|
| MathVision   |   3040 |     19.93 |                24.61 |       4.67 |     25.96 |                27.96 |       2.00 | temp0.6 3-seed mean |
| MathVista    |   1000 |     58.43 |                64.60 |       6.17 |     69.13 |                73.43 |       4.30 | temp0.6 3-seed mean |
| MathVerse    |    788 |     34.09 |                39.59 |       5.50 |     43.82 |                46.40 |       2.58 | temp0.6 3-seed mean |
| PhyX mini MC |   1000 |     32.97 |                37.73 |       4.77 |     40.10 |                47.63 |       7.53 | temp0.6 3-seed mean |
| MMMU-ProVis  |   1730 |     26.76 |                30.83 |       4.07 |     35.03 |                39.88 |       4.86 | temp0.6 3-seed mean |
| Physics      |   1297 |     20.59 |                20.43 |      -0.15 |     20.71 |                25.80 |       5.09 | temp0.6 3-seed mean |
| WeMath       |   1740 |     46.93 |                57.87 |      10.94 |     63.95 |                67.89 |       3.95 | temp0.6 3-seed mean |

### Spatial / Perception / Grounding
| Benchmark           |   Rows |   3B Base |   3B Answer GRPO 500 |   3B Delta |   7B Base |   7B Answer GRPO 500 |   7B Delta | Source              |
|:--------------------|-------:|----------:|---------------------:|-----------:|----------:|---------------------:|-----------:|:--------------------|
| ScreenSpot          |   1272 |     68.19 |                64.02 |      -4.17 |     72.64 |                77.86 |       5.21 | temp0.6 3-seed mean |
| SpatialVizBench COT |   1180 |     25.45 |                26.86 |       1.41 |     26.50 |                31.61 |       5.11 | temp0.6 3-seed mean |
| CV-Bench 3D         |   1200 |     59.50 |                67.31 |       7.81 |     76.67 |                81.39 |       4.72 | temp0.6 3-seed mean |
| TreeBench           |    405 |     39.18 |                40.74 |       1.56 |     40.91 |                43.21 |       2.30 | temp0.6 3-seed mean |
| CountBenchQA        |    487 |     65.57 |                68.65 |       3.08 |     82.82 |                85.08 |       2.26 | temp0.6 3-seed mean |
| Blink               |   1901 |     44.52 |                46.50 |       1.98 |     53.20 |                58.76 |       5.56 | temp0.6 3-seed mean |
| ERQA                |    400 |     34.50 |                35.33 |       0.83 |     38.83 |                40.08 |       1.25 | temp0.6 3-seed mean |

### Puzzle / Abstract Reasoning
| Benchmark     |   Rows | 3B Base   | 3B Answer GRPO 500   | 3B Delta   |   7B Base |   7B Answer GRPO 500 |   7B Delta | Source                             |
|:--------------|-------:|:----------|:---------------------|:-----------|----------:|---------------------:|-----------:|:-----------------------------------|
| PuzzleVQA     |   2000 | 33.03     | 40.35                | 7.32       |     46.85 |                53.18 |       6.33 | temp0.6 3-seed mean                |
| VisualPuzzles |   1168 | 18.49     | 21.03                | 2.54       |     21.66 |                24.49 |       2.83 | temp0.6 3-seed mean                |
| LogicVista    |    447 | 36.84     | 42.65                | 5.82       |     42.80 |                47.73 |       4.92 | temp0.6 3-seed mean                |
| MME-Reasoning |   1188 | not run   | not run              | not run    |     25.11 |                26.49 |       1.37 | temp0.6 7B 3-seed mean; 3B not run |

## Metadata
| key                  | value                                                                                                    |
|:---------------------|:---------------------------------------------------------------------------------------------------------|
| decoding             | temperature=0.6, max_tokens=4096                                                                         |
| core_source          | results/qwen25vl3b_7b_answer_grpo_selected25_temp06_3seed_mean_std.xlsx                                  |
| evochart_source      | results/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z_results.xlsx |
| mme_reasoning_source | /dev/shm/trace_rlvr/trace_mme_reasoning_temp06_seed{42,43,44}_qwen25vl7b_base_vs_answer_*_score          |
| missing_3b           | EvoChart and MME-Reasoning were not run for Qwen2.5-VL-3B in the cached artifacts.                       |
| mathverse_note       | Uses repaired MathVerse Qwen3 judgement scoring from 2026-07-15.                                         |

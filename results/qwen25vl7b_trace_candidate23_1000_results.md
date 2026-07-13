# Qwen2.5-VL-7B TRACE Candidate23 Stage 2 Results

Date: 2026-07-12

Stage: cumulative 1000 samples per benchmark where available. Benchmarks with fewer than 1000 examples use the full available subset.

Models:
- Base: `Qwen/Qwen2.5-VL-7B-Instruct`
- TRACE step500: `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500`

Artifacts:
- Subset root: `benchmark/subsets/trace_candidate23_1000`
- Generation logs: `logs/benchmark/trace_candidate23_1000_7b_20260712T223728Z` and `logs/benchmark/trace_candidate23_1000_7b_continue_20260712T232341Z`
- Score logs: `logs/benchmark/trace_candidate23_1000_7b_continue_20260712T232341Z/score*.log`
- Run root: `/dev/shm/trace_rlvr/trace_runs` via repo symlink `runs/`
- Score queue: `benchmark/queues/score_multi_trace_candidate23_1000_7b_base_vs_step500_20260712T232341Z.json`

Notes:
- Generation and scoring completed for all 23 benchmarks.
- Judge-backed benchmarks were scored with local `Qwen/Qwen3-32B`.
- Scoring parallelism is currently benchmark-granularity: one benchmark job per GPU. Once only one or two judge-heavy benchmarks remain, the other GPUs are idle unless we row-shard those benchmark scorers.
- The final scoring tail also includes CPU/Python row-wise scorer passes after Qwen3 judge generation, during which GPU memory can remain allocated with low SM utilization.

## Averages

| Slice | Benchmarks | Base | Step500 | Delta |
|---|---:|---:|---:|---:|
| Overall | 23 | 42.41 | 42.08 | -0.33 |
| Excluding ScreenSpot and ScreenSpot-Pro | 21 | 42.58 | 42.00 | -0.58 |
| Excluding ScreenSpot, ScreenSpot-Pro, and VLMBias | 20 | 43.65 | 42.92 | -0.73 |

## Benchmark Scores

| Benchmark | Prompt/run | N | Base | Step500 | Delta | Base mean toks | Step500 mean toks |
|---|---|---:|---:|---:|---:|---:|---:|
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 28.50 | 34.50 | +6.00 | 248.63 | 631.30 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 1000 | 23.30 | 29.60 | +6.30 | 325.09 | 584.46 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1000 | 70.10 | 74.10 | +4.00 | 66.45 | 127.66 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 1000 | 11.10 | 11.70 | +0.60 | 92.64 | 184.41 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1000 | 32.50 | 8.88 | -23.62 | 173.69 | 377.36 |
| PuzzleVQA | `vlmevalkit_reasoning` | 1000 | 45.20 | 43.00 | -2.20 | 244.23 | 364.14 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 44.30 | 48.10 | +3.80 | 267.86 | 446.08 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 69.70 | 74.40 | +4.70 | 189.87 | 310.75 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1000 | 71.90 | 68.60 | -3.30 | 122.43 | 206.04 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1000 | 62.30 | 66.90 | +4.60 | 196.12 | 346.71 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 27.10 | 27.30 | +0.20 | 495.97 | 610.37 |
| ERQA | `vlmevalkit_defaults` | 400 | 40.00 | 41.25 | +1.25 | 2.01 | 2.00 |
| TreeBench | `vlmevalkit_defaults` | 405 | 38.02 | 37.28 | -0.74 | 17.96 | 34.01 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 86.24 | 86.65 | +0.41 | 2.11 | 2.09 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 25.51 | 23.10 | -2.41 | 407.67 | 453.26 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 39.20 | 46.40 | +7.20 | 23.45 | 347.81 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 40.30 | 49.80 | +9.50 | 163.34 | 722.79 |
| Physics | `vlmevalkit_reasoning` | 1000 | 14.10 | 15.40 | +1.30 | 720.43 | 897.15 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1000 | 38.20 | 34.20 | -4.00 | 440.48 | 586.52 |
| Blink | `vlmevalkit_defaults` | 1000 | 52.40 | 33.30 | -19.10 | 21.80 | 142.56 |
| VisionGraph-Q3 | `vlmevalkit_q3` | 1000 | 17.78 | 17.46 | -0.32 | 395.40 | 688.68 |
| VStarBench | `vlmevalkit_defaults` | 191 | 76.44 | 72.25 | -4.19 | 5.99 | 23.74 |
| VLMBias | `vlmevalkit_defaults` | 1000 | 21.20 | 23.70 | +2.50 | 4.12 | 4.10 |

## Score Files

| Benchmark | Base score file | Step500 score file |
|---|---|---|
| ChartMuseum | `runs/chartmuseum/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge_test/scores.json` | `runs/chartmuseum/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge_test/scores.json` |
| Game-QA-Lite | `runs/game_qa_lite/qwen25vl7b-base/vlmevalkit_cot_boxed/scores.json` | `runs/game_qa_lite/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_cot_boxed/scores.json` |
| ScreenSpot | `runs/screenspot/qwen25vl7b-base/vlmevalkit_defaults_sample200/scores.json` | `runs/screenspot/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_sample200/scores.json` |
| ScreenSpot-Pro | `runs/screenspotpro/qwen25vl7b-base/vlmevalkit_defaults_sample200/scores.json` | `runs/screenspotpro/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_sample200/scores.json` |
| ChartQAPro | `runs/chartqapro/qwen25vl7b-base/vlmevalkit_faithful_cot/scores.json` | `runs/chartqapro/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_faithful_cot/scores.json` |
| PuzzleVQA | `runs/puzzlevqa/qwen25vl7b-base/vlmevalkit_reasoning/scores.json` | `runs/puzzlevqa/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_reasoning/scores.json` |
| LogicVista | `runs/logicvista/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge/scores.json` | `runs/logicvista/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge/scores.json` |
| MathVista | `runs/mathvista/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge/scores.json` | `runs/mathvista/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge/scores.json` |
| CV-Bench 3D | `runs/cvbench_3d/qwen25vl7b-base/vlmevalkit_defaults/scores.json` | `runs/cvbench_3d/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults/scores.json` |
| WeMath | `runs/wemath/qwen25vl7b-base/vlmevalkit_cot_qwen32b_judge/scores.json` | `runs/wemath/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_cot_qwen32b_judge/scores.json` |
| MathVision | `runs/mathvision/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge/scores.json` | `runs/mathvision/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge/scores.json` |
| ERQA | `runs/erqa/qwen25vl7b-base/vlmevalkit_defaults/scores.json` | `runs/erqa/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults/scores.json` |
| TreeBench | `runs/treebench/qwen25vl7b-base/vlmevalkit_defaults/scores.json` | `runs/treebench/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults/scores.json` |
| CountBenchQA | `runs/countbenchqa/qwen25vl7b-base/vlmevalkit_defaults/scores.json` | `runs/countbenchqa/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults/scores.json` |
| MathVerse | `runs/mathverse/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge/scores.json` | `runs/mathverse/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge/scores.json` |
| CharXivReason | `runs/charxivreason/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge/scores.json` | `runs/charxivreason/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge/scores.json` |
| PhyX mini MC | `runs/phyx_mini_mc/qwen25vl7b-base/vlmevalkit_defaults/scores.json` | `runs/phyx_mini_mc/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults/scores.json` |
| Physics | `runs/physics/qwen25vl7b-base/vlmevalkit_reasoning/scores.json` | `runs/physics/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_reasoning/scores.json` |
| MMMU-ProVis | `runs/mmmu_pro_vision/qwen25vl7b-base/vlmevalkit_cot_max2048/scores.json` | `runs/mmmu_pro_vision/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_cot_max2048/scores.json` |
| Blink | `runs/blink/qwen25vl7b-base/vlmevalkit_defaults/scores.json` | `runs/blink/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults/scores.json` |
| VisionGraph-Q3 | `runs/visiongraph_q3/qwen25vl7b-base/vlmevalkit_q3/scores.json` | `runs/visiongraph_q3/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_q3/scores.json` |
| VStarBench | `runs/vstarbench/qwen25vl7b-base/vlmevalkit_defaults/scores.json` | `runs/vstarbench/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults/scores.json` |
| VLMBias | `runs/vlmbias/qwen25vl7b-base/vlmevalkit_defaults/scores.json` | `runs/vlmbias/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults/scores.json` |

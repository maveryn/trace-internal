# Qwen2.5-VL-3B TRACE Candidate23 Stage 2 Results, Latest Extraction

Date: 2026-07-13

Stage: cumulative 1000 samples per benchmark where available. Benchmarks with fewer than 1000 examples use the full available subset.

Models:
- Base: `Qwen/Qwen2.5-VL-3B-Instruct`
- TRACE step500: `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`

Artifacts:
- Subset root: `benchmark/subsets/trace_candidate23_1000`
- Response root: `/dev/shm/trace_rlvr/trace_runs`
- Latest extraction score root: `benchmark/llm_extracted/trace_candidate15_1000_3b_base_vs_step500_qwen32b_api_extract_20260713T011502Z`
- Previous stage table used for unchanged rows: `results/qwen25vl3b_trace_candidate23_1000_results.md`

Notes:
- The 15 extraction-sensitive benchmarks were rescored with resident `Qwen/Qwen3-32B` judge endpoints through the local OpenAI-compatible API.
- The other 8 rows are carried from the prior Candidate23 stage-2 result because their scoring path was not part of this latest extraction-sensitive rerun.
- VisionGraph-Q3 responses were regenerated into `/dev/shm/trace_rlvr/trace_runs` from 4 shards per model and then merged before scoring.

## Averages

| Slice | Benchmarks | Base | Step500 | Delta |
|---|---:|---:|---:|---:|
| Overall | 23 | 37.75 | 40.66 | +2.90 |
| Excluding ScreenSpot and ScreenSpot-Pro | 21 | 36.34 | 39.76 | +3.43 |
| Excluding ScreenSpot, ScreenSpot-Pro, and VLMBias | 20 | 37.20 | 40.74 | +3.54 |

## Benchmark Scores

| Benchmark | Prompt/run | N | Base | Step500 | Delta | Scoring/extraction |
|---|---|---:|---:|---:|---:|---|
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 21.30 | 24.30 | +3.00 | original stage result |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 1000 | 18.80 | 23.90 | +5.10 | Qwen3-32B latest extraction/scoring |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1000 | 87.94 | 85.11 | -2.83 | original stage result |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 1000 | 17.33 | 15.01 | -2.31 | original stage result |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1000 | 29.73 | 33.89 | +4.15 | Qwen3-32B latest extraction/scoring |
| PuzzleVQA | `vlmevalkit_reasoning` | 1000 | 34.70 | 41.30 | +6.60 | Qwen3-32B latest extraction/scoring |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 36.02 | 43.40 | +7.38 | original stage result |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 62.80 | 65.30 | +2.50 | original stage result |
| CV-Bench 3D | `vlmevalkit_defaults` | 1000 | 66.70 | 72.30 | +5.60 | Qwen3-32B latest extraction/scoring |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1000 | 44.30 | 61.90 | +17.60 | Qwen3-32B latest extraction/scoring |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 21.50 | 23.80 | +2.30 | original stage result |
| ERQA | `vlmevalkit_defaults` | 400 | 37.25 | 36.00 | -1.25 | Qwen3-32B latest extraction/scoring |
| TreeBench | `vlmevalkit_defaults` | 405 | 40.99 | 42.47 | +1.48 | Qwen3-32B latest extraction/scoring |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 72.48 | 71.46 | -1.03 | Qwen3-32B latest extraction/scoring |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 20.94 | 20.05 | -0.89 | original stage result |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 29.90 | 34.90 | +5.00 | original stage result |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 31.10 | 34.50 | +3.40 | Qwen3-32B latest extraction/scoring |
| Physics | `vlmevalkit_reasoning` | 1000 | 21.30 | 21.20 | -0.10 | Qwen3-32B latest extraction/scoring |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1000 | 24.70 | 30.30 | +5.60 | Qwen3-32B latest extraction/scoring |
| Blink | `vlmevalkit_defaults` | 1000 | 46.70 | 46.10 | -0.60 | Qwen3-32B latest extraction/scoring |
| VisionGraph-Q3 | `vlmevalkit_q3` | 1000 | 12.59 | 13.42 | +0.83 | Qwen3-32B latest extraction/scoring |
| VStarBench | `vlmevalkit_defaults` | 191 | 70.16 | 74.35 | +4.19 | Qwen3-32B latest extraction/scoring |
| VLMBias | `vlmevalkit_defaults` | 1000 | 19.10 | 20.20 | +1.10 | Qwen3-32B latest extraction/scoring |

## Updated Rows

Game-QA-Lite, ChartQAPro, PuzzleVQA, CV-Bench 3D, WeMath, ERQA, TreeBench, CountBenchQA, PhyX mini MC, Physics, MMMU-ProVis, Blink, VisionGraph-Q3, VStarBench, VLMBias


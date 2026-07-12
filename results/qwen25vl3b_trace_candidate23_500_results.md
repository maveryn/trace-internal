# Qwen2.5-VL-3B TRACE Candidate-23 500-Row Stage Results

Generated on 2026-07-12 UTC.

Models:
- Base: `Qwen/Qwen2.5-VL-3B-Instruct` (`qwen25vl3b-base`)
- TRACE RLVR step 500: `trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`

Artifacts:
- Cumulative subset manifests: `benchmark/subsets/trace_candidate23_500/`
- Generation logs: `logs/benchmark/trace_candidate23_500_20260712T042900Z/`
- Score logs: `logs/benchmark/trace_candidate23_500_20260712T045700Z/`
- Stage score root: `benchmark/stages/trace_candidate23_500/`
- Step-500 merged HF checkpoint: `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`

This stage carries forward the existing 200-row candidate subset and adds up to 300 deterministic random unused rows per benchmark. Datasets with fewer than 500 available rows use all remaining rows.

| Benchmark | Rows | Base | Step 500 | Delta |
|---|---:|---:|---:|---:|
| ChartMuseum | 500 | 21.20 | 23.80 | +2.60 |
| Game-QA-Lite | 500 | 19.40 | 24.20 | +4.80 |
| ScreenSpot | 500 | 60.62 | 57.82 | -2.80 |
| ScreenSpot-Pro | 500 | 13.43 | 10.69 | -2.74 |
| ChartQAPro | 500 | 30.21 | 26.61 | -3.60 |
| PuzzleVQA | 500 | 31.80 | 36.40 | +4.60 |
| LogicVista | 447 | 36.02 | 43.40 | +7.38 |
| MathVista | 500 | 64.00 | 64.80 | +0.80 |
| CV-Bench 3D | 500 | 49.50 | 53.50 | +4.00 |
| WeMath | 500 | 45.40 | 61.40 | +16.00 |
| MathVision | 500 | 20.20 | 19.60 | -0.60 |
| ERQA | 400 | 31.00 | 33.25 | +2.25 |
| TreeBench | 405 | 40.00 | 35.00 | -5.00 |
| CountBenchQA | 487 | 69.61 | 72.28 | +2.67 |
| MathVerse | 500 | 18.80 | 21.80 | +3.00 |
| CharXivReason | 500 | 29.40 | 34.20 | +4.80 |
| PhyX mini MC | 500 | 33.60 | 35.00 | +1.40 |
| Physics | 500 | 11.20 | 13.40 | +2.20 |
| MMMU-ProVis | 500 | 25.00 | 27.80 | +2.80 |
| BLINK | 500 | 42.40 | 41.60 | -0.80 |
| VisionGraph-Q3 | 500 | 12.68 | 14.00 | +1.32 |
| VStarBench | 191 | 71.73 | 71.20 | -0.52 |
| VLMBias | 500 | 19.80 | 20.00 | +0.20 |

## Averages

| Average | Count | Base | Step 500 | Delta |
|---|---:|---:|---:|---:|
| Overall-23 | 23 | 34.65 | 36.60 | +1.95 |
| Excluding ScreenSpot and ScreenSpot-Pro | 21 | 34.43 | 36.82 | +2.40 |
| Excluding ScreenSpot, ScreenSpot-Pro, and VLMBias | 20 | 35.16 | 37.66 | +2.50 |

## Notes

- Generation reused existing `predictions.jsonl` rows by index and generated only missing rows from the cumulative 500-row manifests.
- Old 200-row `generation_summary.json` sentinel files were removed before generation so the queue would not incorrectly skip the expanded 500-row stage.
- Scoring used `scripts/run_external_benchmark_score_multi_model_queue.py`, which scores base and step-500 for each benchmark in the same worker process. This reuses one persistent Qwen3 judge per GPU for judge-backed benchmarks.
- Stage score JSONs were written under `benchmark/stages/trace_candidate23_500/` to avoid overwriting the prior 200-row benchmark score root.

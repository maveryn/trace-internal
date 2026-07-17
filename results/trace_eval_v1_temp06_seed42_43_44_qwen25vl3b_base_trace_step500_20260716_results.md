# TRACE Eval v1 Temp0.6 Three-Seed Results

Seeds: `42, 43, 44`

## Category Means

| Category | Benchmarks | TRACE Qwen2.5-VL 3B | Qwen2.5-VL-3B Base | TRACE-Base |
|---|---|---|---|---|
| Charts & Tables | 4 | 46.23 +/- 0.93 | 44.56 +/- 0.06 | 1.67 |
| Visual Math | 4 | 39.66 +/- 0.79 | 32.21 +/- 1.65 | 7.44 |
| Science & General | 4 | 46.50 +/- 1.77 | 43.00 +/- 2.54 | 3.50 |
| Spatial Reasoning | 4 | 49.03 +/- 0.90 | 45.79 +/- 2.37 | 3.24 |
| Perception & Counting | 4 | 42.51 +/- 0.32 | 41.02 +/- 0.52 | 1.48 |
| Puzzles & Logic | 4 | 33.20 +/- 0.91 | 29.46 +/- 0.58 | 3.75 |

## Benchmark Means

| Category | Benchmark | Rows | TRACE Qwen2.5-VL 3B | Qwen2.5-VL-3B Base | TRACE-Base |
|---|---|---|---|---|---|
| Charts & Tables | ChartQAPro | 1948 | 31.43 +/- 1.33 | 31.57 +/- 0.66 | -0.14 |
| Charts & Tables | CharXivReason | 1000 | 34.67 +/- 1.47 | 28.90 +/- 1.11 | 5.77 |
| Charts & Tables | TableVQABench | 1500 | 71.99 +/- 0.28 | 69.27 +/- 0.91 | 2.72 |
| Charts & Tables | EvoChart | 1250 | 46.83 +/- 1.36 | 48.51 +/- 0.45 | -1.68 |
| Visual Math | MathVision | 3040 | 25.35 +/- 0.86 | 19.25 +/- 0.65 | 6.10 |
| Visual Math | MathVista | 1000 | 64.43 +/- 2.12 | 58.13 +/- 3.74 | 6.30 |
| Visual Math | MathVerse | 788 | 40.02 +/- 1.52 | 33.59 +/- 1.95 | 6.43 |
| Visual Math | WeMath | 1740 | 28.82 +/- 0.40 | 17.87 +/- 1.24 | 10.95 |
| Science & General | PhyX mini MC | 1000 | 37.47 +/- 5.58 | 32.80 +/- 9.96 | 4.67 |
| Science & General | MMMU-ProVis | 1730 | 31.16 +/- 1.20 | 26.59 +/- 0.32 | 4.57 |
| Science & General | RealWorldQA | 765 | 62.14 +/- 1.18 | 60.35 +/- 0.42 | 1.79 |
| Science & General | MMStar | 1500 | 55.24 +/- 1.02 | 52.27 +/- 0.52 | 2.98 |
| Spatial Reasoning | EmbSpatial | 3640 | 60.88 +/- 1.13 | 59.07 +/- 1.04 | 1.81 |
| Spatial Reasoning | SpatialVizBench COT | 1180 | 31.84 +/- 1.52 | 30.08 +/- 1.22 | 1.75 |
| Spatial Reasoning | CV-Bench 3D | 1200 | 66.97 +/- 3.68 | 58.67 +/- 8.32 | 8.31 |
| Spatial Reasoning | ERQA | 400 | 36.42 +/- 0.52 | 35.33 +/- 0.80 | 1.08 |
| Perception & Counting | Blink | 1901 | 47.13 +/- 0.70 | 44.52 +/- 2.10 | 2.61 |
| Perception & Counting | CountBenchQA | 487 | 68.65 +/- 0.83 | 65.43 +/- 1.59 | 3.22 |
| Perception & Counting | CountQA | 1528 | 15.64 +/- 0.57 | 14.88 +/- 1.80 | 0.76 |
| Perception & Counting | TreeBench | 405 | 38.60 +/- 1.17 | 39.26 +/- 1.96 | -0.66 |
| Puzzles & Logic | PuzzleVQA | 2000 | 39.13 +/- 1.13 | 32.55 +/- 1.21 | 6.58 |
| Puzzles & Logic | VisualPuzzles | 1168 | 28.51 +/- 0.70 | 26.20 +/- 2.74 | 2.31 |
| Puzzles & Logic | LogicVista | 447 | 40.12 +/- 1.71 | 36.47 +/- 1.25 | 3.65 |
| Puzzles & Logic | MME-Reasoning | 1188 | 25.06 +/- 1.53 | 22.62 +/- 1.81 | 2.44 |
| Overall | Average |  | 42.85 +/- 0.39 | 39.34 +/- 0.63 | 3.51 |

Decoding: temperature 0.6, top-p 1, top-k -1, no penalties, maximum 4096 generated tokens.
Scoring: the pinned benchmark routes selected by canonical trace_eval_v1.
Selection manifest SHA-256: `b84262bcd2243d1d2879b2e02d9b49b17052659ea767df3d7303758f4d63de71`.

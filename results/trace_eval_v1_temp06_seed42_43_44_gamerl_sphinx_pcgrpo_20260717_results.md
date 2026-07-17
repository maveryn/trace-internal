# TRACE Eval v1 Temp0.6 Three-Seed Results

Seeds: `42, 43, 44`

## Category Means

| Category | Benchmarks | Game-RL Qwen2.5-VL-7B | Sphinx Qwen2.5-VL-7B 500 | PCGRPO Qwen2.5-VL-7B Jigsaw CARE |
|---|---|---|---|---|
| Charts & Tables | 4 | 54.81 +/- 0.41 | 54.50 +/- 0.87 | 52.91 +/- 0.99 |
| Visual Math | 4 | 44.37 +/- 0.32 | 44.70 +/- 0.26 | 44.99 +/- 0.40 |
| Science & General | 4 | 51.52 +/- 1.53 | 52.25 +/- 0.88 | 52.28 +/- 0.92 |
| Spatial Reasoning | 4 | 54.31 +/- 0.99 | 56.18 +/- 0.97 | 56.03 +/- 0.55 |
| Perception & Counting | 4 | 48.54 +/- 0.24 | 50.03 +/- 0.17 | 48.70 +/- 0.22 |
| Puzzles & Logic | 4 | 34.72 +/- 0.74 | 38.39 +/- 0.05 | 37.91 +/- 0.79 |

## Benchmark Means

| Category | Benchmark | Rows | Game-RL Qwen2.5-VL-7B | Sphinx Qwen2.5-VL-7B 500 | PCGRPO Qwen2.5-VL-7B Jigsaw CARE |
|---|---|---|---|---|---|
| Charts & Tables | ChartQAPro | 1948 | 45.35 +/- 0.38 | 43.88 +/- 2.33 | 39.32 +/- 1.19 |
| Charts & Tables | CharXivReason | 1000 | 39.67 +/- 1.04 | 40.73 +/- 0.35 | 41.23 +/- 0.67 |
| Charts & Tables | TableVQABench | 1500 | 75.59 +/- 0.82 | 74.94 +/- 1.67 | 72.27 +/- 2.55 |
| Charts & Tables | EvoChart | 1250 | 58.64 +/- 0.85 | 58.43 +/- 0.17 | 58.80 +/- 0.56 |
| Visual Math | MathVision | 3040 | 25.30 +/- 0.32 | 26.18 +/- 0.46 | 25.27 +/- 1.04 |
| Visual Math | MathVista | 1000 | 69.93 +/- 0.97 | 71.03 +/- 0.65 | 70.80 +/- 0.60 |
| Visual Math | MathVerse | 788 | 44.08 +/- 1.53 | 45.35 +/- 2.44 | 44.88 +/- 0.97 |
| Visual Math | WeMath | 1740 | 38.19 +/- 1.03 | 36.25 +/- 0.53 | 39.02 +/- 1.44 |
| Science & General | PhyX mini MC | 1000 | 41.43 +/- 4.45 | 42.37 +/- 3.27 | 42.00 +/- 2.89 |
| Science & General | MMMU-ProVis | 1730 | 36.13 +/- 0.55 | 37.57 +/- 0.21 | 36.86 +/- 1.21 |
| Science & General | RealWorldQA | 765 | 65.97 +/- 0.33 | 67.28 +/- 0.20 | 67.80 +/- 0.98 |
| Science & General | MMStar | 1500 | 62.56 +/- 1.47 | 61.78 +/- 0.52 | 62.47 +/- 0.76 |
| Spatial Reasoning | EmbSpatial | 3640 | 69.54 +/- 0.93 | 70.87 +/- 0.71 | 72.74 +/- 0.22 |
| Spatial Reasoning | SpatialVizBench COT | 1180 | 32.66 +/- 2.33 | 33.76 +/- 1.54 | 30.76 +/- 1.78 |
| Spatial Reasoning | CV-Bench 3D | 1200 | 76.19 +/- 0.83 | 79.78 +/- 0.96 | 80.22 +/- 0.46 |
| Spatial Reasoning | ERQA | 400 | 38.83 +/- 1.66 | 40.33 +/- 2.02 | 40.42 +/- 0.76 |
| Perception & Counting | Blink | 1901 | 53.78 +/- 1.21 | 55.73 +/- 1.06 | 56.60 +/- 0.53 |
| Perception & Counting | CountBenchQA | 487 | 82.61 +/- 1.37 | 83.30 +/- 1.32 | 80.56 +/- 1.20 |
| Perception & Counting | CountQA | 1528 | 19.92 +/- 1.04 | 21.36 +/- 0.25 | 17.21 +/- 0.41 |
| Perception & Counting | TreeBench | 405 | 37.86 +/- 1.00 | 39.75 +/- 1.78 | 40.41 +/- 1.98 |
| Puzzles & Logic | PuzzleVQA | 2000 | 40.10 +/- 1.54 | 48.57 +/- 1.10 | 47.95 +/- 1.05 |
| Puzzles & Logic | VisualPuzzles | 1168 | 29.39 +/- 0.72 | 33.19 +/- 0.86 | 33.13 +/- 1.65 |
| Puzzles & Logic | LogicVista | 447 | 43.25 +/- 0.90 | 44.67 +/- 1.23 | 43.03 +/- 0.93 |
| Puzzles & Logic | MME-Reasoning | 1188 | 26.12 +/- 1.07 | 27.13 +/- 0.34 | 27.53 +/- 0.96 |
| Overall | Average |  | 48.05 +/- 0.45 | 49.34 +/- 0.15 | 48.80 +/- 0.28 |

Decoding: temperature 0.6, top-p 1, top-k -1, no penalties, maximum 4096 generated tokens.
Scoring: the pinned benchmark routes selected by canonical trace_eval_v1.
Selection manifest SHA-256: `b84262bcd2243d1d2879b2e02d9b49b17052659ea767df3d7303758f4d63de71`.

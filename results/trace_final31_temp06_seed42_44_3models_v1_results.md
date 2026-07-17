# TRACE Final31 Temp0.6 Three-Seed Results

Seeds: `42, 43, 44`

## Category Means

| Category | Benchmarks | Qwen2.5-VL-7B Base | TRACE Qwen2.5-VL-7B | VERO Qwen2.5-VL-7B | TRACE - Base | TRACE - VERO |
|---|---|---|---|---|---|---|
| Charts & Tables | 5 | 51.86 +/- 0.22 | 55.99 +/- 0.10 | 54.06 +/- 0.29 | 4.14 | 1.94 |
| Visual Math | 4 | 43.03 +/- 0.85 | 48.68 +/- 0.08 | 50.70 +/- 0.24 | 5.65 | -2.02 |
| Science & General | 5 | 42.59 +/- 0.68 | 46.29 +/- 0.20 | 46.45 +/- 0.36 | 3.70 | -0.17 |
| Spatial & Grounding | 7 | 57.52 +/- 1.58 | 59.15 +/- 0.08 | 64.63 +/- 0.15 | 1.63 | -5.48 |
| Perception & Counting | 5 | 48.26 +/- 0.46 | 51.14 +/- 0.25 | 52.36 +/- 0.47 | 2.88 | -1.22 |
| Puzzles & Logic | 5 | 33.51 +/- 0.45 | 36.97 +/- 0.58 | 38.37 +/- 0.18 | 3.46 | -1.40 |

## Benchmark Means

| Category | Benchmark | Rows | Qwen2.5-VL-7B Base | TRACE Qwen2.5-VL-7B | VERO Qwen2.5-VL-7B | TRACE - Base | TRACE - VERO |
|---|---|---|---|---|---|---|---|
| Charts & Tables | ChartMuseum | 1000 | 41.47 +/- 0.12 | 41.57 +/- 0.12 | 41.57 +/- 0.15 | 0.10 | 0.00 |
| Charts & Tables | ChartQAPro | 1948 | 45.81 +/- 0.24 | 48.05 +/- 0.40 | 40.87 +/- 0.42 | 2.24 | 7.18 |
| Charts & Tables | CharXivReason | 1000 | 39.73 +/- 1.17 | 47.13 +/- 0.35 | 45.83 +/- 0.84 | 7.40 | 1.30 |
| Charts & Tables | TableVQABench | 1500 | 75.20 +/- 0.90 | 78.31 +/- 0.17 | 78.47 +/- 0.45 | 3.11 | -0.16 |
| Charts & Tables | EvoChart | 1250 | 57.07 +/- 0.72 | 64.91 +/- 0.05 | 63.55 +/- 0.17 | 7.84 | 1.36 |
| Visual Math | MathVision | 3040 | 24.81 +/- 0.75 | 27.42 +/- 0.62 | 28.15 +/- 0.08 | 2.61 | -0.72 |
| Visual Math | MathVista | 1000 | 68.67 +/- 0.40 | 73.37 +/- 0.45 | 76.80 +/- 0.36 | 4.70 | -3.43 |
| Visual Math | MathVerse | 788 | 43.44 +/- 0.92 | 47.76 +/- 0.51 | 50.93 +/- 1.14 | 4.31 | -3.17 |
| Visual Math | WeMath | 1740 | 35.20 +/- 2.92 | 46.16 +/- 1.32 | 46.92 +/- 0.36 | 10.96 | -0.76 |
| Science & General | PhyX mini MC | 1000 | 40.97 +/- 3.57 | 48.70 +/- 0.82 | 46.63 +/- 0.21 | 7.73 | 2.07 |
| Science & General | Physics | 1297 | 8.95 +/- 0.10 | 9.23 +/- 0.44 | 10.34 +/- 0.80 | 0.28 | -1.11 |
| Science & General | MMMU-ProVis | 1730 | 35.70 +/- 0.39 | 39.36 +/- 0.71 | 39.67 +/- 0.47 | 3.66 | -0.31 |
| Science & General | MMStar | 1500 | 61.89 +/- 0.87 | 65.64 +/- 0.34 | 65.78 +/- 0.32 | 3.76 | -0.13 |
| Spatial & Grounding | ScreenSpot | 1272 | 80.77 +/- 3.84 | 81.66 +/- 0.92 | 89.81 +/- 0.57 | 0.89 | -8.15 |
| Spatial & Grounding | SpatialVizBench COT | 1180 | 35.14 +/- 0.10 | 35.68 +/- 0.34 | 32.06 +/- 0.47 | 0.54 | 3.62 |
| Spatial & Grounding | CV-Bench 3D | 1200 | 76.25 +/- 1.96 | 81.00 +/- 0.43 | 83.11 +/- 0.59 | 4.75 | -2.11 |
| Spatial & Grounding | ERQA | 400 | 39.00 +/- 1.56 | 41.17 +/- 1.28 | 44.58 +/- 0.80 | 2.17 | -3.42 |
| Perception & Counting | Blink | 1901 | 53.31 +/- 1.23 | 56.57 +/- 0.73 | 57.51 +/- 0.67 | 3.26 | -0.95 |
| Perception & Counting | CountBenchQA | 487 | 82.14 +/- 1.48 | 84.80 +/- 1.44 | 82.96 +/- 0.21 | 2.67 | 1.85 |
| Perception & Counting | CountQA | 1528 | 19.59 +/- 1.17 | 22.51 +/- 0.91 | 23.17 +/- 0.29 | 2.92 | -0.65 |
| Perception & Counting | TreeBench | 405 | 38.02 +/- 1.37 | 40.25 +/- 2.11 | 41.48 +/- 0.89 | 2.22 | -1.23 |
| Puzzles & Logic | PuzzleVQA | 2000 | 44.57 +/- 0.64 | 50.02 +/- 0.50 | 49.22 +/- 0.25 | 5.45 | 0.80 |
| Puzzles & Logic | VisualPuzzles | 1168 | 31.08 +/- 0.15 | 34.02 +/- 0.77 | 36.96 +/- 0.44 | 2.94 | -2.94 |
| Puzzles & Logic | LogicVista | 447 | 42.65 +/- 2.24 | 47.35 +/- 0.68 | 47.65 +/- 0.67 | 4.70 | -0.30 |
| Puzzles & Logic | MME-Reasoning | 1188 | 25.17 +/- 1.18 | 28.03 +/- 0.89 | 30.61 +/- 0.73 | 2.86 | -2.58 |
| Perception & Counting | MMVP | 300 | 48.22 +/- 3.08 | 51.56 +/- 0.38 | 56.67 +/- 2.40 | 3.33 | -5.11 |
| Spatial & Grounding | ScreenSpotPro | 1581 | 18.34 +/- 1.81 | 18.72 +/- 0.33 | 40.14 +/- 0.16 | 0.38 | -21.42 |
| Spatial & Grounding | ScreenSpot v2 | 1272 | 83.70 +/- 3.82 | 84.85 +/- 0.25 | 92.11 +/- 0.12 | 1.15 | -7.26 |
| Spatial & Grounding | EmbSpatial | 3640 | 69.42 +/- 0.90 | 70.95 +/- 0.69 | 70.60 +/- 0.07 | 1.53 | 0.35 |
| Science & General | RealWorldQA | 765 | 65.45 +/- 0.87 | 68.50 +/- 0.68 | 69.85 +/- 0.72 | 3.05 | -1.35 |
| Puzzles & Logic | VisuLogic | 1000 | 24.07 +/- 2.48 | 25.43 +/- 1.03 | 27.43 +/- 0.92 | 1.37 | -2.00 |
| Overall | Average |  | 46.96 +/- 0.19 | 50.34 +/- 0.17 | 51.98 +/- 0.04 | 3.38 | -1.64 |

Decoding: temperature 0.6, top-p 1, top-k -1, no penalties, maximum 4096 generated tokens. ScreenSpot, ScreenSpotPro, and ScreenSpot v2 use a 16384-token maximum.
Scoring: faithful Final25 routes plus MMVP and five pinned VLMEvalKit Final31 additions.

# TRACE Final20 Temp0.6 3B/7B All Methods Results

Deterministic repair note: ScreenSpot/TableVQABench cached predictions are re-parsed for final-answer wrappers and positional `pyautogui.click(x, y)` calls; no generation or judge rerun was used.

## 3B
| Benchmark           |    Rows |   Qwen2.5-VL-3B Base (3-seed avg) |   Qwen2.5-VL-3B Answer GRPO 500 (3-seed avg) |   Qwen2.5-VL-3B Annotation GRPO 500 (seed42) |
|:--------------------|--------:|----------------------------------:|---------------------------------------------:|---------------------------------------------:|
| Blink               | 1901.00 |                             44.52 |                                        46.50 |                                        47.03 |
| ChartMuseum         | 1000.00 |                             17.83 |                                        21.30 |                                        18.00 |
| ChartQAPro          | 1948.00 |                             32.08 |                                        33.27 |                                        33.82 |
| CharXivReason       | 1000.00 |                             29.20 |                                        34.27 |                                        32.70 |
| CountBenchQA        |  487.00 |                             65.57 |                                        68.65 |                                        73.31 |
| CV-Bench 3D         | 1200.00 |                             59.50 |                                        67.31 |                                        62.58 |
| Game-QA-Lite        | 2633.00 |                             18.60 |                                        20.96 |                                        21.31 |
| LogicVista          |  447.00 |                             36.84 |                                        42.65 |                                        36.47 |
| MathVision          | 3040.00 |                             19.93 |                                        24.61 |                                        21.88 |
| MathVista           | 1000.00 |                             58.43 |                                        64.60 |                                        64.00 |
| MMMU-ProVis         | 1730.00 |                             26.76 |                                        30.83 |                                        27.69 |
| Physics             | 1297.00 |                             20.59 |                                        20.43 |                                        20.20 |
| PhyX mini MC        | 1000.00 |                             32.97 |                                        37.73 |                                        33.80 |
| PuzzleVQA           | 2000.00 |                             33.03 |                                        40.35 |                                        37.85 |
| ScreenSpot          | 1272.00 |                             68.19 |                                        64.02 |                                        77.52 |
| SpatialVizBench COT | 1180.00 |                             25.45 |                                        26.86 |                                        28.14 |
| TableVQABench       | 1500.00 |                             69.12 |                                        71.88 |                                        72.48 |
| TreeBench           |  405.00 |                             39.18 |                                        40.74 |                                        38.27 |
| VisualPuzzles       | 1168.00 |                             17.32 |                                        18.86 |                                        17.38 |
| WeMath              | 1740.00 |                             46.93 |                                        57.87 |                                        51.67 |
| Average             |  nan    |                             38.10 |                                        41.68 |                                        40.80 |

## 7B
| Benchmark           |    Rows |   Qwen2.5-VL-7B Base (3-seed avg) |   Qwen2.5-VL-7B Answer GRPO 500 (3-seed avg) |   OpenMOSS Game-RL Qwen2.5-VL-7B (seed42) |   Sphinx Qwen2.5-VL-7B 500 (seed42) |   PCGRPO Qwen2.5-VL-7B Jigsaw CARE (seed42) |   Vero Qwen2.5-VL-7B (seed42) |
|:--------------------|--------:|----------------------------------:|---------------------------------------------:|------------------------------------------:|------------------------------------:|--------------------------------------------:|------------------------------:|
| Blink               | 1901.00 |                             53.20 |                                        58.76 |                                     54.08 |                               55.34 |                                       56.23 |                         57.29 |
| ChartMuseum         | 1000.00 |                             24.43 |                                        32.50 |                                     24.50 |                               24.40 |                                       25.10 |                         29.00 |
| ChartQAPro          | 1948.00 |                             46.55 |                                        49.03 |                                     46.85 |                               44.68 |                                       41.27 |                         41.65 |
| CharXivReason       | 1000.00 |                             39.17 |                                        46.43 |                                     39.70 |                               40.60 |                                       40.80 |                         46.40 |
| CountBenchQA        |  487.00 |                             82.82 |                                        85.08 |                                     84.80 |                               83.16 |                                       82.96 |                         83.57 |
| CV-Bench 3D         | 1200.00 |                             76.67 |                                        81.39 |                                     75.83 |                               79.92 |                                       81.08 |                         82.67 |
| Game-QA-Lite        | 2633.00 |                             24.93 |                                        29.08 |                                     30.27 |                               25.07 |                                       25.94 |                         46.79 |
| LogicVista          |  447.00 |                             42.80 |                                        47.73 |                                     44.07 |                               43.40 |                                       43.18 |                         45.86 |
| MathVision          | 3040.00 |                             25.96 |                                        27.96 |                                     26.48 |                               26.28 |                                       25.39 |                         27.34 |
| MathVista           | 1000.00 |                             69.13 |                                        73.43 |                                     68.00 |                               70.80 |                                       71.10 |                         76.50 |
| MMMU-ProVis         | 1730.00 |                             35.03 |                                        39.88 |                                     35.84 |                               36.99 |                                       34.28 |                         40.00 |
| Physics             | 1297.00 |                             20.71 |                                        25.80 |                                     21.05 |                               20.35 |                                       16.73 |                         17.73 |
| PhyX mini MC        | 1000.00 |                             40.10 |                                        47.63 |                                     40.40 |                               40.90 |                                       42.70 |                         46.30 |
| PuzzleVQA           | 2000.00 |                             46.85 |                                        53.18 |                                     49.45 |                               47.15 |                                       50.05 |                         49.80 |
| ScreenSpot          | 1272.00 |                             72.64 |                                        77.86 |                                     75.31 |                               81.05 |                                        8.25 |                         67.85 |
| SpatialVizBench COT | 1180.00 |                             26.50 |                                        31.61 |                                     29.41 |                               27.88 |                                       29.49 |                         31.19 |
| TableVQABench       | 1500.00 |                             74.92 |                                        77.99 |                                     74.13 |                               73.12 |                                       69.68 |                         78.64 |
| TreeBench           |  405.00 |                             40.91 |                                        43.21 |                                     39.26 |                               40.49 |                                       40.74 |                         41.73 |
| VisualPuzzles       | 1168.00 |                             19.35 |                                        22.32 |                                     19.18 |                               18.49 |                                       20.21 |                         23.54 |
| WeMath              | 1740.00 |                             63.95 |                                        67.89 |                                     65.34 |                               65.17 |                                       65.06 |                         72.36 |
| Average             |  nan    |                             46.33 |                                        50.94 |                                     47.20 |                               47.26 |                                       43.51 |                         50.31 |

## Metadata
| key                     | value                                                                                                                             |
|:------------------------|:----------------------------------------------------------------------------------------------------------------------------------|
| source_existing         | results/trace_final20_temp06_3b7b_model_results.xlsx                                                                              |
| source_vero             | results/trace_final20_temp06_seed42_vero-qwen25-7b_20260714T192431Z_results.xlsx                                                  |
| decoding                | temperature=0.6, seed=42 for single-seed external methods; 3-seed average where labeled                                           |
| benchmarks              | TRACE final20                                                                                                                     |
| screenspot_table_repair | Re-parsed cached predictions for ScreenSpot positional clicks and TableVQABench final-answer wrappers; no generation/judge rerun. |

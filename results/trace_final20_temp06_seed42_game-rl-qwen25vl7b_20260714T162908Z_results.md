# game-rl-qwen25vl7b TRACE Final20 Temp0.6 Results

VisualPuzzles repair note: cached Qwen3 extraction outputs are re-scored with the benchmark-wide A-D option contract; no generation or judge rerun was used.

| benchmark_key       | benchmark           | dataset_alias         | prompt_run                             |   game-rl-qwen25vl7b |   game-rl-qwen25vl7b rows | game-rl-qwen25vl7b score run           |
|:--------------------|:--------------------|:----------------------|:---------------------------------------|---------------------:|--------------------------:|:---------------------------------------|
| chartmuseum         | ChartMuseum         | ChartMuseum_test      | vlmevalkit_defaults_qwen32b_judge_test |                24.50 |                   1000.00 | vlmevalkit_defaults_qwen32b_judge_test |
| game_qa_lite        | Game-QA-Lite        | Game-QA-Lite          | vlmevalkit_cot_boxed                   |                30.27 |                   2633.00 | llm_extracted                          |
| screenspot          | ScreenSpot          | ScreenSpot            | vlmevalkit_defaults_sample200          |                75.31 |                   1272.00 | vlmevalkit_defaults_sample200          |
| chartqapro          | ChartQAPro          | ChartQAPro_CoT        | vlmevalkit_faithful_cot                |                46.85 |                   1948.00 | llm_extracted                          |
| puzzlevqa           | PuzzleVQA           | PuzzleVQA             | vlmevalkit_reasoning                   |                49.45 |                   2000.00 | llm_extracted                          |
| logicvista          | LogicVista          | LogicVista            | vlmevalkit_defaults_qwen32b_judge      |                44.07 |                    447.00 | vlmevalkit_defaults_qwen32b_judge      |
| mathvista           | MathVista           | MathVista_MINI        | vlmevalkit_defaults_qwen32b_judge      |                68.00 |                   1000.00 | vlmevalkit_defaults_qwen32b_judge      |
| visualpuzzles       | VisualPuzzles       | VisualPuzzles         | vlmevalkit_reasoning                   |                21.40 |                   1168.00 | llm_extracted                          |
| cvbench_3d          | CV-Bench 3D         | CV-Bench-3D           | vlmevalkit_defaults                    |                75.83 |                   1200.00 | llm_extracted                          |
| wemath              | WeMath              | WeMath_COT            | vlmevalkit_cot_qwen32b_judge           |                65.34 |                   1740.00 | llm_extracted                          |
| mathvision          | MathVision          | MathVision            | vlmevalkit_defaults_qwen32b_judge      |                26.48 |                   3040.00 | vlmevalkit_defaults_qwen32b_judge      |
| treebench           | TreeBench           | TreeBench             | vlmevalkit_defaults                    |                39.26 |                    405.00 | llm_extracted                          |
| countbenchqa        | CountBenchQA        | CountBenchQA          | vlmevalkit_defaults                    |                84.80 |                    487.00 | llm_extracted                          |
| charxivreason       | CharXivReason       | CharXiv_reasoning_val | vlmevalkit_defaults_qwen32b_judge      |                39.70 |                   1000.00 | vlmevalkit_defaults_qwen32b_judge      |
| phyx_mini_mc        | PhyX mini MC        | PhyX_mini_MC          | vlmevalkit_defaults                    |                40.40 |                   1000.00 | llm_extracted                          |
| spatialvizbench_cot | SpatialVizBench COT | SpatialVizBench_CoT   | vlmevalkit_cot                         |                29.41 |                   1180.00 | llm_extracted                          |
| physics             | Physics             | Physics               | vlmevalkit_reasoning                   |                21.05 |                   1297.00 | llm_extracted                          |
| tablevqabench       | TableVQABench       | TableVQABench         | vlmevalkit_defaults                    |                74.13 |                   1500.00 | vlmevalkit_defaults                    |
| mmmu_pro_vision     | MMMU-ProVis         | MMMU_Pro_V_COT        | vlmevalkit_cot_max2048                 |                35.84 |                   1730.00 | llm_extracted                          |
| blink               | Blink               | BLINK                 | vlmevalkit_defaults                    |                54.08 |                   1901.00 | llm_extracted                          |
| average             | Average             | nan                   | nan                                    |                47.19 |                    nan    | nan                                    |

## Metadata
| key             | value                                                                                                                                                         |
|:----------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| suite           | trace_final20_temp06_seed42                                                                                                                                   |
| subset_root     | final20 full eval; candidate benchmarks use trace_candidate24_full subset manifests; SpatialVizBench/TableVQABench/VisualPuzzles use full VLMEvalKit datasets |
| benchmark_count | 20                                                                                                                                                            |
| models          | game-rl-qwen25vl7b                                                                                                                                            |

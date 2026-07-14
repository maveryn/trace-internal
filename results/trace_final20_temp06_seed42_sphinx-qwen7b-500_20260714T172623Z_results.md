# sphinx-qwen7b-500 TRACE Final20 Temp0.6 Results

VisualPuzzles repair note: cached Qwen3 extraction outputs are re-scored with the benchmark-wide A-D option contract; no generation or judge rerun was used.

| benchmark_key       | benchmark           | dataset_alias         | prompt_run                             |   sphinx-qwen7b-500 |   sphinx-qwen7b-500 rows | sphinx-qwen7b-500 score run            |
|:--------------------|:--------------------|:----------------------|:---------------------------------------|--------------------:|-------------------------:|:---------------------------------------|
| chartmuseum         | ChartMuseum         | ChartMuseum_test      | vlmevalkit_defaults_qwen32b_judge_test |               24.40 |                  1000.00 | vlmevalkit_defaults_qwen32b_judge_test |
| game_qa_lite        | Game-QA-Lite        | Game-QA-Lite          | vlmevalkit_cot_boxed                   |               25.07 |                  2633.00 | llm_extracted                          |
| screenspot          | ScreenSpot          | ScreenSpot            | vlmevalkit_defaults_sample200          |               81.05 |                  1272.00 | vlmevalkit_defaults_sample200          |
| chartqapro          | ChartQAPro          | ChartQAPro_CoT        | vlmevalkit_faithful_cot                |               44.68 |                  1948.00 | llm_extracted                          |
| puzzlevqa           | PuzzleVQA           | PuzzleVQA             | vlmevalkit_reasoning                   |               47.15 |                  2000.00 | llm_extracted                          |
| logicvista          | LogicVista          | LogicVista            | vlmevalkit_defaults_qwen32b_judge      |               43.40 |                   447.00 | vlmevalkit_defaults_qwen32b_judge      |
| mathvista           | MathVista           | MathVista_MINI        | vlmevalkit_defaults_qwen32b_judge      |               70.80 |                  1000.00 | vlmevalkit_defaults_qwen32b_judge      |
| visualpuzzles       | VisualPuzzles       | VisualPuzzles         | vlmevalkit_reasoning                   |               22.09 |                  1168.00 | llm_extracted                          |
| cvbench_3d          | CV-Bench 3D         | CV-Bench-3D           | vlmevalkit_defaults                    |               79.92 |                  1200.00 | llm_extracted                          |
| wemath              | WeMath              | WeMath_COT            | vlmevalkit_cot_qwen32b_judge           |               65.17 |                  1740.00 | llm_extracted                          |
| mathvision          | MathVision          | MathVision            | vlmevalkit_defaults_qwen32b_judge      |               26.28 |                  3040.00 | vlmevalkit_defaults_qwen32b_judge      |
| treebench           | TreeBench           | TreeBench             | vlmevalkit_defaults                    |               40.49 |                   405.00 | llm_extracted                          |
| countbenchqa        | CountBenchQA        | CountBenchQA          | vlmevalkit_defaults                    |               83.16 |                   487.00 | llm_extracted                          |
| charxivreason       | CharXivReason       | CharXiv_reasoning_val | vlmevalkit_defaults_qwen32b_judge      |               40.60 |                  1000.00 | vlmevalkit_defaults_qwen32b_judge      |
| phyx_mini_mc        | PhyX mini MC        | PhyX_mini_MC          | vlmevalkit_defaults                    |               40.90 |                  1000.00 | llm_extracted                          |
| spatialvizbench_cot | SpatialVizBench COT | SpatialVizBench_CoT   | vlmevalkit_cot                         |               27.88 |                  1180.00 | llm_extracted                          |
| physics             | Physics             | Physics               | vlmevalkit_reasoning                   |               20.35 |                  1297.00 | llm_extracted                          |
| tablevqabench       | TableVQABench       | TableVQABench         | vlmevalkit_defaults                    |               73.12 |                  1500.00 | vlmevalkit_defaults                    |
| mmmu_pro_vision     | MMMU-ProVis         | MMMU_Pro_V_COT        | vlmevalkit_cot_max2048                 |               36.99 |                  1730.00 | llm_extracted                          |
| blink               | Blink               | BLINK                 | vlmevalkit_defaults                    |               55.34 |                  1901.00 | llm_extracted                          |
| average             | Average             | nan                   | nan                                    |               47.26 |                   nan    | nan                                    |

## Metadata
| key             | value                                                                                                                                                         |
|:----------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| suite           | trace_final20_temp06_seed42                                                                                                                                   |
| subset_root     | final20 full eval; candidate benchmarks use trace_candidate24_full subset manifests; SpatialVizBench/TableVQABench/VisualPuzzles use full VLMEvalKit datasets |
| benchmark_count | 20                                                                                                                                                            |
| models          | sphinx-qwen7b-500                                                                                                                                             |

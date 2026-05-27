# External Benchmark Results

Scores are collected from `benchmark/<dataset>/<model>/<run_name>/scores.json`.
Generation setup follows the benchmark-specific policy in `benchmark/evaluation_plan.md`.

## Model Comparison

| Benchmark | `qwen3-vl-4b-instruct` | `trace-qwen3vl4b-alpha0-answer-step250` | `trace-qwen3vl4b-alpha0-5-answer-step250` | `trace-qwen3vl4b-alpha1-answer-step250` |
|---|---:|---:|---:|---:|
| ChartQAPro | 52.37 | 52.86 | 51.95 | 53.41 |
| ChartMuseum | 42.00 | 42.10 | 42.00 | 42.40 |
| CharXivDesc | 80.27 | 81.67 | 81.85 | 81.30 |
| CharXivReason | 44.20 | 43.80 | 43.00 | 42.60 |
| EvoChart | 61.04 | 60.80 | 60.16 | 61.04 |
| InfoVQA | 79.22 | 79.49 | 79.66 | 79.96 |
| MMMU-ProVis | 36.42 | 37.69 | 37.80 | 38.79 |
| MathVision | 51.09 | 44.21 | 44.41 | 45.03 |
| MathVista | 74.60 | 74.10 | 74.60 | 75.10 |
| MathVerse | 35.28 | 36.68 | 35.91 | 35.79 |
| LogicVista | 59.73 | 60.40 | 56.38 | 58.39 |
| Blink | 53.34 | 52.08 | 51.92 | 52.13 |
| ERQA | 40.75 | 40.75 | 39.75 | 39.75 |
| EmbSpatial | 78.32 | 78.35 | 78.38 | 78.43 |
| RoboSpatialHome | 41.14 | 41.43 | 40.86 | 41.71 |
| Game-QA-Lite | 33.84 | 33.61 | 34.71 | 34.56 |
| CountQA | 28.53 | 28.53 | 28.60 | 28.99 |
| VStarBench | 78.01 | 74.35 | 75.39 | 75.39 |
| MMStar | 34.33 | 32.07 | 32.20 | 32.20 |
| MME-RealWorld-Lite | 47.58 | 47.26 | 47.52 | 46.95 |
| TreeBench | 43.21 | 41.48 | 40.99 | 41.73 |
| VLMBlind | 55.22 | 55.40 | 55.35 | 55.52 |
| ScreenSpotPro | 0.70 | 0.76 | 0.70 | 0.76 |

## Detailed Results

| Model | Benchmark | Split / Variant | Rows | Score | Status | Artifacts |
|---|---|---|---:|---:|---|---|
| `qwen3-vl-4b-instruct` | Blink | `vlmevalkit_defaults` | 1901 | 53.34 | done | `benchmark/blink/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | CharXivDesc | `vlmevalkit_defaults_qwen32b_judge` | 4000 | 80.27 | done | `benchmark/charxivdesc/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge/` |
| `qwen3-vl-4b-instruct` | CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 44.20 | done | `benchmark/charxivreason/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge/` |
| `qwen3-vl-4b-instruct` | ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 42.00 | done | `benchmark/chartmuseum/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge_test/` |
| `qwen3-vl-4b-instruct` | ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 52.37 | done | `benchmark/chartqapro/qwen3-vl-4b-instruct/vlmevalkit_faithful_cot/` |
| `qwen3-vl-4b-instruct` | CountQA | `vlmevalkit_defaults` | 1528 | 28.53 | done | `benchmark/countqa/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | ERQA | `vlmevalkit_defaults` | 400 | 40.75 | done | `benchmark/erqa/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | EmbSpatial | `vlmevalkit_defaults` | 3640 | 78.32 | done | `benchmark/embspatial/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | EvoChart | `vlmevalkit_vero_qwen3_zs` | 1250 | 61.04 | done | `benchmark/evochart/qwen3-vl-4b-instruct/vlmevalkit_vero_qwen3_zs/` |
| `qwen3-vl-4b-instruct` | Game-QA-Lite | `vlmevalkit_defaults` | 2633 | 33.84 | done | `benchmark/game_qa_lite/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | InfoVQA | `vlmevalkit_defaults_val` | 2801 | 79.22 | done | `benchmark/infovqa/qwen3-vl-4b-instruct/vlmevalkit_defaults_val/` |
| `qwen3-vl-4b-instruct` | LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 59.73 | done | `benchmark/logicvista/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge/` |
| `qwen3-vl-4b-instruct` | MME-RealWorld-Lite | `vlmevalkit_defaults` | 1919 | 47.58 | done | `benchmark/mme_realworld_lite/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 36.42 | done | `benchmark/mmmu_pro_vision/qwen3-vl-4b-instruct/vlmevalkit_cot_max2048/` |
| `qwen3-vl-4b-instruct` | MMStar | `vlmevalkit_defaults` | 1500 | 34.33 | done | `benchmark/mmstar/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 35.28 | done | `benchmark/mathverse/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge/` |
| `qwen3-vl-4b-instruct` | MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 51.09 | done | `benchmark/mathvision/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge/` |
| `qwen3-vl-4b-instruct` | MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 74.60 | done | `benchmark/mathvista/qwen3-vl-4b-instruct/vlmevalkit_defaults_qwen32b_judge/` |
| `qwen3-vl-4b-instruct` | RoboSpatialHome | `vlmevalkit_defaults` | 350 | 41.14 | done | `benchmark/robospatialhome/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | ScreenSpotPro | `vlmevalkit_defaults_pooled` | 1581 | 0.70 | done | `benchmark/screenspotpro/qwen3-vl-4b-instruct/vlmevalkit_defaults_pooled/` |
| `qwen3-vl-4b-instruct` | TreeBench | `vlmevalkit_defaults` | 405 | 43.21 | done | `benchmark/treebench/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | VLMBlind | `vlmevalkit_defaults` | 8016 | 55.22 | done | `benchmark/vlmblind/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `qwen3-vl-4b-instruct` | VStarBench | `vlmevalkit_defaults` | 191 | 78.01 | done | `benchmark/vstarbench/qwen3-vl-4b-instruct/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | Blink | `vlmevalkit_defaults` | 1901 | 51.92 | done | `benchmark/blink/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | CharXivDesc | `vlmevalkit_defaults_qwen32b_judge` | 4000 | 81.85 | done | `benchmark/charxivdesc/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 43.00 | done | `benchmark/charxivreason/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 42.00 | done | `benchmark/chartmuseum/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_qwen32b_judge_test/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 51.95 | done | `benchmark/chartqapro/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_faithful_cot/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | CountQA | `vlmevalkit_defaults` | 1528 | 28.60 | done | `benchmark/countqa/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | ERQA | `vlmevalkit_defaults` | 400 | 39.75 | done | `benchmark/erqa/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | EmbSpatial | `vlmevalkit_defaults` | 3640 | 78.38 | done | `benchmark/embspatial/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | EvoChart | `vlmevalkit_vero_qwen3_zs` | 1250 | 60.16 | done | `benchmark/evochart/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_vero_qwen3_zs/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | Game-QA-Lite | `vlmevalkit_defaults` | 2633 | 34.71 | done | `benchmark/game_qa_lite/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | InfoVQA | `vlmevalkit_defaults_val` | 2801 | 79.66 | done | `benchmark/infovqa/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_val/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 56.38 | done | `benchmark/logicvista/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | MME-RealWorld-Lite | `vlmevalkit_defaults` | 1919 | 47.52 | done | `benchmark/mme_realworld_lite/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 37.80 | done | `benchmark/mmmu_pro_vision/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_cot_max2048/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | MMStar | `vlmevalkit_defaults` | 1500 | 32.20 | done | `benchmark/mmstar/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 35.91 | done | `benchmark/mathverse/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 44.41 | done | `benchmark/mathvision/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 74.60 | done | `benchmark/mathvista/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | RoboSpatialHome | `vlmevalkit_defaults` | 350 | 40.86 | done | `benchmark/robospatialhome/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | ScreenSpotPro | `vlmevalkit_defaults_pooled` | 1581 | 0.70 | done | `benchmark/screenspotpro/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults_pooled/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | TreeBench | `vlmevalkit_defaults` | 405 | 40.99 | done | `benchmark/treebench/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | VLMBlind | `vlmevalkit_defaults` | 8016 | 55.35 | done | `benchmark/vlmblind/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-5-answer-step250` | VStarBench | `vlmevalkit_defaults` | 191 | 75.39 | done | `benchmark/vstarbench/trace-qwen3vl4b-alpha0-5-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | Blink | `vlmevalkit_defaults` | 1901 | 52.08 | done | `benchmark/blink/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | CharXivDesc | `vlmevalkit_defaults_qwen32b_judge` | 4000 | 81.67 | done | `benchmark/charxivdesc/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 43.80 | done | `benchmark/charxivreason/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 42.10 | done | `benchmark/chartmuseum/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_qwen32b_judge_test/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 52.86 | done | `benchmark/chartqapro/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_faithful_cot/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | CountQA | `vlmevalkit_defaults` | 1528 | 28.53 | done | `benchmark/countqa/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | ERQA | `vlmevalkit_defaults` | 400 | 40.75 | done | `benchmark/erqa/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | EmbSpatial | `vlmevalkit_defaults` | 3640 | 78.35 | done | `benchmark/embspatial/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | EvoChart | `vlmevalkit_vero_qwen3_zs` | 1250 | 60.80 | done | `benchmark/evochart/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_vero_qwen3_zs/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | Game-QA-Lite | `vlmevalkit_defaults` | 2633 | 33.61 | done | `benchmark/game_qa_lite/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | InfoVQA | `vlmevalkit_defaults_val` | 2801 | 79.49 | done | `benchmark/infovqa/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_val/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 60.40 | done | `benchmark/logicvista/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | MME-RealWorld-Lite | `vlmevalkit_defaults` | 1919 | 47.26 | done | `benchmark/mme_realworld_lite/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 37.69 | done | `benchmark/mmmu_pro_vision/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_cot_max2048/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | MMStar | `vlmevalkit_defaults` | 1500 | 32.07 | done | `benchmark/mmstar/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 36.68 | done | `benchmark/mathverse/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 44.21 | done | `benchmark/mathvision/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 74.10 | done | `benchmark/mathvista/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | RoboSpatialHome | `vlmevalkit_defaults` | 350 | 41.43 | done | `benchmark/robospatialhome/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | ScreenSpotPro | `vlmevalkit_defaults_pooled` | 1581 | 0.76 | done | `benchmark/screenspotpro/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults_pooled/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | TreeBench | `vlmevalkit_defaults` | 405 | 41.48 | done | `benchmark/treebench/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | VLMBlind | `vlmevalkit_defaults` | 8016 | 55.40 | done | `benchmark/vlmblind/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha0-answer-step250` | VStarBench | `vlmevalkit_defaults` | 191 | 74.35 | done | `benchmark/vstarbench/trace-qwen3vl4b-alpha0-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | Blink | `vlmevalkit_defaults` | 1901 | 52.13 | done | `benchmark/blink/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | CharXivDesc | `vlmevalkit_defaults_qwen32b_judge` | 4000 | 81.30 | done | `benchmark/charxivdesc/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 42.60 | done | `benchmark/charxivreason/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 42.40 | done | `benchmark/chartmuseum/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_qwen32b_judge_test/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 53.41 | done | `benchmark/chartqapro/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_faithful_cot/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | CountQA | `vlmevalkit_defaults` | 1528 | 28.99 | done | `benchmark/countqa/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | ERQA | `vlmevalkit_defaults` | 400 | 39.75 | done | `benchmark/erqa/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | EmbSpatial | `vlmevalkit_defaults` | 3640 | 78.43 | done | `benchmark/embspatial/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | EvoChart | `vlmevalkit_vero_qwen3_zs` | 1250 | 61.04 | done | `benchmark/evochart/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_vero_qwen3_zs/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | Game-QA-Lite | `vlmevalkit_defaults` | 2633 | 34.56 | done | `benchmark/game_qa_lite/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | InfoVQA | `vlmevalkit_defaults_val` | 2801 | 79.96 | done | `benchmark/infovqa/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_val/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 58.39 | done | `benchmark/logicvista/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | MME-RealWorld-Lite | `vlmevalkit_defaults` | 1919 | 46.95 | done | `benchmark/mme_realworld_lite/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 38.79 | done | `benchmark/mmmu_pro_vision/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_cot_max2048/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | MMStar | `vlmevalkit_defaults` | 1500 | 32.20 | done | `benchmark/mmstar/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 35.79 | done | `benchmark/mathverse/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 45.03 | done | `benchmark/mathvision/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 75.10 | done | `benchmark/mathvista/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_qwen32b_judge/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | RoboSpatialHome | `vlmevalkit_defaults` | 350 | 41.71 | done | `benchmark/robospatialhome/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | ScreenSpotPro | `vlmevalkit_defaults_pooled` | 1581 | 0.76 | done | `benchmark/screenspotpro/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults_pooled/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | TreeBench | `vlmevalkit_defaults` | 405 | 41.73 | done | `benchmark/treebench/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | VLMBlind | `vlmevalkit_defaults` | 8016 | 55.52 | done | `benchmark/vlmblind/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |
| `trace-qwen3vl4b-alpha1-answer-step250` | VStarBench | `vlmevalkit_defaults` | 191 | 75.39 | done | `benchmark/vstarbench/trace-qwen3vl4b-alpha1-answer-step250/vlmevalkit_defaults/` |

## Notes

- ChartMuseum scores use a local `Qwen/Qwen3-32B` judge approximation because the official benchmark uses GPT-4.1-mini judging.
- CharXiv, MathVision, MathVista, MathVerse, and LogicVista use local `Qwen/Qwen3-32B` judging where required by the evaluator.
- ScreenSpotPro is reported as a pooled sample-wise aggregate over the six `ScreenSpot_Pro_*` subsets when all subset scores are present.
- If an evaluator emits category scores without an explicit overall score, the table reports the mean over numeric category scores.
- Existing per-run README files and `scores.json` files remain the source of detailed generation and judge settings.

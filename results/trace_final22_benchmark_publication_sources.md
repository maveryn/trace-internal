# TRACE Final22 Benchmark Publication Sources

This note records paper/source metadata for the TRACE final20 benchmark set plus
`EvoChart` and `MathVerse`.

The "venue / status" column is conservative. If I found only an arXiv paper,
dataset card, or toolkit source rather than a confirmed peer-reviewed venue, the
row says so explicitly.

## Benchmark Sources

| Benchmark | Local alias / split | Paper or primary source | Venue / status | Year | Notes |
| --- | --- | --- | --- | ---: | --- |
| Blink | `BLINK` | [BLINK: Multimodal Large Language Models Can See but Not Perceive](https://arxiv.org/abs/2404.12390) | [ECCV 2024](https://dl.acm.org/doi/10.1007/978-3-031-73337-6_9) | 2024 | Perception-heavy benchmark over classic CV-style tasks. |
| ChartMuseum | `ChartMuseum_test` | [ChartMuseum: Testing Visual Reasoning Capabilities of Large Vision-Language Models](https://arxiv.org/abs/2505.13444) | NeurIPS 2025 reported by [author page](https://www.bodunhu.com/) / DBLP pages; arXiv source is the primary open paper link | 2025 | Use the test split in local eval. |
| ChartQAPro | `ChartQAPro_CoT` | [ChartQAPro: A More Diverse and Challenging Benchmark for Chart Question Answering](https://aclanthology.org/2025.findings-acl.978/) | Findings of ACL 2025 | 2025 | Local eval uses the CoT prompt variant. |
| CharXivReason | `CharXiv_reasoning_val` | [CharXiv: Charting Gaps in Realistic Chart Understanding in Multimodal LLMs](https://proceedings.neurips.cc/paper_files/paper/2024/hash/cdf6f8e9fd9aeaf79b6024caec24f15b-Abstract-Datasets_and_Benchmarks_Track.html) | NeurIPS 2024 Datasets and Benchmarks Track | 2024 | We use the reasoning validation split. |
| CountBenchQA | `CountBenchQA` | [CountBenchQA dataset card](https://huggingface.co/datasets/vikhyatk/CountBenchQA); CountBench from [Teaching CLIP to Count to Ten](https://openaccess.thecvf.com/content/ICCV2023/html/Paiss_Teaching_CLIP_to_Count_to_Ten_ICCV_2023_paper.html); VQA form cited by [PaliGemma](https://arxiv.org/html/2407.07726v1) | CountBench: ICCV 2023; CountBenchQA: HF/PaliGemma eval dataset, no separate standalone venue found | 2023 / 2024 | CountBenchQA converts CountBench images into VQA counting questions. |
| CV-Bench 3D | `CV-Bench-3D` | [Cambrian-1: A Fully Open, Vision-Centric Exploration of Multimodal LLMs](https://arxiv.org/abs/2406.16860) | [NeurIPS 2024 Oral](https://cambrian-mllm.github.io/cambrian-1/) | 2024 | CV-Bench is introduced inside Cambrian-1; we use the 3D subset. |
| Game-QA-Lite | `Game-QA-Lite` | [Game-QA-Lite dataset card](https://huggingface.co/datasets/gsarch/Game-QA-Lite); related release/context in [Vero: An Open RL Recipe for General Visual Reasoning](https://arxiv.org/html/2604.04917v1) | HF dataset / Vero arXiv preprint; no standalone Game-QA-Lite venue found | 2026 | Treat as a dataset-release benchmark. It overlaps with Vero's GameQA training/eval ecosystem, so exclude from fair Vero headline averages if needed. |
| LogicVista | `LogicVista` | [LogicVista: Multimodal LLM Logical Reasoning Benchmark in Visual Contexts](https://arxiv.org/abs/2407.04973) | arXiv preprint / OpenReview record; no formal venue confirmed from primary sources | 2024 | 448-question visual logical reasoning benchmark. |
| MathVision | `MathVision` | [Measuring Multimodal Mathematical Reasoning with MATH-Vision Dataset](https://papers.nips.cc/paper_files/paper/2024/hash/ad0edc7d5fa1a783f063646968b7315b-Abstract-Datasets_and_Benchmarks_Track.html) | NeurIPS 2024 Datasets and Benchmarks Track | 2024 | Competition-style visual math problems. |
| MathVista | `MathVista_MINI` | [MathVista: Evaluating Mathematical Reasoning of Foundation Models in Visual Contexts](https://proceedings.iclr.cc/paper_files/paper/2024/hash/663bce02a0050c4a11f1eb8a7f1429d3-Abstract-Conference.html) | ICLR 2024 | 2024 | We use the mini/testmini-style split through VLMEvalKit. |
| MMMU-ProVis | `MMMU_Pro_V_COT` | [MMMU-Pro: A More Robust Multi-discipline Multimodal Understanding Benchmark](https://aclanthology.org/2025.acl-long.736/) | ACL 2025 Long Papers | 2025 | Local alias is the vision-only / CoT variant. |
| Physics | `Physics` | VLMEvalKit [`Physics_yale`](https://github.com/open-compass/VLMEvalKit/blob/main/vlmeval/dataset/image_vqa.py) / OpenCompass-hosted Physics TSVs | Toolkit-hosted benchmark source; no standalone benchmark paper found | 2025 | Local VLMEvalKit source maps `Physics` to `Physics_yale` and OpenCompass TSV URLs. |
| PhyX mini MC | `PhyX_mini_MC` | [PhyX: Does Your Model Have the "Wits" for Physical Reasoning?](https://arxiv.org/abs/2505.15929) | arXiv preprint; no formal venue confirmed from primary sources | 2025 | We use the mini multiple-choice split. |
| PuzzleVQA | `PuzzleVQA` | [PuzzleVQA: Diagnosing Multimodal Reasoning Challenges of Language Models with Abstract Visual Patterns](https://aclanthology.org/2024.findings-acl.962/) | Findings of ACL 2024 | 2024 | Abstract visual pattern reasoning. |
| ScreenSpot | `ScreenSpot` | [SeeClick: Harnessing GUI Grounding for Advanced Visual GUI Agents](https://aclanthology.org/2024.acl-long.505/) | ACL 2024 Long Papers | 2024 | SeeClick introduced ScreenSpot as a GUI grounding benchmark. |
| SpatialVizBench COT | `SpatialVizBench_CoT` | [SpatialViz-Bench: A Cognitively-Grounded Benchmark for Diagnosing Spatial Visualization in MLLMs](https://arxiv.org/abs/2507.07610) | arXiv preprint; no formal venue confirmed from primary sources | 2025 | Local eval uses the CoT prompt variant. |
| TableVQABench | `TableVQABench` | [TableVQA-Bench: A Visual Question Answering Benchmark on Multiple Table Domains](https://arxiv.org/abs/2404.19205) | arXiv preprint / dataset release; no formal venue confirmed from primary sources | 2024 | Built from WTQ, TabFact, and FinTabNet-style table sources. |
| TreeBench | `TreeBench` | [Traceable Evidence Enhanced Visual Grounded Reasoning: Evaluation and Methodology](https://arxiv.org/abs/2507.07999) | arXiv preprint | 2025 | TreeBench is the benchmark; TreeVGR is the associated training/evaluation method. |
| VisualPuzzles | `VisualPuzzles` | [VisualPuzzles: Decoupling Multimodal Reasoning Evaluation from Domain Knowledge](https://arxiv.org/abs/2504.10342) | arXiv preprint / OpenReview record; no formal venue confirmed from primary sources | 2025 | Knowledge-light visual reasoning benchmark. |
| WeMath | `WeMath_COT` | [We-Math: Does Your Large Multimodal Model Achieve Human-like Mathematical Reasoning?](https://aclanthology.org/2025.acl-long.983/) | ACL 2025 Long Papers | 2025 | Local eval uses the CoT variant. WeMath overlaps with Vero training data. |
| EvoChart | `EvoChart_Qwen3_ZS` | [EvoChart: A Benchmark and a Self-Training Approach Towards Real-World Chart Understanding](https://ojs.aaai.org/index.php/AAAI/article/view/32383) | AAAI 2025 | 2025 | Added as an extra chart benchmark; EvoChart overlaps with Vero training data. |
| MathVerse | `MathVerse_MINI_Vision_Only_cot` | [MathVerse: Does Your Multi-modal LLM Truly See the Diagrams in Visual Math Problems?](https://arxiv.org/abs/2403.14624) | [ECCV 2024](https://dl.acm.org/doi/10.1007/978-3-031-73242-3_10) | 2024 | Local eval uses the mini vision-only CoT variant. |

## Fairness Caveats

- `Game-QA-Lite`, `WeMath`, and `EvoChart` should be treated carefully when
  comparing against Vero because the Vero paper/release uses the corresponding
  GameQA, WeMath, and EvoChart data families.
- `Physics` is kept in the table because it is part of our 20-benchmark eval
  suite, but I did not find a standalone benchmark paper. The provenance is the
  VLMEvalKit `Physics_yale` adapter and OpenCompass-hosted TSV source.
- Several 2025 benchmarks are currently arXiv/dataset releases. If later
  accepted versions appear, update this document rather than silently treating
  preprints as conference papers.

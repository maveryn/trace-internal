# Benchmark Results

Curated benchmark score summaries live here.

Directory layout:

```text
benchmark/<dataset>/<model>/<run_name>/scores.json
benchmark/<dataset>/<model>/<run_name>/README.md
```

Full model outputs and prediction files should live under the repo-level
`runs/` directory, with the same `<dataset>/<model>/<run_name>/` layout.

## Final20 Evaluation

Use `scripts/run_trace_final20_temp06_seed42_single_model.sh` for the
canonical single-model final evaluation suite. It runs these 20 benchmarks:

```text
Blink
ChartMuseum
ChartQAPro
CharXivReason
CountBenchQA
CV-Bench 3D
Game-QA-Lite
LogicVista
MathVision
MathVista
MMMU-ProVis
Physics
PhyX mini MC
PuzzleVQA
ScreenSpot
SpatialVizBench COT
TableVQABench
TreeBench
VisualPuzzles
WeMath
```

The default decoding configuration is the current final-eval setting:
`temperature=0.6`, `top_p=1.0`, `top_k=-1`, no presence penalty,
`repetition_penalty=1.0`, `max_tokens=4096`, and `seed=42`. The script starts
an 8-endpoint vLLM pool for generation, then starts a Qwen3-32B endpoint pool
for benchmark judge/extraction passes.

Example:

```bash
MODEL_PATH=/dev/shm/trace_rlvr/hf_models/sphinx_qwen7b_500 \
MODEL_SLUG=sphinx-qwen7b-500 \
bash scripts/run_trace_final20_temp06_seed42_single_model.sh
```

Outputs are written under `/dev/shm/trace_rlvr/<run_tag>/` and summarized to
`results/<run_tag>_results.md` plus `results/<run_tag>_results.xlsx`.

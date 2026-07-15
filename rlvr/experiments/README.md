# TRACE Answer-Only RLVR and Final25 Evaluation

This directory is the canonical, self-contained experiment record for the
reported TRACE answer-only Qwen2.5-VL models and the Final25 evaluation suite.
The machine-readable companion is
[`final_answer_only_manifest.json`](final_answer_only_manifest.json).

## Canonical implementation

| Component | Path |
| --- | --- |
| 3B training entry point | [`scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh`](../../scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh) |
| 7B training entry point | [`scripts/run_trace_qwen25vl7b_easyr1_answer_nokl_tmpfs.sh`](../../scripts/run_trace_qwen25vl7b_easyr1_answer_nokl_tmpfs.sh) |
| Shared EasyR1 launcher | [`scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh`](../../scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh) |
| Answer system prompt | [`rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt`](../examples/prompts/trace_vero_json_system_prompt_answer.txt) |
| Reward function | [`rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py`](../easyr1_backend/examples/reward_function/trace_rlvr.py) |
| GRPO and policy loss | [`rlvr/easyr1_backend/verl/trainer/core_algos.py`](../easyr1_backend/verl/trainer/core_algos.py) |
| Final25 launcher | [`scripts/run_trace_final25_temp06_3seed_8models.sh`](../../scripts/run_trace_final25_temp06_3seed_8models.sh) |
| Final25 benchmark registry | [`scripts/benchmark_queue_lib.py`](../../scripts/benchmark_queue_lib.py) |
| Frozen scoring contracts | [`scripts/trace_final25_contract.py`](../../scripts/trace_final25_contract.py) |
| Multi-seed summarizer | [`scripts/summarize_trace_final25_multiseed.py`](../../scripts/summarize_trace_final25_multiseed.py) |

The reported 3B run started at repository revision
`32977891fceba573cc856e9c3da26f93385ed4a5` and resumed at
`4251bcaeb0f49fe27a449e81fb40415c219821f5`. The 7B run used
`9a65120f77b4046e8e99218b1a50382b681d28ad`. Final25 generation and the
frozen scoring contract were audited at
`92ee98fa82f068e582b03f84ff8f2481f8334c6f`.

## Training data

Both models use the same semantic all-task TRACE corpus:

| Split | Tasks | Samples/task | Rows | Generation seed | Role |
| --- | ---: | ---: | ---: | ---: | --- |
| Train | 1,000 | 64 | 64,000 | 42 | RLVR updates |
| Validation | 1,000 | 2 | 2,000 | 1042 | IID monitoring every 100 steps |

Images are embedded in parquet. Exported images are capped at 1,280,000
pixels. The train dataloader shuffles with seed 1. With 128 prompts per step,
500 steps consume exactly 64,000 prompt rows, or one dataloader pass. Eight
rollouts per prompt produce 1,024 sampled responses per update and 512,000
sampled training responses in total.

The exact byte-level sources differ because the 3B run preceded the viewer
shuffle and the 7B run used the sharded Hugging Face export:

| Model | Exact source | Prompt column | Provenance |
| --- | --- | --- | --- |
| 3B | `trace_rlvr_train_64000_all1000_seed42.parquet` and `trace_rlvr_validation_iid_2000_all1000_seed1042.parquet` | `prompt_answer_only` | SHA-256 `5aab653cc0ceea28f5cf597493572a5deb624714d2aebb027f30d7e79579765a` and `0be8b114454f8b9814cac9e70f412fb1e19a143775c8b27501e1400a682414a4` |
| 7B | [`maveryn/trace`](https://huggingface.co/datasets/maveryn/trace) revision `e317b746b258630682367cc6a9d87dedd195113c` | `prompt_answer` | 16 train shards and one validation parquet |

The two sources were verified to contain identical sets of 64,000 train and
2,000 validation `instance_id` values. For every ID, `task`, `answer_gt`, and
`trace_ref` match, and the 3B `prompt_answer_only` value equals the 7B
`prompt_answer` value. Their row ordering and physical schemas are different,
so the sources are pinned separately rather than treated as byte-identical
files.

## Prompt and reward

The following text is supplied as a system message. The dataset's selected
answer prompt is supplied as the user message with its image.

```text
You are a helpful, conversational assistant tasked with answering a question about an image.

Reason carefully from the image and the question to determine the answer.

End your response with a JSON object in this format:
{"answer": ...}
```

The prompt file SHA-256 is
`f394927d9abcfb7a1e43ef48a30c29b8c70e6facdbda314d7b27c59d8c3ae900`.

For response `y` and typed ground truth `a*`:

1. The scorer finds an `{"answer": ...}` object and canonicalizes its value and
   `a*`. Strings are stripped and lowercased, numeric scalars are normalized,
   dictionary keys are sorted, and sequences retain order.
2. `R_answer = 1` only when the canonical values are exactly equal; otherwise
   it is 0.
3. `R_format = 1` only when the response ends in a valid JSON object whose key
   set is exactly `{"answer"}`. A correct answer may still be extracted from a
   nonterminal object, but it then receives no format credit.
4. The bounded scalar reward is:

```text
R = 0.95 * R_answer + 0.05 * R_format
```

The reward mode is `answer`, answer scoring is `exact_json`, and the configured
weights are answer `1.0`, annotation `0.0`, and format `0.05`.

## GRPO update

This is GRPO with a token-level clipped PPO policy objective. It is not GSPO.
For prompt group `g`, each of its eight responses receives scalar reward `r_i`.
The response advantage is:

```text
A_i = (r_i - mean(r_g)) / (std(r_g) + 1e-6)
```

PyTorch's sample standard deviation is used. `A_i` is copied to every valid
response token. The token importance ratio is
`rho_t = exp(log pi_theta - log pi_old)`, clamped numerically before the
exponential. The policy objective uses:

- lower ratio clip: `1 - 0.2 = 0.8`
- upper ratio clip: `1 + 0.3 = 1.3`
- dual-clip bound for negative advantages: `3.0`
- one policy epoch per generated batch
- token-mean loss aggregation over non-padding response tokens

There is no critic/value model in the GRPO path. KL-to-reference is disabled
(`disable_kl=true`, `use_kl_loss=false`, `kl_coef=0`), and there is no entropy
bonus. Entropy and old/new-policy approximate KL may be logged as diagnostics,
but neither is added to the loss.

## Training configuration

| Parameter | Value |
| --- | --- |
| Base models | `Qwen/Qwen2.5-VL-3B-Instruct`, `Qwen/Qwen2.5-VL-7B-Instruct` |
| Steps | 500 |
| Prompt batch per step | 128 |
| Rollouts per prompt | 8 |
| Responses per update | 1,024 |
| Prompt / response cap | 2,048 / 2,048 tokens |
| Train sampling | temperature 1.0, top-p 1.0, top-k -1, seed 1 |
| Actor optimizer | fused AdamW, LR `1e-6`, betas `(0.9, 0.999)`, weight decay `0.01` |
| LR schedule | constant, no warmup |
| Gradient clipping | global norm 1.0 |
| Policy microbatch/device | experience 2, update 1, dynamic token batching |
| Precision | BF16 parameters, FP32 FSDP reductions and buffers |
| Distributed strategy | single node, 8 GPUs, FSDP full shard |
| Parameterization | full-parameter training, LoRA rank 0 |
| Vision tower | trainable (`freeze_vision_tower=false`) |
| Memory controls | gradient checkpointing, parameter and optimizer offload |
| Rollout engine | hybrid vLLM, tensor parallel 2 |
| Rollout memory | utilization 0.60, max 8,192 batched tokens |
| Image processor range | 262,144 to 4,194,304 pixels |
| Validation | 2,000 IID rows, batch 1,024, temperature 0.6, top-p 0.95, one response |
| Validation/checkpoint interval | every 100 steps; no validation before training |
| Logging | console and Weights & Biases project `trace_easyr1` |

The recorded machine had 8 NVIDIA H100 80GB HBM3 GPUs and driver 570.195.03.
The recorded Python environment included PyTorch 2.8.0+cu128, Transformers
4.57.6, vLLM 0.10.2, Ray 2.56.0, Datasets 5.0.0, PyArrow 24.0.0, and W&B
0.26.1.

## Trained checkpoints

| Model | Base revision | Training run | W&B | Merged checkpoint fingerprint |
| --- | --- | --- | --- | --- |
| Qwen2.5-VL-3B Answer GRPO 500 | `66285546d2b821cf421d4f5eb2576359d3770cd3` | `trace_qwen25vl3b_easyr1_all1000_answer_nokl_step200_bsz128_rollout8_iidval2000_20260711T141819Z`, resumed from step 200 to 500 | [`hj1ichjk`](https://wandb.ai/llm-reasoning-rl/trace_easyr1/runs/hj1ichjk) | config `29cadee0...0f4`; index `713a5e05...3ce9` |
| Qwen2.5-VL-7B Answer GRPO 500 | `cc594898137f460bfe9f0759e9844b3ce807cfb5` | `trace_qwen25vl7b_easyr1_all1000_answer_nokl_step500_bsz128_rollout8_iidval2000_20260712T073500Z` | [`jiswyznz`](https://wandb.ai/llm-reasoning-rl/trace_easyr1/runs/jiswyznz) | config `90932c21...0141`; index `cccf1415...b8d4` |

The full SHA-256 values for the merged model shards and metadata are in the
manifest. The step-500 actor, optimizer, dataloader, and extra state were saved
before conversion to merged Hugging Face format.

## Final25 evaluation protocol

Final25 evaluates full benchmark splits, not sampled subsets. Each model is
generated independently with decoding seeds 42, 43, and 44. These are three
generation seeds for one fixed checkpoint, not three independent training
seeds.

Model generation uses benchmark-specific VLMEvalKit/local prompts and the same
prompt path for every model. The TRACE training system prompt is not injected
into benchmark evaluation. The common decoding contract is:

```text
temperature = 0.6
top_p = 1.0
top_k = -1
presence_penalty = 0.0
repetition_penalty = 1.0
max_tokens = 4096
```

Effective caps are 2,048 for WeMath and MMMU-ProVis and 1,024 for ScreenSpot;
all other benchmarks use 4,096. Images sent to the endpoints are constrained
to at most 1,000,000 pixels and 1,280 pixels on the longest side, encoded as
JPEG quality 85 when conversion is required.

Generation uses eight one-GPU vLLM OpenAI-compatible endpoints with 32 client
workers per endpoint, GPU memory utilization 0.90, max model length 32,768,
max 256 sequences, and max 32,768 batched tokens. One model remains loaded
while all 25 benchmarks and three seeds are generated, minimizing reloads.

Judge-backed extraction/scoring uses eight one-GPU endpoints serving
[`Qwen/Qwen3-32B`](https://huggingface.co/Qwen/Qwen3-32B) revision
`9216db5781bf21249d130ec9da846c4624c16137` at temperature 0. Judge responses
are validated; malformed outputs fail the scoring job rather than silently
becoming incorrect answers. Raw model response, extracted answer, judge output,
normalized prediction/ground truth, and row score are retained.

### Evaluated models

| Label | Model source | Revision |
| --- | --- | --- |
| Qwen2.5-VL-3B Base | [`Qwen/Qwen2.5-VL-3B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct) | `66285546d2b821cf421d4f5eb2576359d3770cd3` |
| Qwen2.5-VL-3B Answer GRPO 500 | merged checkpoint above | checkpoint fingerprint in manifest |
| Qwen2.5-VL-7B Base | [`Qwen/Qwen2.5-VL-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | `cc594898137f460bfe9f0759e9844b3ce807cfb5` |
| Qwen2.5-VL-7B Answer GRPO 500 | merged checkpoint above | checkpoint fingerprint in manifest |
| OpenMOSS Game-RL Qwen2.5-VL-7B | [`OpenMOSS-Team/Game-RL-Qwen2.5-VL-7B`](https://huggingface.co/OpenMOSS-Team/Game-RL-Qwen2.5-VL-7B) | `205b5934ce70504cfd6ae26b16f705d0b98b9306` |
| Sphinx Qwen2.5-VL-7B 500 | [`xashru/sphinx_qwen7b_500`](https://huggingface.co/xashru/sphinx_qwen7b_500) | `6ffefb03d5cb0767683bfb42a084ea86b707ef9a` |
| PCGRPO Qwen2.5-VL-7B Jigsaw CARE | [`armenjeddi/PCGRPO-Qwen2.5-VL-7B-Jigsaw-with-curriculum-with-grpo-care`](https://huggingface.co/armenjeddi/PCGRPO-Qwen2.5-VL-7B-Jigsaw-with-curriculum-with-grpo-care) | `921bbced4176f5d362e98c843a57656c5d78dad7` |
| Vero Qwen2.5-VL-7B | [`zlab-princeton/Vero-Qwen25-7B`](https://huggingface.co/zlab-princeton/Vero-Qwen25-7B) | `180e84be5acb2aa887cf51015b84b6a6e453ee90` |

### Benchmarks and scoring

`Judge` means the Qwen3-32B judge is used for extraction, semantic scoring, or
both. Exact-option and exact-integer checks remain deterministic after judge
extraction.

| Category | Benchmark | VLMEvalKit/local alias | Rows | Cap | Extraction and primary scoring | Judge | Paper/source |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| Charts, Tables & Structured Figures | ChartMuseum | `ChartMuseum_test` | 1,000 | 4096 | Preserve answer; semantic correctness against reference | scoring | [ChartMuseum](https://arxiv.org/abs/2505.13444) |
| Charts, Tables & Structured Figures | ChartQAPro | `ChartQAPro_CoT` | 1,948 | 4096 | Extract final answer; official normalized scorer | extraction | [Findings ACL 2025](https://aclanthology.org/2025.findings-acl.978/) |
| Charts, Tables & Structured Figures | CharXivReason | `CharXiv_reasoning_val` | 1,000 | 4096 | Benchmark rubric extracts and scores answer | both | [NeurIPS 2024 D&B](https://proceedings.neurips.cc/paper_files/paper/2024/hash/cdf6f8e9fd9aeaf79b6024caec24f15b-Abstract-Datasets_and_Benchmarks_Track.html) |
| Charts, Tables & Structured Figures | TableVQABench | `TableVQABench` | 1,500 | 4096 | Deterministic wrapper parser; four official split scorers | none | [TableVQA-Bench](https://arxiv.org/abs/2404.19205) |
| Charts, Tables & Structured Figures | EvoChart | `EvoChart` | 1,250 | 4096 | Semantic extraction/scoring with numeric tolerance | both | [AAAI 2025](https://ojs.aaai.org/index.php/AAAI/article/view/32383) |
| Visual Mathematics | MathVision | `MathVision` | 3,040 | 4096 | Official prefetch or answer extraction; official normalized scorer | extraction fallback | [NeurIPS 2024 D&B](https://papers.nips.cc/paper_files/paper/2024/hash/ad0edc7d5fa1a783f063646968b7315b-Abstract-Datasets_and_Benchmarks_Track.html) |
| Visual Mathematics | MathVista | `MathVista_MINI` | 1,000 | 4096 | Official prefetch or answer extraction; official normalized scorer | extraction fallback | [ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/663bce02a0050c4a11f1eb8a7f1429d3-Abstract-Conference.html) |
| Visual Mathematics | MathVerse | `MathVerse_MINI_Vision_Only_cot` | 788 | 4096 | Extract answer; official prefetch or strict binary correctness | both/fallback | [ECCV 2024](https://arxiv.org/abs/2403.14624) |
| Visual Mathematics | WeMath | `WeMath_COT` | 1,740 | 2048 | Extract option; exact option-letter match | extraction | [ACL 2025](https://aclanthology.org/2025.acl-long.983/) |
| Science & Academic Reasoning | PhyX mini MC | `PhyX_mini_MC` | 1,000 | 4096 | Extract A-D option; exact match | extraction | [PhyX](https://arxiv.org/abs/2505.15929) |
| Science & Academic Reasoning | Physics | `Physics` | 1,297 | 4096 | Extract while judging strict semantic correctness | both | [VLMEvalKit source](https://github.com/open-compass/VLMEvalKit) |
| Science & Academic Reasoning | MMMU-ProVis | `MMMU_Pro_V_COT` | 1,730 | 2048 | Extract option; exact option-letter match | extraction | [ACL 2025](https://aclanthology.org/2025.acl-long.736/) |
| Science & Academic Reasoning | MMStar | `MMStar` | 1,500 | 4096 | Extract A-D option; exact match | extraction | [NeurIPS 2024](https://arxiv.org/abs/2403.20330) |
| Spatial, 3D, Embodied & UI Grounding | ScreenSpot | `ScreenSpot` | 1,272 | 1024 | Parse click coordinate; point inside target box | none | [ACL 2024](https://aclanthology.org/2024.acl-long.505/) |
| Spatial, 3D, Embodied & UI Grounding | SpatialVizBench COT | `SpatialVizBench_CoT` | 1,180 | 4096 | Extract option; exact option-letter match | extraction | [SpatialViz-Bench](https://arxiv.org/abs/2507.07610) |
| Spatial, 3D, Embodied & UI Grounding | CV-Bench 3D | `CV-Bench-3D` | 1,200 | 4096 | Extract option; exact option-letter match | extraction | [NeurIPS 2024](https://arxiv.org/abs/2406.16860) |
| Spatial, 3D, Embodied & UI Grounding | ERQA | `ERQA` | 400 | 4096 | Extract A-D option; exact match | extraction | [Gemini Robotics report](https://arxiv.org/abs/2503.20020) |
| Visual Perception, Counting & Evidence Grounding | Blink | `BLINK` | 1,901 | 4096 | Extract option; exact option-letter match | extraction | [ECCV 2024](https://arxiv.org/abs/2404.12390) |
| Visual Perception, Counting & Evidence Grounding | CountBenchQA | `CountBenchQA` | 487 | 4096 | Extract integer; normalized exact match | extraction | [CountBenchQA](https://huggingface.co/datasets/vikhyatk/CountBenchQA) |
| Visual Perception, Counting & Evidence Grounding | CountQA | `CountQA` | 1,528 | 4096 | Extract integer; normalized exact match | extraction | [CountQA](https://arxiv.org/abs/2508.06585) |
| Visual Perception, Counting & Evidence Grounding | TreeBench | `TreeBench` | 405 | 4096 | Extract source-labeled option; exact match | extraction | [TreeBench](https://arxiv.org/abs/2507.07999) |
| Puzzles & Abstract Logic | PuzzleVQA | `PuzzleVQA` | 2,000 | 4096 | Extract option/value and map to option; exact match | extraction | [Findings ACL 2024](https://aclanthology.org/2024.findings-acl.962/) |
| Puzzles & Abstract Logic | VisualPuzzles | `VisualPuzzles` | 1,168 | 4096 | Extract A-D option; exact match | extraction | [VisualPuzzles](https://arxiv.org/abs/2504.10342) |
| Puzzles & Abstract Logic | LogicVista | `LogicVista` | 447 | 4096 | Extract option set; official normalized exact-set match | extraction | [LogicVista](https://arxiv.org/abs/2407.04973) |
| Puzzles & Abstract Logic | MME-Reasoning | `MME-Reasoning` | 1,188 | 4096 | Official task-specific extraction and deterministic functions; semantic judge for open answers | both | [MME-Reasoning](https://arxiv.org/abs/2505.21327) |

The suite contains 31,969 rows per model and seed. TableVQABench's primary
score is the macro mean of its four official split scores. Every other primary
benchmark score is row accuracy in percent. The overall Final25 score is an
unweighted macro average of the 25 primary benchmark scores, so large datasets
do not dominate the aggregate.

For comparisons involving Vero, WeMath and EvoChart must be marked as known
training-data-family overlaps based on the Vero release. Keep their scores in
the complete table, but do not present them as held-out evidence without that
qualification.

For each model and benchmark, report the arithmetic mean and sample standard
deviation across seeds 42, 43, and 44. Model deltas must pair the same benchmark
rows and generation seeds. Because there is one trained checkpoint per scale,
these standard deviations measure decoding variation, not training-run
variation.

## Reproduction checks

Before accepting a result table:

1. Run `python -m unittest tests.test_trace_final25_scoring_contract -v`.
2. Run `scripts/verify_trace_final25_campaign.py` for both generation and score
   phases with all model slugs and all three seeds.
3. Confirm every generation summary has `rows == expected_rows`, no row errors,
   and the expected decoding parameters.
4. Confirm every judge-backed route retained valid extraction/judge artifacts.
5. Generate the final workbook and Markdown with
   `scripts/summarize_trace_final25_multiseed.py`; do not average rows across
   datasets directly.

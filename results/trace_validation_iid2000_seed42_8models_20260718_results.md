# TRACE IID validation evaluation — seed 42

This campaign evaluates one response from each of eight models on the pinned
2,000-row TRACE validation split. The rows are non-overlapping IID samples from
the same 1,000 tasks used for training, with two validation samples per task.
This is not a held-out-task or task-generalization benchmark.

## Overall results

`Combined semantic` is the primary answer metric. `Historical answer` preserves
the training-time scorer, while `Terminal format` measures its required
terminal JSON format. Every percentage uses all 2,000 rows per model as the
denominator.

| Model | Combined semantic | Historical answer | Terminal format | Judge fallback | Unresolved |
|---|---:|---:|---:|---:|---:|
| TRACE Qwen2.5-VL-7B | **51.55%** | 51.60% | 100.00% | 0.15% | 0.15% |
| TRACE Qwen2.5-VL-3B | **41.05%** | 41.05% | 99.75% | 0.35% | 0.35% |
| VERO Qwen2.5-VL-7B | 38.40% | 31.55% | 0.00% | 22.15% | 1.75% |
| Game-RL Qwen2.5-VL-7B | 35.55% | 35.50% | 99.35% | 1.05% | 0.85% |
| Qwen2.5-VL-7B Base | 34.25% | 34.20% | 99.55% | 1.30% | 1.30% |
| PCGRPO Qwen2.5-VL-7B | 34.10% | 34.10% | 100.00% | 0.50% | 0.45% |
| Sphinx Qwen2.5-VL-7B | 33.50% | 33.50% | 99.85% | 1.00% | 1.00% |
| Qwen2.5-VL-3B Base | 24.45% | 24.40% | 98.65% | 3.55% | 3.15% |

On the paired rows, TRACE 3B improves over the 3B base by **16.60 points**:
TRACE-only correct on 529 rows, base-only correct on 197, both correct on 292,
and both incorrect on 982. TRACE 7B improves over the 7B base by **17.30
points**: TRACE-only correct on 526 rows, base-only correct on 180, both correct
on 505, and both incorrect on 789.

## Frozen protocol

- Suite: `trace-iid-validation-2000-answer-seed42-v1`, SHA-256
  `8ca9888542175e37cd1dfcfad0d48ec9d3340752b78394277ba6cd0244eaf776`.
- Dataset: `maveryn/trace@e317b746b258630682367cc6a9d87dedd195113c`,
  validation parquet SHA-256
  `0cb46bcf858ae3e9f39b88f60a24549a5de133976b9e8b74a45b4e6e4d699470`.
- Prompt: the row's `prompt_answer` plus
  `rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt` at SHA-256
  `f394927d9abcfb7a1e43ef48a30c29b8c70e6facdbda314d7b27c59d8c3ae900`,
  rendered with each checkpoint's native chat template.
- Generation: one response, seed 42, temperature 0.6, top-p 0.95, top-k -1,
  repetition penalty 1.0, and at most 2,048 generated tokens.
- Extraction: ground-truth-blind deterministic parsing first. Exactly 601 of
  16,000 responses entered the Qwen3-32B fallback. The judge received only the
  raw response and declared answer type, never the question, image, choices,
  or reference answer.
- Judge: `Qwen/Qwen3-32B@9216db5781bf21249d130ec9da846c4624c16137`,
  temperature 0, thinking disabled. It returned 421 valid answers, 53
  `missing`, 36 `ambiguous`, and 91 strict failures. All 180 unresolved rows
  remain incorrect and in the denominator.

## Model revisions

| Model | Immutable source revision | Runtime view revision |
|---|---|---|
| Qwen2.5-VL-3B Base | `Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3` | same as source |
| TRACE Qwen2.5-VL-3B | `maveryn/trace-qwen2.5-vl-3b@2ec2374d5c219e6b12e26bda93d3b3adeb1e30c5` | `sha256set:fd7d9ef4dd828eb950ce29c8ccde0432ccd31420529d4f023300ede928d070a1` |
| Qwen2.5-VL-7B Base | `Qwen/Qwen2.5-VL-7B-Instruct@cc594898137f460bfe9f0759e9844b3ce807cfb5` | same as source |
| TRACE Qwen2.5-VL-7B | `maveryn/trace-qwen2.5-vl-7b@4d0f1ae8ee25022058090dbdbff61957ece7331d` | `sha256set:28421ef2be848d24e2a9fa363d885f42c651bfb6fa986de3d07faa9d78da47cf` |
| Game-RL Qwen2.5-VL-7B | `OpenMOSS-Team/Game-RL-Qwen2.5-VL-7B@205b5934ce70504cfd6ae26b16f705d0b98b9306` | `sha256set:2a805cbedc07225555712644c3569019da15a30108bb50b2dbe60d9562d24b2f` |
| Sphinx Qwen2.5-VL-7B | `xashru/sphinx_qwen7b_500@6ffefb03d5cb0767683bfb42a084ea86b707ef9a` | same as source |
| PCGRPO Qwen2.5-VL-7B | `armenjeddi/PCGRPO-Qwen2.5-VL-7B-Jigsaw-with-curriculum-with-grpo-care@921bbced4176f5d362e98c843a57656c5d78dad7` | same as source |
| VERO Qwen2.5-VL-7B | `zlab-princeton/Vero-Qwen25-7B@180e84be5acb2aa887cf51015b84b6a6e453ee90` | same as source |

## Verification and artifact ownership

The full verifier passed with exactly eight models, 2,000 rows per model,
16,000 generation rows, 16,000 scored rows, and one-to-one coverage of all 601
judge requests. The final aggregate summary SHA-256 is
`c4dda04ab5391ed7283a7b85c5e0730f177c9a469adb43691e951566d6999e45`.

The canonical response, extraction, score, result, and provenance export
belongs under run `trace-iid-validation-2000-answer-seed42-8models-v1` in
`maveryn/trace-eval-runs`. Raw receipts, prompts, ground truth, media paths,
judge caches, logs, and machine-local paths are excluded from that export and
from this Git report.

The run was sealed at Hugging Face data revision
`cf0d14aed86db2661d397ce8b68b36171873478d` and documented at repository head
`b3b37f633b4bcfea294185051e05a930191984b3`. Its export manifest SHA-256 is
`73fe4d1d5e8008452720206fbbf404960b0490a397823fd3f4c77ddc94634a48`, and its
evaluation harness revision is
`b7e4bcf2bae88684a442834419d41d74c58e3eac`.

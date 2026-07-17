# Remote Artifact Handoff

This receipt records the durable state required to continue TRACE paper and
release work after the current GPU host is retired. It intentionally records
immutable remote identities rather than machine-local paths.

After verifying the remote identities in this receipt, continue with
[`PUBLIC_RELEASE/RELEASE_COMPLETION_CHECKLIST.md`](PUBLIC_RELEASE/RELEASE_COMPLETION_CHECKLIST.md).

## Source repositories

- Internal source: `maveryn/trace-internal`, branch `rlvr`. The GPU-host
  handoff point is tagged `gpu-host-handoff-20260717` after the active baseline
  campaign and its publication receipt are complete.
- Public source: `maveryn/trace`, branches `main` and `rlvr`. Local commit
  `d5d0215ff887e15c2ffafac632f27a3e0e76b5e8` contains the validated public CI,
  release constraints, verifier documentation, release checker, and an explicit
  RLVR release boundary. Its push requires a GitHub credential with `repo` and
  `workflow` scopes. A two-patch recovery copy is stored at
  `maveryn/trace-internal-eval-runs@a53ce5f687851532db7ba4f8c761237634b4f96a`
  under `handoff/public-repository/d5d0215/`.
- Public `rlvr` is intentionally not populated during this handoff. Curate the
  paper training and canonical evaluation surface separately on the next
  machine; do not copy the internal evaluation tree wholesale.

## Dataset and models

| Artifact | Immutable remote identity | Notes |
| --- | --- | --- |
| TRACE dataset | `maveryn/trace@e317b746b258630682367cc6a9d87dedd195113c` | Pinned paper-training revision; all 17 local Parquet files were hash-verified against HF. Documented repository head at handoff: `0e4bbdb2d422cffcb22f0753dac7a094eed493f1`. |
| TRACE 7B | `maveryn/trace-qwen2.5-vl-7b@4d0f1ae8ee25022058090dbdbff61957ece7331d` | Evaluation-bound merged inference checkpoint, 16.60 GB; all local safetensor hashes match HF. Documentation-only head: `d82f048bfb459595e3ebe14bc69e3fd8894f1732`. |
| TRACE 3B | `maveryn/trace-qwen2.5-vl-3b@2ec2374d5c219e6b12e26bda93d3b3adeb1e30c5` | Evaluation-bound merged inference checkpoint, 8.15 GB; all local safetensor hashes match HF. Documentation-only head: `557bd92bd626c10754aa765876839524f485929a`. |

The full EasyR1/FSDP optimizer checkpoints are deliberately not uploaded. They
are approximately 109 GB for 7B and 51 GB for 3B and are unnecessary for
inference, evaluation, paper release, or reproducing training from the pinned
base model and configuration. Preserve them separately only if exact
post-step-500 optimizer-state continuation becomes a requirement.

## Evaluation artifacts

| Scope | Repository and revision | Coverage |
| --- | --- | --- |
| Canonical 7B comparison | `maveryn/trace-eval-runs@4178a839b689babe16f8ac36f0de7b1b2c5ef36c` | Base, TRACE, and VERO; 24 benchmarks; seeds 42/43/44; 648 response/extraction/score slices. The immutable run prefix remains valid after later repository appends. |
| Canonical 3B comparison | `maveryn/trace-eval-runs@4178a839b689babe16f8ac36f0de7b1b2c5ef36c` | Base and TRACE; 24 benchmarks; seeds 42/43/44; 432 slices. The immutable run prefix remains valid after repository-level documentation changes. |
| RL 7B baselines | `maveryn/trace-eval-runs@4ca25af7a4d7daa644e6f35e070dbed1af078321` | Game-RL, Sphinx, and PCGRPO; 24 benchmarks; seeds 42/43/44; 648 response/extraction/score slices. Repository documentation head: `b61d7702d0c95435869597b1050c8140d5b0d1f2`. |
| Internal supplementary comparison | `maveryn/trace-internal-eval-runs@04267dc31304f1bd5ed41b8930db63b03d3b8d29` | Seven non-paper benchmarks; three 7B models; three seeds; 189 slices. |
| Historical standalone candidates | `maveryn/trace-internal-eval-runs@67bebe1a23d112b20a0c517e863c750714635ca7` | Noncanonical RealWorldQA and VStarBench seed-42 archives under `historical/standalone-candidate-runs/20260716/`. |

The private internal archive's documented handoff head is
`a8c87dbdba6ec8d1bacff95b9040cd8d541ca2ae`. It records that legacy slice
manifests and recovery patches may preserve historical machine paths as private
provenance; new unsanitized paths must not be added.

The canonical repositories contain neutral machine-readable
`metadata/results/benchmark_scores.json` files in addition to row-level
responses and extractions, score records, and provenance slices. Per-example
score records are present only where the official route emits them; aggregate
score records exist for every model, seed, and benchmark. Internal copies of
the human-readable summaries and publication receipts live under `results/`.

The archive migration verification receipt proves that the canonical 24 and
seven supplementary benchmarks are a disjoint, complete partition of the
original 31-benchmark archive. See
`results/trace_eval_archive_migration_20260717_verification_receipt.json`.

## Training telemetry

- TRACE 7B W&B run: `llm-reasoning-rl/trace_easyr1/usqbkpd6`.
- TRACE 3B W&B run: `llm-reasoning-rl/trace_easyr1/kijsydl8`.
- Historical reference run: `llm-reasoning-rl/trace_easyr1/jiswyznz`.

All three runs were verified online with configuration, history, output, and
step-500 completion metadata.

The 3B and 7B model cards record the actual answer-focused GRPO contract:
`prompt_answer`, exact JSON answer reward weight `1.0`, JSON-format reward
weight `0.05`, annotation reward `0`, and KL disabled. W&B remains the source
of truth for the full resolved training configurations.

## Completed baseline campaign

The final GPU-host evaluation job,
`trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717`, completed
generation and scoring for Game-RL, Sphinx, and PCGRPO on all 24
`trace_eval_v1` benchmarks and seeds 42, 43, and 44. Generation produced
295,245 row responses, all 216 model/seed/benchmark score identities completed,
and all 648 generation/extraction/score archive slices passed local coverage.
The neutral publication id is
`qwen2.5-vl-7b-rl-baselines-temp06-seeds42-44-v1`.

The completed local results are mean and sample standard deviation across the
three decoding seeds:

| Category | Game-RL | Sphinx | PCGRPO |
| --- | ---: | ---: | ---: |
| Charts & Tables | 54.81 +/- 0.41 | 54.50 +/- 0.87 | 52.91 +/- 0.99 |
| Visual Math | 44.37 +/- 0.32 | 44.70 +/- 0.26 | 44.99 +/- 0.40 |
| Science & General | 51.52 +/- 1.53 | 52.25 +/- 0.88 | 52.28 +/- 0.92 |
| Spatial Reasoning | 54.31 +/- 0.99 | 56.18 +/- 0.97 | 56.03 +/- 0.55 |
| Perception & Counting | 48.54 +/- 0.24 | 50.03 +/- 0.17 | 48.70 +/- 0.22 |
| Puzzles & Logic | 34.72 +/- 0.74 | 38.39 +/- 0.05 | 37.91 +/- 0.79 |
| Overall 24-benchmark macro-average | 48.05 +/- 0.45 | 49.34 +/- 0.15 | 48.80 +/- 0.28 |

Two evaluator-provenance details must accompany these results:

- PCGRPO seed 44, LogicVista row index 135 exhausted the five existing judge
  attempts because each cached extraction was `C.`. The pinned parser accepts
  `C` but rejects the otherwise equivalent terminal-period form. The scoped
  repair removes exactly one terminal period from an otherwise valid
  letter/number label token or set; extra prose, internal punctuation, and
  repeated punctuation remain invalid. The repair reused the unchanged model
  response and all existing judge-cache files, made zero new judge requests,
  and is recorded in the score aggregate's `parser_repair` provenance.
- SpatialVizBench COT retained the pinned evaluator's official fallback to
  `INVALID` after its extraction retries. The fallback counts for seeds
  42/43/44 are Game-RL `1/1/1`, Sphinx `1/2/0`, and PCGRPO `0/1/0`, for totals
  of 3, 3, and 1 rows respectively. These rows were not inferred or repaired
  after the campaign.

The sanitized private HF upload completed at artifact revision
`4ca25af7a4d7daa644e6f35e070dbed1af078321`. The publisher verified all 648
expected slices, 1,304 allowlisted files, content-set SHA-256
`6f19acf3c9abf7949bfe031433bdcbb75d9cc7e6e7178d37e9a517b3c692f38c`,
and a private remote readback. Repository-level documentation was then updated
at `b61d7702d0c95435869597b1050c8140d5b0d1f2` without changing the immutable
artifact revision.

The compact local handoff copies are:

- `results/trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717_results.md`
- `results/trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717_results.xlsx`
- `results/trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717_scores.json`
- `results/trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717_publish_receipt.json`
- `results/trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717_logicvista_repair_receipt.json`

## Public release gates

The internal evaluation tree is the provenance and operations source. A
baseline-specific runtime adapter, processor alias, parser incident, or
recovery fixture belongs in internal documentation and receipts; it must not
be copied into the public repository as a model-specific test or public API
contract. The public evaluation release may include a small generic TRACE
model smoke check, but it must not encode compatibility behavior for Game-RL,
Sphinx, PCGRPO, or another comparison model.

Before publishing the paper-facing `rlvr` branch:

1. Pin and record one immutable public `rlvr` source commit.
2. Preserve the exact answer system-prompt asset at
   `rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt`, whose
   expected SHA-256 is
   `f394927d9abcfb7a1e43ef48a30c29b8c70e6facdbda314d7b27c59d8c3ae900`.
3. Publish a complete source revision, split/version, license, and citation
   matrix for every benchmark in `trace_eval_v1`.
4. Replace paper citation placeholders with the approved dataset, model,
   evaluator, and training references.
5. Bind the released result metadata to the immutable model, judge, suite,
   evaluator-code, prompt, and HF artifact revisions; spreadsheets remain
   derived views rather than the source of truth.

## Resume checklist

1. Clone both GitHub repositories and verify the internal handoff tag.
2. Download the pinned TRACE dataset and merged model revisions above.
3. Follow `evaluation/trace_eval/README.md` to recreate the pinned evaluator
   environment and verify any downloaded model snapshots deeply.
4. Verify the HF evaluation manifests and result metadata before rebuilding
   tables; do not treat XLSX files as the source of truth.
5. Continue public-repository curation on `rlvr` only after agreeing on the
   exact paper-facing file list.

No access tokens, benchmark media, or machine-local paths belong in this
receipt or the public repository.

# Remote Artifact Handoff

This receipt records the durable state required to continue TRACE paper and
release work after the current GPU host is retired. It intentionally records
immutable remote identities rather than machine-local paths.

## Source repositories

- Internal source: `maveryn/trace-internal`, branch `rlvr`. The GPU-host
  handoff point is tagged `gpu-host-handoff-20260717` after the active baseline
  campaign and its publication receipt are complete.
- Public source: `maveryn/trace`, branches `main` and `rlvr`. Local commit
  `4aea3727a39c17f683310297cd1fde6ba8dae26d` contains the validated public CI,
  release constraints, verifier documentation, and release checker. Its push
  requires a GitHub credential with `repo` and `workflow` scopes.
- Public `rlvr` is intentionally not populated during this handoff. Curate the
  paper training and canonical evaluation surface separately on the next
  machine; do not copy the internal evaluation tree wholesale.

## Dataset and models

| Artifact | Immutable remote identity | Notes |
| --- | --- | --- |
| TRACE dataset | `maveryn/trace@e317b746b258630682367cc6a9d87dedd195113c` | Pinned training revision; all 17 local Parquet files were hash-verified against HF. Current repo head at handoff audit: `8f5acc3387daa5ef6a7e577f07948664549dc333`. |
| TRACE 7B | `maveryn/trace-qwen2.5-vl-7b@4d0f1ae8ee25022058090dbdbff61957ece7331d` | Merged inference checkpoint, 16.60 GB; all local safetensor hashes match HF. |
| TRACE 3B | `maveryn/trace-qwen2.5-vl-3b@2ec2374d5c219e6b12e26bda93d3b3adeb1e30c5` | Merged inference checkpoint, 8.15 GB; all local safetensor hashes match HF. |

The full EasyR1/FSDP optimizer checkpoints are deliberately not uploaded. They
are approximately 109 GB for 7B and 51 GB for 3B and are unnecessary for
inference, evaluation, paper release, or reproducing training from the pinned
base model and configuration. Preserve them separately only if exact
post-step-500 optimizer-state continuation becomes a requirement.

## Evaluation artifacts

| Scope | Repository and revision | Coverage |
| --- | --- | --- |
| Canonical 7B comparison | `maveryn/trace-eval-runs@4178a839b689babe16f8ac36f0de7b1b2c5ef36c` | Base, TRACE, and VERO; 24 benchmarks; seeds 42/43/44; 648 response/extraction/score slices. |
| Canonical 3B comparison | `maveryn/trace-eval-runs@4178a839b689babe16f8ac36f0de7b1b2c5ef36c` | Base and TRACE; 24 benchmarks; seeds 42/43/44; 432 slices. |
| Internal supplementary comparison | `maveryn/trace-internal-eval-runs@04267dc31304f1bd5ed41b8930db63b03d3b8d29` | Seven non-paper benchmarks; three 7B models; three seeds; 189 slices. |
| Historical standalone candidates | `maveryn/trace-internal-eval-runs@67bebe1a23d112b20a0c517e863c750714635ca7` | Noncanonical RealWorldQA and VStarBench seed-42 archives under `historical/standalone-candidate-runs/20260716/`. |

The canonical repositories contain neutral machine-readable
`metadata/results/benchmark_scores.json` files in addition to row-level
response, extraction, score, and provenance slices. Internal copies of the
human-readable summaries and publication receipts live under `results/`.

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

## Pending baseline campaign

The final GPU-host job is
`trace_eval_v1_temp06_seed42_43_44_gamerl_sphinx_pcgrpo_20260717`, publishing
as `qwen2.5-vl-7b-rl-baselines-temp06-seeds42-44-v1`. Do not retire the host
until generation, scoring, all 648 archive slices, remote HF readback, and the
publisher completion receipt succeed. Update this section and the internal
handoff tag after completion.

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

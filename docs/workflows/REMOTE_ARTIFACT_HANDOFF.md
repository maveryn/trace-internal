# Remote Artifact Handoff

This receipt records the durable state required to continue TRACE paper and
release work after the current GPU host is retired. It intentionally records
immutable remote identities rather than machine-local paths.

After verifying the remote identities in this receipt, continue with
[`PUBLIC_RELEASE/RELEASE_COMPLETION_CHECKLIST.md`](PUBLIC_RELEASE/RELEASE_COMPLETION_CHECKLIST.md).

## Source repositories

- Internal source: `maveryn/trace-internal`. `main` resolves to
  `28785f91cdf3a4d35f92a790de975adfbf552c68`; the substantive `rlvr` state
  immediately before this final audit is
  `d7c6830c56a028c4570f6f473d28049afffbb7c0`. The earlier GPU handoff remains
  tagged `gpu-host-handoff-20260717`; the audit receipt and final handoff state
  are tagged `machine-retirement-handoff-20260722`.
- Public source: `maveryn/trace`. At the final machine audit, `main` resolves to
  `e89c17cd8993d567f2d47a50141a865064fa5b00`, `dev` to
  `1cd627f05639a7e0f89ae5c4c727c96f49536220`, and `rlvr` to
  `4f64405de90a5bdc52803d4fc2e71c14ec051efc`. All three local worktrees match
  these remote heads.
- Paper-writing skills: `maveryn/ml-codex-skills`, `main` at
  `54876bbffd4c7752d5826cf0e3e40d7ee7d3b89a`.

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
| Fixed external subsets | `maveryn/trace-external-eval-subsets@eb0df9b304356f6fa7ee0293e513ff7a2a0be3cf` | Private manifest-only indices for eight 1,000-row subsets, seed 42; 8,000 selected rows total. No benchmark media are redistributed. The verified 18-file content-set SHA-256 is `fcba5e939c5573f9188c8293be47190e9762eecc0588593ecb14fa5999e8ec46`. |
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

### Experimental annotation artifacts

The preliminary annotation-supervision experiment is not a headline paper
result, but its expensive checkpoints and row-level evaluations are already
preserved for future work:

- 3B checkpoint:
  `maveryn/trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500@68ea66ce6ddcb1c683a58d0992d19f6e61963e4d`
  (8.15 GB).
- 7B checkpoint:
  `maveryn/trace-qwen25vl7b-rlvr-ann-additive-0p50-sectioned-step500@f5ecbe0f8564548f201a6e4e2719225f1c8947e2`
  (16.60 GB).
- Evaluation archive:
  `maveryn/trace-internal-eval-runs@fa8ce278bfd1a99bb31b1b16431a36e3fd3942fa`.
  It contains generation, extraction, and score slices for all 24 benchmarks at
  seed 42 for both annotation checkpoints: 144 files per model and 288 files in
  total.

These runs are exploratory and should not be combined with the canonical
three-seed answer-focused comparison without an explicit protocol distinction.

## Task calibration artifacts

The final task-level calibration ledger is archived privately at
`maveryn/trace-internal-calibration@7c439def86a89722a6757ce2b37362c9a52f4d81`.
It covers all 1,000 active tasks with zero pending tasks: 955 pass the final
numerical gates directly and 45 have an explicit human acceptance record. The
archive also contains 225 available referenced solve-rate workbooks; its
manifest records the nine optional referenced workbooks that were unavailable
at archival time.

This is a mixed calibration ledger, not a uniform model benchmark. It combines
757 records from the original 20-question by 8-rollout Qwen2.5-VL-3B prompt
pilot with 243 records from later 50-question by 8-rollout calibration or
explicit resolution records, principally using Qwen2.5-VL-7B. The verified
content-set SHA-256 is
`6db157d83fe1377178ed8b0508e837b1cf2f4a5c4d36c73d6b2c3955e511cb0a`.
See `results/trace_task_calibration_v0_20260722_publish_receipt.json` for the
complete publication and remote-verification receipt.

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

The final local/remote inventory and explicit disposal decisions are recorded
in `results/trace_machine_retirement_audit_20260722.json`. Large local review
artifacts, copied benchmark media, caches, old package builds, and preliminary
runs are intentionally excluded from the handoff.

No access tokens, benchmark media, or machine-local paths belong in this
receipt or the public repository.

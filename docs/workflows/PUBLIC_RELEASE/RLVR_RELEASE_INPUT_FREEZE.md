# RLVR Release Input Freeze

This freeze answers a narrow release question: preserve the exact source of
the paper's 3B/7B answer-only training and the shared 24-benchmark evaluation
workflow without publishing the internal experiment history around it.

## Release truth

The authoritative inputs are:

- the reviewed, per-file internal-to-public map
  [`rlvr_public_file_manifest.v1.json`](rlvr_public_file_manifest.v1.json);
- the sanitized resolved run configurations
  [`rlvr_training_configs.v1.json`](rlvr_training_configs.v1.json) and training
  environments
  [`rlvr_training_environments.v1.json`](rlvr_training_environments.v1.json);
- the canonical suite
  [`evaluation/trace_eval/suite.v1.json`](../../../evaluation/trace_eval/suite.v1.json);
- the reviewed 24-benchmark provenance matrix
  [`evaluation/trace_eval/benchmark_provenance.v1.json`](../../../evaluation/trace_eval/benchmark_provenance.v1.json);
- the generated eight-model result source
  [`results/canonical/trace_eval_v1/release/results.json`](../../../results/canonical/trace_eval_v1/release/results.json);
- the fail-closed validator
  [`scripts/validate_rlvr_release_inputs.py`](../../../scripts/validate_rlvr_release_inputs.py).

Generated release metadata and the sanitized training receipts are frozen at
internal source revision `c28b706d7be5da62ee453375c9f559e99752e843`.
Every source-map entry uses a full Git commit and a SHA-256; no entry may read
its source identity from mutable working-tree content. The reviewed map itself
is identified by the commit or release tag that contains it.

The file map is default-deny. `approved_exact_copy` means the recorded bytes
may move after their SHA-256 is checked. `approved_for_public_adaptation` means
the internal file is an approved source only: it must be narrowed to
`trace_eval_v1`, renamed where necessary, stripped of private paths and
recovery machinery, adapted to `trace_tasks`, and reviewed again in the public
tree.

## Training source decision

The final W&B run records resolve to two internal source commits:

| Scale | W&B run | Internal source commit | Merged release model |
| --- | --- | --- | --- |
| 3B | `kijsydl8` | `847e9f5279f8111fdbfef1c8b8631fc621c23456` | `maveryn/trace-qwen2.5-vl-3b@2ec2374d5c219e6b12e26bda93d3b3adeb1e30c5` |
| 7B | `usqbkpd6` | `d29b23f6085764ea831adb5edc5a23f89b0d98f3` | `maveryn/trace-qwen2.5-vl-7b@4d0f1ae8ee25022058090dbdbff61957ece7331d` |

The release map stores a SHA-256 for every selected training file at both run
source commits. Across the selected shared runtime, only
`examples/reward_function/trace_rlvr.py` and `verl/trainer/config.py` differ;
the reviewed source diff only changes user-facing capitalization from `Trace`
to `TRACE`. The 3B source commit is therefore the public source baseline while
both exact run-source receipts remain recorded.

The W&B receipts are authoritative for the resolved run settings, rather than
the generic wrapper defaults. Both final reruns used `save_limit=1`,
`find_last_checkpoint=false`, `load_checkpoint_path=null`, and selected
`global_step_500`. In particular, the final 7B run did **not** use the older
wrapper's two-checkpoint/resume defaults. The receipts preserve the raw W&B
config, requirements, and metadata hashes while removing host, identity,
network, GPU-UUID, credential, and machine-path fields.

The public training entrypoint surface is exactly:

- `rlvr/configs/trace-qwen2.5-vl-3b.yaml`;
- `rlvr/configs/trace-qwen2.5-vl-7b.yaml`;
- `rlvr/train.py`, exposing `check`, `prepare`, `run`, `smoke`, and `merge`.

The curated dependency unit retains the reviewed 64-file `verl` tree from the
3B source revision, the EasyR1 Apache license, the answer prompt, the reward
adapter, and the local checkpoint merger. It records clean upstream EasyR1
revision `dd71bbd252694f5f850213eec15795b6b88d9fea`. The reward adapter, merger,
and `verl/trainer/{config,data_loader,metrics}.py` plus
`verl/utils/dataset.py` require public adaptation. The merger must lose all
upload behavior; the other adaptations remove internal imports and
annotation/task-conditioned configuration while preserving answer-only run
semantics.

Generic EasyR1 example configuration and packaging, unpinned backend
requirements, internal reward tests, and the four operational shell launchers
are not publication sources. Annotation training, task-conditioned routing,
resume workflows, historical campaign machinery, and automatic Hugging Face
publication remain outside this release. Existing public task-environment
annotation fields and verifier APIs are unaffected by this training boundary.

## Evaluation source decision

One model-agnostic `trace_eval_v1` workflow evaluates all eight model
descriptors. Baseline-specific recovery launchers and processor aliases are
not release APIs. The public adaptation must expose only:

1. pinned environment and dataset/model preparation;
2. resumable generation;
3. shared extraction and scoring;
4. status and exact-coverage verification;
5. multi-seed summary generation;
6. sanitized, non-blocking result publication.

Historical `final25` and `final26` filenames in the internal implementation
are mapped to neutral public destinations and must be renamed as part of the
adaptation. Provisional suite choices, ScreenSpot imports, private archive
migration, parser-repair receipts, and baseline compatibility fixtures are
explicitly denylisted.

## Historical manifest decision

Do not copy or publish
`rlvr/experiments/final_answer_only_manifest.json`. It is retained internally
as experiment history only. It neither selects the canonical training runs
nor supplies any value in the canonical release result source. The file is
both absent from the allowlist and named explicitly in the denylist.

## Verification

Run these checks after any change to a frozen input:

```bash
python scripts/build_rlvr_public_file_manifest.py --check
python scripts/validate_rlvr_release_inputs.py
python -m pytest -q tests/test_rlvr_release_inputs.py
```

The result builder additionally supports `--check` when the three immutable
source bundles are available locally. No training or model inference is
required for these validations.

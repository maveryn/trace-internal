# TRACE Build and Validation

Operational policy for build lifecycle and pre-finalize validation.

## 1) Build lifecycle
1. Build to staging directory.
2. Generate train instances + sidecar traces.
3. Run pre-finalize validation.
4. Optional strict-repro second pass and compare.
5. Write reports.
6. Atomic finalize on success; failure bundle on error.

## 2) Mandatory trace contract
1. Sidecar trace export is required.
2. Every `TrainInstance` must include `trace_ref`.
3. Trace write failures are hard build failures.

## 3) Required pre-finalize checks
1. Train-instance schema validity.
2. `trace_ref` existence/hash/index integrity.
3. Image path/hash integrity.
4. Task count expectations.
5. Single `instance_version` consistency.
6. Prompt metadata/bundle/key validity.
7. Required slot conformance and unresolved placeholder checks.
8. Prompt variant-count/index consistency.

## 4) Distribution review policy
For new or distribution-changing task logic:
1. Generate per-query samples (`--count-per-query 100` recommended).
2. Review `distribution_report.json`.
3. Fix obvious skew before merge/finalize.

## 5) Reports and failure artifacts
Always emit in staging:
1. `validation_report.json`
2. `build_report.json`

On failure, keep:
1. staging directory (for debugging),
2. failure bundle under `failed_builds/<dataset_id>/`.

## 6) CI strict-repro profile
Run CI with a pinned strict-repro config and fail on:
1. record mismatches,
2. trace mismatches,
3. image-byte/hash mismatches,
4. missing pinned tasks or attempt-limit exhaustion.

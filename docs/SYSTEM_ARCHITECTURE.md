# TRACE System Architecture

## Purpose
This document defines how TRACE is structured in code and how data flows through the system.
It is the implementation-facing architecture reference, while `docs/DSL_BLUEPRINT.md` remains the normative contract/ABI document.

## Architectural principles
1. Deterministic generation from explicit config, versions, and seeds.
2. Task logic produces both final answer and evidence from one execution trace.
3. Training-facing records stay lightweight; heavy replay/debug payloads live in sidecar traces.
4. Reuse shared infrastructure first; avoid per-task reinvention.

## Code layout (current)
1. `trace/core/`
- Shared infrastructure: ABI types, canonical JSON, hashing, seed derivation, identity, type registry, trace store, validation, builder.
2. `trace/tasks/`
- Task registry/framework plus task packages organized as `trace/tasks/<domain>/<task_group>/...`.
- Domain-shared helpers live under `trace/tasks/<domain>/shared/`.
3. `trace/core/visual/`
- Shared visual-variation helpers (deterministic background styles + post-image noise).
4. `trace/core/prompts/`
- Shared prompt bundle loading, deterministic variant selection, and strict template rendering.
5. `prompts/`
- External prompt bundle assets grouped by domain/task_group.
6. `trace/configs/`
- Internal registry/config assets (for example type registry).
7. `configs/`
- Build/runtime configs (for example CI strict-repro profile, task-group defaults in `configs/task_groups/<domain>/<task_group>.yaml`).
8. `scripts/`
- Operational CLIs (build, cleanup, etc.).
9. `tests/`
- Determinism, schema, validation, and end-to-end build checks.

## Runtime build pipeline
1. Load build config and type registry.
2. Resolve deterministic `dataset_id` from canonical config payload.
3. Create temp staging output.
4. Sample tasks by task-level policy.
5. For each accepted instance:
- generate prompt/answer/evidence/image from task,
- resolve prompt templates from external bundle assets,
- apply deterministic visual variations (for example post-image noise),
- write image artifact,
- write sidecar trace record,
- emit `TrainInstance` with `trace_ref`.
6. If strict reproducibility is enabled, run an additional staging pass and compare:
- ordered canonical `TrainInstance` records,
- decompressed sidecar trace content,
- image bytes/hashes.
7. Run pre-finalize validation.
8. Emit `validation_report.json` and `build_report.json`.
9. On success: atomic finalize from staging to final dataset path.
10. On failure: keep staging for debugging and persist failure bundle.

## Component responsibilities
1. `trace/core/types.py`
- ABI dataclasses (`TrainInstance`, `TraceInstance`, `TraceRef`, typed answer/evidence envelopes).
2. `trace/core/canonical.py`
- Shared canonical serializer for identity/hash inputs and canonicalization policy enforcement.
3. `trace/core/hash_utils.py`
- `blake3` hashing helpers for bytes/files.
4. `trace/core/seed.py`
- Namespace-based deterministic seed derivation.
5. `trace/core/identity.py`
- Deterministic `instance_id` computation from training-facing canonical payload.
6. `trace/core/type_registry.py`
- Global answer/evidence type registry load and checks.
7. `trace/core/trace_store.py`
- Sidecar trace shard append/read utilities.
8. `trace/core/validation.py`
- Pre-finalize validation (including prompt metadata/bundle/key/placeholder checks) and structured validation report generation.
9. `trace/core/builder.py`
- End-to-end dataset build orchestration.
10. `trace/core/strict_repro.py`
- strict reproducibility comparisons for train records, traces, and images.
11. `trace/tasks/*`
- Domain/task-specific scene generation, query execution, evidence projection, and task trace payloads.
12. `trace/tasks/<domain>/<task_group>/*`
- Canonical placement for concrete task modules (for example `trace/tasks/geometry/measurement/angle_value_query.py`).
13. `trace/core/prompts/*`
- Prompt bundle parsing/cache, deterministic variant selection, placeholder validation, and composition helpers.
14. `trace/core/visual/noise.py`
- Task-group-aware deterministic post-image noise sampling/application and metadata emission.
15. `trace/core/visual/background.py`
- Task-group-aware deterministic background-style sampling/rendering and metadata emission.
16. `trace/core/task_group_config.py`
- Cached loader for domain/task-group defaults from `configs/task_groups/<domain>/<task_group>.yaml`.

## Sampling architecture
1. Global sampling unit is `task`.
2. Domain/task-group probabilities are derived from task probabilities.
3. Tasks may define internal `query_type` sampling.
4. `P(sample=t,q) = P_task(t) * P_query(q|t)`.
5. `task_group` should stay broad (shared reasoning style); query variants stay inside task-level `query_type`.
6. For geometry value-style tasks, use `task_group = measurement` by default.

## Extension points
1. Add a new task under `trace/tasks/` and register it.
2. Add shared utilities under `trace/core/` or domain-shared modules before adding task-local copies.
3. Add new answer/evidence types by updating type registry and validators.
4. Add new build checks in `trace/core/validation.py` with cataloged error codes.

## Invariants
1. Every emitted `TrainInstance` must include `trace_ref`.
2. Every instance must have exactly one valid final answer by construction.
3. No auto-relaxation of semantic constraints during generation.
4. Image paths are dataset-root-relative and image hashes are required.
5. Identity hashes must use shared canonicalization + `blake3`.

## Documentation maintenance rule
Update this file whenever architecture-level behavior changes, including:
1. major module boundary changes,
2. data-flow changes in build/finalize/failure handling,
3. changes to shared invariants or extension points.

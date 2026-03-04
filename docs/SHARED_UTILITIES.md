# TRACE Shared Utilities

## Purpose
This document lists reusable infrastructure and helper modules.
Use it to prevent duplicate implementations across tasks/domains.

## Reuse policy
1. Before adding logic, check if an existing shared utility already covers it.
2. If needed behavior is generic, add it once to a shared module and reuse it.
3. Task-local helper code is allowed only when task-specific by definition.
4. If you add or change shared helpers, update this document in the same change.

## Global shared utilities (`trace/core`)
1. `trace/core/types.py`
- ABI dataclasses and typed envelope structures.
- Use for `TrainInstance`, `TraceInstance`, `TraceRef`, and complexity records.
2. `trace/core/canonical.py`
- Canonical JSON serialization and canonicalization error handling.
- Use for all identity/hash serialization paths.
3. `trace/core/hash_utils.py`
- `blake3` helpers for raw bytes and file content.
4. `trace/core/seed.py`
- Namespace-based deterministic seed derivation and RNG spawning.
5. `trace/core/identity.py`
- Deterministic `instance_id` construction from training-facing fields.
6. `trace/core/type_registry.py`
- Versioned answer/evidence type registry loading and checks.
7. `trace/core/trace_store.py`
- Sidecar trace shard writing/reading (`.jsonl.zst`).
8. `trace/core/validation.py`
- Schema/trace/image/count/version/identity validation and report generation.
9. `trace/core/error_codes.py`
- Machine-readable validation/build error codes.
10. `trace/core/config.py`
- Build config parsing and typed config models.
11. `trace/core/builder.py`
- Shared dataset build lifecycle orchestration.
12. `trace/core/strict_repro.py`
- Strict reproducibility comparisons across staging outputs (train records, traces, images).
13. `trace/core/task_group_config.py`
- Cached loader for domain/task-group defaults from per-group files under `configs/task_groups/<domain>/<task_group>.yaml`.
14. `trace/core/visual/noise.py`
- Deterministic post-image noise application with caller-supplied defaults and per-task overrides.
- Task families should define defaults in their own modules and pass them into the shared applier.
15. `trace/core/prompts/*`
- Shared prompt bundle loading, deterministic variant sampling, schema checks, and strict placeholder rendering.
16. `prompts/*`
- External prompt bundle assets organized by domain/task_group.

## Task framework shared modules (`trace/tasks`)
1. `trace/tasks/registry.py`
- Shared task registration and lookup.
2. `trace/tasks/base.py`
- Shared task protocol and `TaskOutput` container.
3. `trace/tasks/geometry/shared/value_queries.py`
- Domain-shared value-query operators for candidate sets (`min`, `max`, `median`, `closest_to_x`, threshold variants, and `difference_max_min`).
- Reuse for geometry/chart tasks that share answer-from-candidate-value semantics.
4. `trace/tasks/shared/value_queries.py`
- Backward-compatible shim that re-exports geometry shared value-query operators while imports migrate.

## Domain/task-group shared utility guidance
1. If 2+ tasks in one domain/task_group need the same logic, create a domain-shared module under:
- `trace/tasks/<domain>/shared/` or
- `trace/tasks/shared/` for cross-domain reuse.
2. Place concrete task modules under `trace/tasks/<domain>/<task_group>/` so related tasks stay co-located.
3. Typical candidates:
- geometry primitives and constraints,
- chart candidate extraction,
- evidence anchor projection,
- common prompt slot/render helpers.
4. Keep module APIs deterministic and seed-driven.
5. Prompt text assets live outside task modules under `prompts/`; task code should call shared prompt helpers.

## What should not be duplicated
1. Canonical serialization and hashing logic.
2. Seed derivation policy.
3. Type registry checks.
4. Trace shard I/O contract.
5. Validation report and error-code plumbing.
6. Task registration mechanics.

## Review checklist for reuse
1. Did we search this file and existing modules before adding new code?
2. Is new helper task-specific or reusable?
3. If reusable, is it in a shared module with docstring and tests?
4. Did we update this file and `AGENTS.md` references if shared surfaces changed?

## Documentation maintenance rule
Update this file whenever:
1. a new shared module/function is introduced,
2. a shared module API changes,
3. a duplicate pattern is consolidated into shared infrastructure.

# TRACE Task Authoring Guide

## Purpose
This is the canonical guide for creating new tasks in TRACE.
Use this file as the task-level implementation playbook on top of `docs/DSL_BLUEPRINT.md`.

Platform build lifecycle, pre-finalize validation, failure handling, cleanup, and CI strict-repro
rules live in `docs/BUILD_VALIDATION.md`.

## Authoring flow (required)
1. Define the task in spec terms first:
- `SceneSpec`
- `QuerySpec`
- `RenderSpec`
- `PromptSpec`
- `VerifierSpec`
- optional `SamplerSpec` and `choice_spec`
2. Assign task taxonomy explicitly: `domain`, `task_group`, `task`.
3. Confirm required domain capabilities (`relations`, `ops`) before implementation.
4. Define evidence forms the task supports and the default evidence type for dataset builds.
5. Ensure evidence resolution uses config precedence `domain -> task_group -> task` (no per-instance override).
6. Reuse an existing `TemplateBundle` when possible; add a new bundle only if necessary.
7. Implement deterministic scene/query/render execution with explicit seeds and no hidden RNG.
8. Emit canonical instance output per `InstanceRecordSpec`.
9. Ensure `answer_gt`, `evidence_gt`, and `execution_trace` come from the same query execution.
10. Emit typed envelopes in `answer_gt` and `evidence_gt` as `{type, value}`.
11. Use only registered global type IDs for `answer_gt.type` and `evidence_gt.type`; namespace task-specific extensions.
12. Enforce unique-answer-by-construction in generation logic for the task; if ambiguity appears, reject/resample or redesign.
13. Use bounded resampling (`max_attempts`) and reject/replace candidates when exhausted; never auto-relax task constraints.
14. Emit `task_complexity.complexity_score` (shared key) and task-defined `complexity_components`.
15. Use sidecar trace payload export and require `trace_ref` on every emitted `TrainInstance`.
16. Ensure `instance_id` is deterministic from canonical training-facing fields.
17. Use shared canonical JSON serializer utility for all identity hashes; no task-level canonicalization overrides.
18. Treat canonicalization failures as hard errors (unsupported types, non-string keys, non-finite numbers).
19. Use PNG as default image output format unless explicitly overridden by build config.
20. Update docs (`DSL_BLUEPRINT.md`, this file, and `LESSONS_LEARNED.md`) when reusable guidance changes.

## Definition of done
A task is done only when:
1. Typed IR program validates.
2. Capability requirements are explicit and satisfied.
3. Determinism checks pass for fixed seeds.
4. Verifier checks pass for answer/evidence/consistency.
5. Generation enforces one unique final answer.
6. Constraint-hardness is preserved (no auto-relaxation).
7. `TrainInstance` includes typed `answer_gt` and `evidence_gt`.
8. `task_complexity.complexity_score` and `complexity_components` are emitted.
9. No duplicate contract fields are emitted (`answer_space` absent, no per-instance `schema_version`).
10. All emitted instances in a dataset share the same `instance_version`.
11. `images[*].path` is dataset-root-relative and `images[*].image_hash` is present (`blake3`).

## Task-level testing checklist
1. Schema validity test for emitted instance records.
2. Answer correctness test (GT + negative cases).
3. Evidence correctness test (valid + invalid evidence forms).
4. Consistency checker test.
5. Determinism/replay test across repeated runs.
6. Ambiguity-rejection test (generator resamples/rejects non-unique-answer instances).
7. Constraint-hardness test (generator does not auto-relax constraints under failure pressure).
8. Evidence format test: resolver chooses correct build-time format from `domain -> task_group -> task` precedence.
9. Validation test: unsupported requested evidence format returns hard error.
10. Trace reference integrity test: `trace_ref` resolves to a record and hash check passes.
11. Deterministic-ID test: repeated generation with same config/seed yields same `instance_id`.
12. Hash-policy test: `trace_ref.trace_record_hash` uses `blake3`.
13. Envelope-schema test: `answer_gt` and `evidence_gt` always have `{type,value}` and types align with verifier/task schema.
14. Type-registry test: `answer_gt.type` and `evidence_gt.type` exist in the versioned global registry (or valid namespaced extension).
15. Path-invariance test: changing only image file paths does not change `instance_id` if image content hash is unchanged.
16. Canonical-json test: emitted JSON files use canonical key ordering.
17. Non-finite-number test: serialized outputs reject `NaN`/`Inf`/`-Inf`.
18. Canonical-error-code test: serializer failures return cataloged `schema_*` codes.
19. Multi-image contract test: task prompt/render contract defines panel semantics without global image-role metadata.
20. Choice/distractor semantic-distinctness tests (if applicable).

## Sampling and quality checklist
1. Validate required metadata presence (`instance_id`, `instance_seed`, taxonomy fields, versions, answer/evidence fields).
2. Report target metric distributions.
3. Report answer-shape distributions.
4. For choice tasks, verify distractor uniqueness and semantic distinctness.
5. Verify trace shard manifest and `trace_ref` consistency.
6. Flag suspicious skews and resample/fix before finalizing.

## Cross-task tips (living)
Use this section for practical rules that apply to many tasks.

1. Never rely on unordered iteration of sets/maps when emitting canonical outputs.
2. Keep witness space symbolic; project to pixel evidence only through render-map anchors.
3. If multiple evidence surface forms are supported, choose one primary prompt form and keep alternates explicit.
4. Fail fast on IR type/capability mismatches; do not silently degrade behavior.
5. For path tasks, enforce unique shortest-path answer in generation (or redesign task constraints).
6. If max attempts are exhausted, reject and replace the sample; never weaken semantic constraints.
7. Keep full replay metadata in trace payload; keep training-facing records lightweight.
8. Evidence/witness ordering semantics are task-defined (no global rule); each task must document whether order matters and keep emission deterministic.

## Maintenance rule
Whenever you discover guidance that applies to more than one task:
1. Add/update the relevant bullet in `Cross-task tips (living)` here.
2. Add a matching entry in `docs/LESSONS_LEARNED.md` if it came from a bug, regression, or review finding.

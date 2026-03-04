# TRACE Task Authoring Guide

## Purpose
This is the canonical guide for creating new tasks in TRACE.
Use this file as the task-level implementation playbook on top of `docs/DSL_BLUEPRINT.md`.
Use `docs/SYSTEM_ARCHITECTURE.md` for module/lifecycle context and `docs/SHARED_UTILITIES.md` before adding new helpers.
Use `docs/PROMPT_SYSTEM.md` for prompt-template architecture and external prompt-bundle rules.
Use `docs/CODE_DOCUMENTATION.md` for code-level docstring/comment standards.

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
3. Choose `task_group` by shared reasoning style; do not split groups by every query variant.
4. For geometry value-style tasks, default `task_group` to `measurement` and express variant logic through `query_type`.
5. Use isolated task groups only when the task does not cleanly fit existing group semantics.
6. Confirm required domain capabilities (`relations`, `ops`) before implementation.
7. Define evidence forms the task supports and the default evidence type for dataset builds.
8. Ensure evidence resolution uses config precedence `domain -> task_group -> task` (no per-instance override).
9. Check `docs/SHARED_UTILITIES.md` and reuse existing shared helpers before creating new task-local utilities.
10. Reuse an existing `TemplateBundle` when possible; add a new bundle only if necessary.
11. Define prompt assets in external bundles under `prompts/` (no hardcoded prompt literals in task modules).
12. Use layered prompt composition:
- one task-type template layer (10+ variants),
- one query-type template layer (10+ variants per query type).
13. Use deterministic prompt variant sampling with explicit prompt seed namespaces.
14. Emit prompt-variant provenance metadata in trace payload (`bundle/key/index/count` fields).
15. Define visual-variation policy at task-group level (domain/task_group), with task-level overrides only when needed.
16. Store shared task-group defaults (generation/rendering/visual variation) in per-group files under `configs/task_groups/<domain>/<task_group>.yaml`.
17. For post-image noise, load task-group defaults via group modules and call shared deterministic noise helpers; keep evidence coordinates valid (no geometric warps).
18. Record selected visual variation metadata in trace payload (for example `render_spec.post_image_noise`).
19. Implement deterministic scene/query/render execution with explicit seeds and no hidden RNG.
20. Emit canonical instance output per `InstanceRecordSpec`.
21. Ensure `answer_gt`, `evidence_gt`, and `execution_trace` come from the same query execution.
22. Emit typed envelopes in `answer_gt` and `evidence_gt` as `{type, value}`.
23. Use only registered global type IDs for `answer_gt.type` and `evidence_gt.type`; namespace task-specific extensions.
24. Enforce unique-answer-by-construction in generation logic for the task; if ambiguity appears, reject/resample or redesign.
25. Use bounded resampling (`max_attempts`) and reject/replace candidates when exhausted; never auto-relax task constraints.
26. Emit `task_complexity.complexity_score` (shared key) and task-defined `complexity_components`.
27. Use sidecar trace payload export and require `trace_ref` on every emitted `TrainInstance`.
28. Ensure `instance_id` is deterministic from canonical training-facing fields.
29. Use shared canonical JSON serializer utility for all identity hashes; no task-level canonicalization overrides.
30. Treat canonicalization failures as hard errors (unsupported types, non-string keys, non-finite numbers).
31. Use PNG as default image output format unless explicitly overridden by build config.
32. Update docs (`DSL_BLUEPRINT.md`, `PROMPT_SYSTEM.md`, `SYSTEM_ARCHITECTURE.md`, `CODE_DOCUMENTATION.md`, `SHARED_UTILITIES.md`, this file, and `LESSONS_LEARNED.md`) when reusable guidance changes.

## Task and query sampling policy (required)
1. Global sampling is task-level only: `task` is the primary sampling unit.
2. Domain/task-group probabilities are derived by aggregating task-level probabilities.
3. For tasks with multiple question variants, define explicit `query_type` values in task contract/query spec.
4. Default query-type sampling inside a task is uniform unless task config overrides weights.
5. Query-type multiplicity must not change global task probability; it only affects `P(query_type | task)`.
6. Record selected `query_type` in trace/query metadata for every instance.

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
12. Prompt is rendered from external templates with deterministic variant metadata captured in trace payload.

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
21. Query-sampling test for multi-query tasks: default query-type distribution is uniform unless explicit task-level weights are configured.
22. Prompt bundle resolution test: bundle exists and required keys are present.
23. Prompt variant-count test: task-type and query-type template lists satisfy minimum cardinality (10+ each).
24. Prompt placeholder test: all required placeholders are resolved and no unresolved placeholders remain in rendered prompts.
25. Prompt determinism test: same seed/spec yields identical rendered prompt and variant indices.
26. Visual-noise determinism test: same seed/spec yields identical post-noise image and edit metadata.
27. Visual-noise safety test: enabled noise modes do not invalidate evidence coordinate semantics.

## Sampling and quality checklist
1. Validate required metadata presence (`instance_id`, `instance_seed`, taxonomy fields, versions, answer/evidence fields).
2. Report target metric distributions.
3. Report answer-shape distributions.
4. For choice tasks, verify distractor uniqueness and semantic distinctness.
5. Verify trace shard manifest and `trace_ref` consistency.
6. Flag suspicious skews and resample/fix before finalizing.
7. For tasks with multiple query types, report per-task query-type accepted counts/distribution.

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
9. Keep prompt text in external assets; task modules should assemble prompts via shared prompt renderer only.

## Task documentation requirement
Every new task must add `docs/tasks/<task_id>.md` using `docs/tasks/TASK_DOC_TEMPLATE.md`.
Required fields include:
1. prompt bundle id,
2. task-type key,
3. query-type template mapping,
4. placeholder slot schema,
5. prompt examples and variant counts.

## Maintenance rule
Whenever you discover guidance that applies to more than one task:
1. Add/update the relevant bullet in `Cross-task tips (living)` here.
2. Add a matching entry in `docs/LESSONS_LEARNED.md` if it came from a bug, regression, or review finding.

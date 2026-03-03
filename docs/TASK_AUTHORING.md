# TRACE Task Authoring Guide

## Purpose
This is the canonical guide for creating new tasks in TRACE.
Use this file as the practical implementation playbook on top of `docs/DSL_BLUEPRINT.md`.

## Authoring flow (required)
1. Define the task in spec terms first:
- `SceneSpec`
- `QuerySpec`
- `RenderSpec`
- `PromptSpec`
- `VerifierSpec`
- optional `SamplerSpec` and `choice_spec`
2. Confirm required domain capabilities (`relations`, `ops`) before implementation.
3. Reuse an existing `TemplateBundle` when possible; add a new bundle only if necessary.
4. Implement deterministic scene/query/render execution with explicit seeds and no hidden RNG.
5. Emit canonical instance output per `InstanceRecordSpec`.
6. Ensure `answer_gt`, `evidence_gt`, and `execution_trace` come from the same query execution.
7. Implement/attach consistency checking (`reward_consistency`) for the task family.
8. Add schema + verifier + determinism tests.
9. Generate representative samples and validate distributions.
10. Update docs (`DSL_BLUEPRINT.md`, this file, and `LESSONS_LEARNED.md`) when reusable guidance changes.

## Definition of done
A task is done only when:
1. Typed IR program validates.
2. Capability requirements are explicit and satisfied.
3. Determinism checks pass for fixed seeds.
4. Verifier checks pass for answer/evidence/consistency.
5. Canonicalization policy is explicit for multi-solution cases.
6. Coordinate conventions and tolerances are explicit in prompt/verifier contracts.
7. In-code docs are updated (docstrings/comments for invariants and non-obvious logic).
8. Samples are generated and checked for schema + distribution quality.

## Testing checklist
1. Schema validity test for emitted instance records.
2. Answer correctness test (GT + negative cases).
3. Evidence correctness test (valid + invalid evidence forms).
4. Consistency checker test.
5. Determinism/replay test across repeated runs.
6. Multi-solution canonicalization test (if applicable).
7. Choice/distractor semantic-distinctness tests (if applicable).

## Sampling and quality checklist
1. Validate required metadata presence (`scene_ir`, `query_spec`, `render_map`, `execution_trace`, versions/seeds).
2. Report target metric distributions.
3. Report answer-shape distributions.
4. For choice tasks, verify distractor uniqueness and semantic distinctness.
5. Flag suspicious skews and resample/fix before finalizing.

## Cross-task tips (living)
Use this section for practical rules that apply to many tasks.

1. Never rely on unordered iteration of sets/maps when emitting canonical outputs.
2. Keep witness space symbolic; project to pixel evidence only through render-map anchors.
3. If multiple evidence surface forms are supported, choose one primary prompt form and keep alternates explicit.
4. Fail fast on IR type/capability mismatches; do not silently degrade behavior.
5. For path tasks, always log canonicalization policy and store canonical witness.

## Maintenance rule
Whenever you discover guidance that applies to more than one task:
1. Add/update the relevant bullet in `Cross-task tips (living)` here.
2. Add a matching entry in `docs/LESSONS_LEARNED.md` if it came from a bug, regression, or review finding.

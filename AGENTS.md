# TRACE AGENTS

## Project goal
TRACE is a grounded visual reasoning task environment for RLVR.
Each generated instance should include:
- prompt
- typed answer
- image(s)
- metadata-grounded verifier payload

Canonical architecture and contracts live in `docs/DSL_BLUEPRINT.md`.
Canonical versioned requirements live in `REQUIREMENTS.md`.

## Scope and boundaries
- Work in this repository unless the user explicitly asks otherwise.
- Treat `docs/DSL_BLUEPRINT.md` as the source of truth for architecture decisions.
- Treat `REQUIREMENTS.md` as the source of truth for project requirements and requirement versioning.
- Prefer additive, reusable infrastructure over one-off task code.

## Core engineering rules
- Keep generation factorized into explicit specs:
  - `SceneSpec`
  - `QuerySpec`
  - `RenderSpec`
  - `PromptSpec`
  - `VerifierSpec`
  - `SamplerSpec`
  - `InstanceRecordSpec`
- Generators must be deterministic given seeds/specs/versions.
- No hidden randomness: all random sources must be explicit and recorded.
- Verifiers must rely on metadata contracts and projections, not pixel heuristics as source of truth.
- Query programs must be typed IR with named intermediate outputs.
- Answers and evidence must be derived from the same query execution trace.
- Multi-solution tasks must use explicit canonicalization and record the policy.
- Domain requirements must be capability-driven (relations/ops declared explicitly).

## Reuse and code organization
- Before adding new logic, search for reusable helpers and extend shared modules when possible.
- Do not duplicate utilities across tasks/domains unless there is a strong reason.
- If a helper is missing, add it once in a shared place and reuse it.

## Output and metadata requirements
- Every task must emit one canonical instance record shape (per `InstanceRecordSpec`).
- Payload should include, at minimum:
  - scene IR
  - query spec
  - render spec
  - render map
  - execution trace
  - canonicalization metadata
  - seeds and version bundle
- Include structural descriptors for curriculum analysis.
- Use globally consistent coordinate conventions and tolerance policies.

## Testing and validation
- Add tests for:
  - schema/contract validity
  - answer/evidence/verifier consistency
  - determinism/replay stability
- Maintain a determinism harness for fixed seed suites.
- For generated samples, verify:
  - answer type and verifier alignment
  - evidence contract alignment
  - required metadata presence
- Report distribution summaries for generated datasets (target metric, answer shape, key sampling axes).

## Documentation discipline
- Update docs when behavior/contracts change.
- Keep `docs/DSL_BLUEPRINT.md` aligned with implementation decisions.
- Keep `REQUIREMENTS.md` updated whenever requirements are added/changed/removed.
- Every requirement change must include an explicit `requirements_version` bump and `Change Log` entry in `REQUIREMENTS.md`.
- Document new reusable helpers and new verifier edge cases when discovered.

## Workflow guidelines
- After any code edit, ask whether to commit before creating a commit.
- Avoid destructive git/file operations unless explicitly requested.
- Prefer clear, versioned contracts over implicit behavior.

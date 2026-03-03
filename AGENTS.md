# TRACE AGENTS

## Project goal
TRACE is a grounded visual reasoning task environment for RLVR.
Each generated instance should include:
- prompt
- typed answer
- image(s)
- metadata-grounded verifier payload

Canonical architecture and contracts live in `docs/DSL_BLUEPRINT.md`.
Python package dependencies live in `requirements.txt`.
Task creation instructions live in `docs/TASK_AUTHORING.md`.
Lessons/pitfalls log lives in `docs/LESSONS_LEARNED.md`.

## Scope and boundaries
- Work in this repository unless the user explicitly asks otherwise.
- Treat `docs/DSL_BLUEPRINT.md` as the source of truth for architecture decisions.
- Treat `requirements.txt` as the source of truth for Python dependency installation.
- Treat `docs/TASK_AUTHORING.md` as the source of truth for task authoring procedure.
- Treat `docs/LESSONS_LEARNED.md` as the source of truth for cross-task pitfalls and reusable fixes.
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

## Code documentation standards
- Add concise docstrings for new modules, classes, and non-trivial functions.
- Document assumptions, invariants, and tie-breaking/canonicalization rules where they are implemented.
- Prefer comments that explain *why* a decision exists, not line-by-line restatements of obvious code.
- Keep public API docs and type hints aligned with behavior.
- When behavior changes, update both inline docs/docstrings and relevant files under `docs/`.

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
- Keep `docs/TASK_AUTHORING.md` updated with tips and rules that apply across multiple tasks.
- Keep `docs/LESSONS_LEARNED.md` updated whenever new pitfalls, regressions, or reusable fixes are discovered.
- Document new reusable helpers and new verifier edge cases when discovered.

## Workflow guidelines
- After any code edit, ask whether to commit before creating a commit.
- Avoid destructive git/file operations unless explicitly requested.
- Prefer clear, versioned contracts over implicit behavior.

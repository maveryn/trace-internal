# TRACE Lessons Learned

## Purpose
This is the shared memory for pitfalls, failure patterns, and reusable fixes.
Update it whenever we learn something that can prevent future task bugs or tooling regressions.

## How to write entries
For each lesson, include:
1. Date
2. Symptom
3. Root cause
4. Fix
5. Preventive rule (generic, reusable)

Keep entries concise and general enough to apply beyond a single task.

## Entries

### 2026-03-03: Template tag without true execution
- Symptom: A task declared a template ID but answer/witness were produced by bespoke logic.
- Root cause: `query_spec.template_id` was treated as metadata annotation rather than executable contract.
- Fix: Enforce typed IR execution and derive answer/evidence from execution trace.
- Preventive rule: Never accept template-id-only payloads; require validated `query_spec.program`.

### 2026-03-03: Non-deterministic ordering drift
- Symptom: Replays produced equivalent semantics but different serialized outputs.
- Root cause: Unordered iteration in set/map traversal.
- Fix: Canonicalize ordering (entity-id sort or deterministic traversal).
- Preventive rule: Each task must define ordering semantics explicitly and ensure emitted outputs are deterministic under that task contract.

### 2026-03-03: Multi-solution witness reward noise
- Symptom: Correct answers received unstable evidence rewards on tasks with multiple valid witnesses.
- Root cause: No explicit canonicalization and unclear acceptance policy.
- Fix: Store canonical witness and explicit acceptance policy (strict vs lenient).
- Preventive rule: Every multi-solution task must define and record canonicalization semantics.

### 2026-03-03: Choice distractor false diversity
- Symptom: Distractors looked different but were semantically equivalent under allowed transforms.
- Root cause: Distinctness checks were pixel-only.
- Fix: Add semantic distinctness checks in distractor policy.
- Preventive rule: For choice tasks, require both uniqueness checks and semantic equivalence rejection.

### 2026-03-03: Evidence parser ambiguity
- Symptom: Different evidence encodings produced inconsistent verification behavior.
- Root cause: Prompt/output encoding conventions were not standardized globally.
- Fix: Define global coordinate formats, normalization, and parsing rules.
- Preventive rule: Keep coordinate conventions/tolerances centralized and referenced by task prompts/verifiers.

## Maintenance rule
Whenever a new pitfall appears in debugging, review, or testing:
1. Add a new lesson entry here.
2. Add/update a reusable guidance bullet in `docs/TASK_AUTHORING.md`.
3. If architecture-level, update `docs/DSL_BLUEPRINT.md`.

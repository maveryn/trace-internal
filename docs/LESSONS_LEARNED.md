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

### 2026-03-04: Single prompt format reduced training-control flexibility
- Symptom: Tasks emitted only one prompt wording, preventing training-time choice between answer-only and answer+evidence supervision.
- Root cause: Prompt system composition had only task/query layers with one rendered output text.
- Fix: Added reusable `answer_or_evidence` prompt layer, rendered/stored both modes per instance, and validated mode metadata/variant consistency.
- Preventive rule: For tasks that may train with different supervision styles, emit and store all required prompt output modes at generation time.

### 2026-03-04: Implicit geometry overlap created ambiguous visuals
- Symptom: Multi-angle scenes could contain touching/crossing primitives, making target evidence harder to localize.
- Root cause: Vertex spacing alone did not guarantee line-level clearance between different entities.
- Fix: Added explicit point/segment minimum-clearance checks, rejected violating layouts, and moved checks into shared layout-constraint helpers.
- Preventive rule: When overlap/touch is disallowed for multi-entity tasks, define and enforce a minimum-clearance policy in generation and assert it in tests.

### 2026-03-04: Order-statistics answer bias in value queries
- Symptom: Even with valid scenes, answer distributions skewed by query type (for example `min` toward low values, `median` toward center).
- Root cause: Candidate sets were sampled first, so final answers inherited order-statistics bias.
- Fix: Use answer-conditioned generation: sample from feasible answers first, then construct distractors around that answer while preserving uniqueness constraints.
- Preventive rule: For multi-query value tasks, keep per-query final-answer sampling close to feasible-uniform unless an explicit curriculum policy documents a different target distribution.

### 2026-03-04: Measurement prompt/visual ambiguity
- Symptom: Measurement prompts said "numeric answer" and geometry measurements could render on non-graph backgrounds with off-grid vertices.
- Root cause: Prompt wording and visual defaults were not strict enough for integer-only measurement policy.
- Fix: Updated measurement templates to require integer-only answers, enforced exact-integer query semantics, and forced graph-paper backgrounds with grid-aligned vertices.
- Preventive rule: For geometry measurement tasks, keep integer-answer wording, integer query semantics, and graph-intersection anchor alignment as hard invariants.

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
3. If architecture-level, update `docs/BLUEPRINT.md`.

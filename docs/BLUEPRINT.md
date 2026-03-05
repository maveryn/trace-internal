# TRACE Blueprint

Status: normative contract for dataset ABI, determinism, and build policy.

## 1) Goal
TRACE generates grounded visual-reasoning instances with:
1. prompt,
2. typed answer,
3. image artifacts,
4. typed evidence,
5. sidecar trace for replay/verifier metadata.

## 2) Taxonomy and config precedence
Use: `domain -> task_group -> task`.

Rules:
1. `task_group` is broad reasoning style; query variants stay inside task via `query_type`.
2. For geometry value-style tasks, default `task_group=measurement`.
3. Config precedence: `domain defaults -> task_group defaults -> task/params`.

## 3) Required artifacts
### 3.1 Train instance (lightweight)
Every record must include:
1. identity + taxonomy (`instance_id`, `instance_seed`, `domain`, `task_group`, `task`),
2. `prompt` and optional `prompt_variants`,
3. `images[]` with relative `path` + `image_hash`,
4. `answer_gt: {type, value}`,
5. `evidence_gt: {type, value}`,
6. `task_complexity`,
7. `trace_ref`,
8. `versions`.

Constraints:
1. `answer_gt.type` and `evidence_gt.type` must be registered type IDs.
2. `images[*].path` is dataset-root-relative (never absolute).
3. `trace_ref` is mandatory.

### 3.2 Sidecar trace (heavy)
Trace payload is mandatory and referenced by `trace_ref`.

Required sections:
1. `scene_ir`
2. `query_spec`
3. `render_spec`
4. `render_map`
5. `execution_trace`
6. `witness_symbolic`
7. `projected_evidence`

## 4) Prompt contract
1. Prompt text must live in external bundles under `prompts/`.
2. Deterministic composition layers:
   - task type
   - query type
   - output mode (`answer_only`, `answer_and_evidence`)
3. Store both prompt modes per instance in `prompt_variants`.
4. Record prompt metadata in trace (`bundle/key/variant/count/slots`).
5. Template cardinality rule: each required list has at least 10 variants.

## 5) Evidence contract
1. Symbolic witness is source of truth in trace.
2. Prompt-facing evidence is projected from witness.
3. `TrainInstance.evidence_gt` uses one resolved default evidence type.
4. Evidence-order semantics are task-defined and deterministic.
5. Unsupported evidence-type requests are hard validation errors.

## 6) Determinism and identity
1. Single root seed per instance: `instance_seed`.
2. All sub-seeds derive via namespace hash.
3. No hidden randomness; no call-order dependence.
4. Canonical JSON (RFC 8785 JCS) is required for identity hashes.
5. Hash algorithm is `blake3`.
6. `instance_id` uses semantic fields + image content hashes (not file paths).

## 7) Sampling policy
1. Global sampling unit is `task`.
2. Domain/task-group probabilities are derived by task aggregation.
3. Query sampling is inside each task (`P(query|task)`), uniform by default.
4. For each query type, sample final answers as close to feasible-uniform as constraints allow.
5. Never relax semantic constraints to force acceptance.

## 8) Build, validation, and finalize
1. Build to staging directory.
2. Generate train records + trace shards.
3. Run pre-finalize validation.
4. Optionally run strict reproducibility pass.
5. Atomically finalize on success.
6. Persist failure bundle on failure.

Required build outputs:
1. `validation_report.json`
2. `build_report.json`

## 9) Versioning policy
1. `instance_version` is ABI contract version.
2. Breaking schema/semantic changes require version bump.
3. Mixed instance versions in one dataset are invalid.
4. Replay-critical versions must be recorded in `versions`.

## 10) Quality gates
A task/build is acceptable only if:
1. schema and trace linkage are valid,
2. answer/evidence/witness come from one execution trace,
3. final answer is unique by construction,
4. determinism checks pass for fixed seeds,
5. prompt metadata and template constraints pass,
6. no silent constraint relaxation is used.

## 11) Document ownership
When contracts change, update this file with:
1. `docs/SYSTEM_ARCHITECTURE.md` (implementation mapping),
2. `docs/TASK_AUTHORING.md` (author workflow),
3. `docs/BUILD_VALIDATION.md` (operational policy),
4. task docs under `docs/tasks/` (task-specific behavior).

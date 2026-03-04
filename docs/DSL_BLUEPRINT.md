# Grounded Visual DSL Project Blueprint

Date: 2026-03-03
Status: Project requirement and implementation blueprint

## 1. Project goal
Build a modular, deterministic visual reasoning environment for RLVR where each generated instance includes:
1. prompt,
2. typed answer,
3. image(s),
4. grounded evidence,
5. deterministic metadata for verification and replay.

## 2. Taxonomy and config scopes
Use this hierarchy everywhere:
1. `domain` (for example: `tile`, `geometry`, `icon`)
2. `task_group` (for example inside `tile`: `path`, `count`, `measurement`)
3. `task` (for example: `tile_shortest_path`)

Task-group policy:
1. use `task_group` for broad shared reasoning style, not for every query variant.
2. keep query variation inside a task via `query_type` when answer/evidence contracts remain compatible.
3. for geometry value-style tasks, default to `task_group = measurement` (for example angle/area value queries).
4. create isolated task groups only when a task does not fit existing group semantics cleanly.

Config precedence (lowest to highest):
1. domain default
2. task_group override
3. task override

No instance-level override for semantic policies such as evidence format.

## 3. First-class artifacts
All generation and export are defined through explicit specs:
1. `SceneSpec`
2. `QuerySpec`
3. `RenderSpec`
4. `PromptSpec`
5. `VerifierSpec`
6. `SamplerSpec`
7. `InstanceRecordSpec` (output ABI)

`PromptSpec` minimum contract:
1. `prompt_bundle_id` (external asset identifier),
2. `task_type_key` (shared composition bucket),
3. `query_type_key` (query-specific composition bucket),
4. slot schema for template placeholders,
5. deterministic prompt seed namespaces.

## 4. Output contracts (sidecar ABI)
`InstanceRecordSpec` is the compatibility contract for dataset writers, dataloaders, trainers, evaluators, and debuggers.

The system has three data layers:
1. `TrainInstance` (always present, lightweight, training-facing)
2. `TraceInstance` (heavy replay/debug payload, sidecar)
3. `CurriculumIndex` (sampling metadata for curriculum)

### 4.1 TrainInstance v1 (required)
Minimal shape:

```json
{
  "instance_version": "v1",
  "instance_id": "blake3:9f2c...",
  "instance_seed": 123456789,
  "domain": "geometry",
  "task_group": "measurement",
  "task": "geometry_angle",
  "prompt": "...",
  "images": [{"image_id": "img0", "format": "png", "image_hash": "blake3:3ac4...", "path": "images/geometry/geometry_angle/000001.png"}],
  "answer_gt": {"type": "integer", "value": 7},
  "evidence_gt": {"type": "point_set", "value": [[10.5, 20.0], [15.0, 18.0]]},
  "task_complexity": {
    "complexity_score": 0.62,
    "complexity_components": {"num_vertices": 8, "num_candidates": 5}
  },
  "trace_ref": {
    "shard_id": "trace_shard_0001.jsonl.zst",
    "line_index": 1823,
    "trace_record_hash": "blake3:ab12..."
  },
  "versions": {
    "dsl_spec_version": "v1",
    "template_version": "v3",
    "operator_bundle_version": "v5",
    "domain_capability_version": "v2",
    "renderer_version": "v4",
    "code_hash": "..."
  }
}
```

Rules:
1. `answer_gt` and `evidence_gt` are always required in `TrainInstance`.
2. Training and dataloaders should not require joining `TraceInstance` to access final answer/evidence targets.
3. `answer_gt` uses a typed envelope: `{type, value}`.
4. `evidence_gt` uses a typed envelope: `{type, value}`.
5. `answer_gt.type` and `evidence_gt.type` must come from a versioned global type registry.
6. Task-specific type extensions must be namespaced (for example `task.geometry_angle.special_form`).
7. Default image output format is PNG unless explicitly overridden by build config.
8. Do not emit `answer_space` in `TrainInstance` (avoid duplicate schema information).
9. Do not emit a separate per-instance `schema_version`; use `instance_version` only.
10. `images[*].path` must be dataset-root-relative (not absolute).
11. `images[*].image_hash` is required and uses `blake3`.
12. Do not add a shared generic image `role` field in `TrainInstance`.
13. For multi-image tasks, image semantics/presentation are task-defined via `RenderSpec` + prompt contract (not global image-role metadata).
14. `trace_ref` is required on every `TrainInstance`.

### 4.2 TraceInstance v1 (required sidecar payload)
Heavy replay/debug metadata is stored as sidecar payload referenced from `TrainInstance`.
Sidecar trace export is mandatory for every dataset build.

Default sidecar storage policy:
1. shard by dataset chunk.
2. one compressed JSONL trace shard per chunk (`.jsonl.zst`).
3. `TrainInstance.trace_ref` points to the trace record (`shard_id`, `line_index`, `trace_record_hash`).
4. `trace_record_hash` uses `blake3` over canonical serialized trace-record bytes.

Trace payload should include:
1. `scene_ir`
2. `query_spec`
3. `render_spec`
4. `render_map`
5. `execution_trace`
6. symbolic witness (task-defined semantics)
7. all supported projected evidence forms
8. optional debug `seed_map`
9. optional duplicated `answer_gt` and `evidence_gt` for audit/replay consistency checks

### 4.3 CurriculumIndex v1
May be embedded or exported as a separate table keyed by `instance_id`.
Required fields:
1. `instance_id`
2. `domain`
3. `task_group`
4. `task`
5. `task_complexity.complexity_score`
6. `task_complexity.complexity_components`

## 5. Core IR contracts
### 5.1 SceneIR core (domain-agnostic)
Required core fields:
1. `entities`: `{entity_id, entity_type, attrs}`
2. `relations`: named relation tables
3. `frames`: coordinate systems
4. `provenance`: seeds, versions, hashes

### 5.2 RenderMapIR core (domain-agnostic)
Required core shape:
1. `image_id -> panels -> anchors`
2. anchor kinds: `bbox`, `polygon`, `polyline`, `point`
3. explicit `coord_space`: `pixel` or panel-local variants
4. optional `z_order`, `occlusion_flags`

`RenderMapIR` is a projection artifact, not semantic truth.

## 6. Query program representation
Query programs use typed SSA-like IR with named outputs.

Each op declares:
1. input types
2. output type
3. required domain capabilities

Generation fails fast on:
1. type mismatch
2. arity mismatch
3. missing capability

## 7. Template bundles
`template_id` resolves to a versioned `TemplateBundle` with:
1. `program_skeleton`
2. `input_schema`
3. `canonicalization_policy` (deterministic ordering/serialization only)
4. `witness_policy`
5. `evidence_projection_policy`
6. optional `consistency_checker`

### 7.1 Prompt template bundles
Prompt templates are external assets (no hardcoded task prompts).

`prompt_bundle_id` resolves to a versioned prompt bundle with:
1. task-type template lists (`task_type_key -> [templates]`),
2. query-type template lists (`query_type -> [templates]`),
3. required placeholder definitions per key,
4. optional shared answer/evidence instruction templates.

Rules:
1. task-type template list must have at least 10 variants,
2. each query-type template list must have at least 10 variants,
3. prompt selection is deterministic from prompt seed namespaces,
4. prompt variant metadata (`bundle/key/index/count`) is recorded in trace payload.

## 8. Domain plugin contract
Each domain registers:
1. entity schemas
2. relation schemas
3. operator implementations
4. anchor projection logic
5. canonicalizers (stable ordering/serialization)
6. renderer adapters
7. capability version

Tasks must declare required capabilities explicitly.

## 9. Evidence contract and verification
Evidence operates in two spaces:
1. authoritative witness space (symbolic): `id_set`, `id_path`, `pair_set`, ...
2. prompt evidence space: `point_set`, `bbox_set`, `point_path`, ...

Policy:
1. store symbolic witness in trace payload, with ordering semantics defined by the task contract.
2. store all supported projected evidence forms in trace payload.
3. expose one default evidence form in `TrainInstance.evidence_gt`.
4. do not duplicate evidence type in a separate top-level field; use `TrainInstance.evidence_gt.type` as the single source of truth.
5. no global evidence-order canonicalization rule; each task defines whether order is significant and how equality should be interpreted.

Unsupported requested evidence form must return a hard validation error, including:
1. requested type
2. task default type
3. supported types

## 10. Evidence format resolution policy
Evidence output format is fixed at dataset build time.

Resolution order:
1. domain default
2. task_group override
3. task override

Rules:
1. no instance-level override.
2. dataloader does not choose evidence form at read time.
3. resolved mapping must be saved in `build_report.json`.

## 10.1 Visual variation policy
Visual variation is also fixed at dataset build time, with deterministic metadata:
1. scene/background style defaults may be defined at task-family scope (`domain/task_group`),
2. task-level overrides are allowed,
3. post-image noise defaults may be defined at task-family scope.

Rules:
1. post-image noise must preserve evidence coordinate validity (photometric/non-geometric edits only by default),
2. applied visual edits are recorded in trace payload (for example `render_spec.post_image_noise`),
3. visual variation sampling uses explicit seed namespaces.

## 11. Answer uniqueness and constraint hardness
Every generated instance must have exactly one valid final answer.

Rules:
1. if an instance is ambiguous, reject/resample or redesign the task.
2. never use output formatting to break semantic ties.
3. canonicalization is for deterministic serialization, not semantic tie resolution.
4. never auto-relax semantic constraints to force acceptance.

## 12. Determinism and seed derivation
Use one required seed per instance:
1. `instance_seed`

All component seeds are derived deterministically via namespace-based derivation:
1. `subseed = hash64(instance_seed, seed_derivation_version, namespace, index)`

Rules:
1. derivation is namespace-based, not call-order-based.
2. include `seed_derivation_version` in metadata.
3. `seed_map` is optional debug payload only.
4. `instance_id` is deterministic and derived from canonical training-facing fields (including `instance_seed`, taxonomy, prompt, image content hashes, answer, and evidence payload).
5. deterministic hash inputs must use RFC 8785 JCS canonical JSON serialization.
6. image file paths are excluded from `instance_id` hash input (use image content identity only).

## 13. Versioning and replay contract
ABI policy:
1. treat `instance_version` as stable contract.
2. breaking field changes require version bump.
3. do not silently change field semantics in-place.
4. enforce one `instance_version` per dataset build; mixed instance versions in one dataset are disallowed.

Canonical serialization policy:
1. use one shared canonical JSON serializer utility for all identity hashes (`instance_id`, `trace_record_hash`, `dataset_id`).
2. serializer API is strict and shared (for example `canonical_json_bytes(obj) -> bytes`); no task-level override hooks.
3. canonicalization failures are hard errors (unsupported type, non-serializable object, non-string key).
4. non-finite numeric values (`NaN`, `Inf`, `-Inf`) are forbidden in serialized outputs.
5. numeric precision normalization is fixed globally.
6. UTF-8 string literals are allowed (no forced ASCII-only escaping).
7. emitted JSON files use canonical object-key ordering (not just hash inputs).

Replay-critical versions must be recorded:
1. DSL/schema version
2. template and operator versions
3. domain capability version
4. renderer version
5. code hash

Dataset-level registry versions must be recorded in build metadata (not per-instance), including type registry version.

## 14. Sampling and build behavior
`SamplerSpec` controls distributions without code edits.

Minimum controls:
1. weighted mixture over tasks (global sampling unit)
2. per-task query-type distribution
3. difficulty/control knob distributions
4. anti-degenerate constraints

Sampling policy:
1. global sampling operates at `task` level only.
2. default global behavior is equal weight across enabled tasks.
3. curriculum updates task-level weights only (for example down-weight tasks with high model accuracy).
4. `domain` and `task_group` probabilities are derived by aggregation from task weights (not sampled directly).
5. each task samples `query_type` internally; default is uniform over that task's supported query types.
6. task-level query-type weights may override uniform defaults when needed.
7. number of query types does not change a task's global sampling probability.

Formal factorization:
1. `P(sample=t,q) = P_task(t) * P_query(q | t)`
2. `P(domain=d) = sum_{t in d} P_task(t)`
3. `P(task_group=g) = sum_{t in g} P_task(t)`

Build-policy summary:
1. use bounded resampling (`max_attempts`) per candidate; if exhausted, reject and sample replacement.
2. do not auto-relax semantic constraints.
3. sidecar trace write failures are hard build failures.
4. finalize outputs atomically (temp staging -> final path).
5. run required pre-finalize validation before finalize.
6. on failure, preserve failure artifacts for debugging.
7. CI strict reproducibility uses fixed, pinned settings.

Normative operational details (validation report shape, failure bundles, cleanup behavior, and CI strict-repro defaults such as `K=5` and `max_attempts_per_instance_ci=100`) are defined in `docs/BUILD_VALIDATION.md`.

## 15. Build telemetry and reports
Every build must emit telemetry in both:
1. logs, and
2. `<dataset_root>/build_report.json`.

`build_report.json` must include:
1. `build_report_schema_version` (required top-level, bump on breaking report-schema changes)
2. `dataset_id` (required top-level, deterministic ID from manifest-critical fields)
3. per-task accepted counts
4. per-task rejected counts
5. rejection reason breakdown by task
6. final rejection rate
7. resolved evidence format map (domain/task_group/task resolution)
8. trace shard manifest summary
9. trace hash algorithm (`blake3`) and canonicalization/version info used for hashing
10. type registry metadata (`type_registry_version`, registry file path, registry file hash)
11. code provenance metadata (for example commit/hash), explicitly marked as non-identity input
12. split metadata (if split artifacts are generated): split ratios/method and split seed
13. image encoding metadata (`image_format`, compression params, color mode, and resolution policy)
14. per-task query-type accepted-count summary for tasks with multiple query types

`dataset_id` policy:
1. compute from canonical hash of dataset-critical configuration only.
2. include full resolved task set with task versions and enabled/disabled status.
3. include dataset-level sampling seed configuration.
4. include requested dataset size (`num_instances` or equivalent requested count).
5. include sampler/evidence-format/type-registry/schema-critical versions and configs.
6. include task-level sampler configuration and per-task query-type sampling configuration.
7. include image encoding configuration (`image_format`, compression settings, color mode, resolution policy).
8. include split configuration and split seed when split artifacts are generated by this build.
9. exclude run diagnostics and outcomes (for example rejection counts, warnings, timing).
10. exclude environment/provenance-only fields such as output path, generation timestamp, and code commit/hash.
11. use RFC 8785 JCS canonical JSON + `blake3`.

Builds continue with warnings by default (no hard fail on rejection-rate threshold).

## 16. RLVR reward contract
Verifier exposes:
1. `reward_answer`
2. `reward_evidence`
3. `reward_consistency`

Evidence verification should be symbolic or anchor-projected, not loose string plausibility.

## 17. Complexity and curriculum contract
Each task must emit:
1. shared scalar `task_complexity.complexity_score`
2. task-defined `task_complexity.complexity_components`

Rules:
1. `complexity_score` is per-task normalized scale (task-local semantics).
2. raw complexity scores are not globally comparable across tasks.
3. curriculum sampling using score must respect task boundaries.
4. components are mainly for analysis/debugging.

## 18. Authoring SDK requirements
Required tooling:
1. Python builder API for specs and typed IR
2. linter for schema/type/capability/evidence checks
3. visual debugger with overlays + step-through
4. macro/subprogram support
5. docs auto-generation from registries

## 19. Global coordinate conventions
Coordinate standards are global:
1. full-image pixel coordinates with top-left `(0,0)`.
2. points are floats: `(x, y)` with `0.0 <= x <= image_width`, `0.0 <= y <= image_height`.
3. boxes are floats: `(x1, y1, x2, y2)` with `0.0 <= x1 < x2 <= image_width`, `0.0 <= y1 < y2 <= image_height`.
4. rounding/parsing policy must be explicit in verifier/prompt contracts.
5. default tolerances are domain/task specific and versioned.

## 20. Implementation plan
### Phase A: schemas and ABI
1. define `TrainInstance`, `TraceInstance`, `CurriculumIndex` schemas.
2. define `SceneIR` and `RenderMapIR` contracts.
3. add schema validators.

### Phase B: typed IR and template bundles
1. implement IR parser/validator.
2. implement op typing and capability checks.
3. implement versioned template registry.
4. implement versioned prompt-bundle registry and loader.
5. implement strict placeholder validation and deterministic prompt composition.

### Phase C: domains and deterministic engine
1. register domain plugins.
2. enforce purity and canonical iteration.
3. implement seed-derivation library + tests.

### Phase D: evidence and verifier stack
1. implement witness projection to all supported forms.
2. implement evidence-format resolver (domain/task_group/task).
3. enforce hard-error behavior for unsupported requested format.

### Phase E: sampler and build pipeline
1. implement bounded resampling with rejection replacement.
2. emit mandatory telemetry + `build_report.json`.
3. support sidecar trace payload export.

### Phase F: curriculum integration
1. implement complexity score/components interface per task.
2. provide curriculum index export and task-bounded sampler hooks.

### Phase G: docs and review tooling
1. task authoring/review checklist automation.
2. regression suites for determinism, uniqueness, and constraint hardness.

## 21. Quality gates
A task is accepted only if:
1. it emits valid ABI records.
2. typed IR and capability checks pass.
3. answer/witness/evidence come from one execution trace.
4. uniqueness-by-construction is enforced.
5. constraint hardness is enforced (no auto-relaxation).
6. determinism/replay checks pass.
7. required build telemetry/report fields are present.
8. complexity score/components are emitted.
9. prompts are externalized via bundle assets (no hardcoded task prompt strings).
10. prompt bundle variant cardinality and placeholder validation checks pass.

## 22. Open questions
1. Which verifier tolerance presets should be standardized first per domain?

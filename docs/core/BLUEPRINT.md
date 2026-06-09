# TRACE Blueprint

Status: normative contract for dataset ABI, determinism, and build policy.

## 1) Goal
TRACE generates grounded visual-reasoning instances with:
1. prompt,
2. typed answer,
3. image artifacts,
4. typed annotation,
5. sidecar trace for replay/verifier metadata.

## 2) Taxonomy and config precedence
Public dataset taxonomy uses: `domain -> scene_id -> task`.

Implementation and config grouping use: `domain -> task_group -> task`.

Rules:
1. `scene_id` is the visual rendering grammar for the task.
2. `task_group` is a broad reasoning/config style; intra-task query
   variants stay inside the task via canonical `query_id` metadata.
   `query_id` is an internal replay selector, not a public sampling unit.
3. For geometry graph-paper readout tasks, use `task_group=measurement`; for multi-object geometry ranking/value-choice scenes, use `task_group=comparison`; for analytical panel-label tasks, use `task_group=analytical`.
4. Config precedence: `domain defaults -> task_group defaults -> task/params`.
5. In task-group config sections (`generation`, `rendering`, `prompt`, `sampling`), keep shared keys under `shared` and task-specific keys under `task_overrides.<task_id>` (flat section keys are unsupported).
6. Build-task weights control cross-task sampling; query-id weights are resolved inside the task from config/params.
7. Task-id naming uses taxonomy-v0 form `task_<domain>__<scene_id>__<objective_contract>` (lowercase snake_case inside each segment). Active/default public tasks must use this form.
8. For taxonomy-v0 ids, the `task_id` domain segment must match class `domain`; `task_group` remains an implementation/config grouping field.
9. Task module naming is mandatory: use file path `trace/tasks/<domain>/<task_group>/<task_name>.py` by default (do not repeat full `task_id` in filename); `puzzles/cell_board` keeps its scene-specific internals under `trace/tasks/puzzles/cell_board/`.

## 3) Required artifacts
### 3.1 Train instance (lightweight)
Every record must include:
1. identity + taxonomy (`instance_id`, `instance_seed`, `domain`, `scene_id`, `task`, plus source `task_group`),
2. `prompt` and optional `prompt_variants`,
3. `images[]` with relative `path` + `image_hash`,
4. `answer_gt: {type, value}`,
5. `annotation_gt: {type, value}`,
6. `reward_contract`,
7. `task_complexity`,
8. `trace_ref`,
9. `versions`.

Constraints:
1. `answer_gt.type` and `annotation_gt.type` must be registered type IDs.
2. `images[*].path` is dataset-root-relative (never absolute).
3. `trace_ref` is mandatory.
4. `reward_contract` is mandatory and must match the resolved public answer/annotation reward mapping.

### 3.2 Sidecar trace (heavy)
Trace payload is mandatory and referenced by `trace_ref`.

Required sections:
1. `scene_ir`
2. `query_spec`
3. `render_spec`
4. `render_map`
5. `execution_trace`
6. `witness_symbolic`
7. `projected_annotation`

## 4) Prompt contract
1. Prompt text must live in external bundles under `prompts/`.
2. Deterministic composition layers:
   - scene
   - task
   - optional query layer keyed by `query_id`
   - output mode (`answer_only`, `answer_and_annotation`)
3. Store both prompt modes per instance in `prompt_variants`.
4. Record prompt metadata in trace (`bundle/key/variant/count/slots`).
5. Template cardinality rule: each required list has exactly 5 high-quality variants.

## 5) Annotation contract
1. Symbolic witness is source of truth in trace.
2. Prompt-facing annotation is projected from witness.
3. `TrainInstance.annotation_gt` uses one resolved default annotation type.
4. Annotation-order semantics are task-defined and deterministic.
5. Unsupported annotation-type requests are hard validation errors.

## 5.1 Reward contract
1. `reward_contract` is builder-owned metadata derived from `answer_gt.type` and `annotation_gt.type`.
2. The public reward contract must be stored on both the train record and sidecar trace.
3. Reward-contract ids are versioned separately from answer/annotation types.
4. If a public annotation type changes, update the reward-contract resolver and task-review mapping in the same patch.

## 6) Determinism and identity
1. Single root seed per instance: `instance_seed`.
2. All sub-seeds derive via namespace hash.
3. No hidden randomness; no call-order dependence.
4. Canonical JSON (RFC 8785 JCS) is required for identity hashes.
5. Hash algorithm is `blake3`.
6. `instance_id` uses semantic fields + image content hashes (not file paths).

## 6.1 Visual variation invariant
1. Repeated-unit visual grammars should include non-semantic unit-size jitter whenever the task image is built from repeated cells, tiles, slots, grid squares, hexes, stickers, or voxels.
2. The first target is a sampled minimum-to-maximum rendered unit-size span of at least `2x` (`max_unit_size / min_unit_size >= 2.0`), for example scale support `0.50..1.00`; narrower ranges are acceptable when readability, scene fit, or annotation integrity requires them, but the exception must be documented.
3. Logical board-size variation alone does not satisfy this requirement; the same logical scene should be renderable with different repeated-unit sizes.
4. Unit-size jitter must be explicit and recorded in render metadata, and all annotation bboxes/points must be projected after the final jittered layout is known.
5. Exemptions or narrower jitter ranges require a documented readability, fit, or verifier-contract reason in the relevant domain/task docs.

## 7) Sampling policy
1. Global sampling unit is `task`.
2. Domain/scene/task-group probabilities are derived by task aggregation.
3. Query sampling is inside each task (`P(query_id|task)`). Use **query
   variant** as the prose term for these branches and `query_id` as the
   canonical field.
4. Validate answer distributions per query id / `query_id` with
   lightweight anti-degeneracy checks over generated answers: at least 5 unique
   answers and max single-answer frequency below 1/3; numeric 5-bin summaries
   are still reported for review but are not hard pass/fail gates.
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
2. answer/annotation/witness come from one execution trace,
3. final answer is unique by construction,
4. determinism checks pass for fixed seeds,
5. prompt metadata and template constraints pass,
6. no silent constraint relaxation is used.

## 11) Document ownership
When contracts change, update this file with:
1. `docs/core/SYSTEM_ARCHITECTURE.md` (implementation mapping),
2. `docs/workflows/TASK_AUTHORING.md` (author workflow),
3. `docs/workflows/BUILD_VALIDATION.md` (operational policy),
4. task docs under `docs/tasks/` (task-specific behavior).

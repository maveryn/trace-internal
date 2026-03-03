# Grounded Visual DSL Project Blueprint

Date: 2026-03-03  
Status: Project requirement and implementation blueprint

## 1. Project goal
Build a modular, deterministic visual reasoning gym for RLVR where each generated instance includes:
1. prompt,
2. typed answer,
3. image(s),
4. metadata-grounded verifier payload.

The DSL must make task authoring compositional and extensible across domains while preserving deterministic replay.

## 2. First-class artifacts
All task generation and export must be defined through explicit first-class specs:

1. `SceneSpec`
- Defines world entities, attributes, relations, and sampling knobs.
- Replay key: `(scene_seed, scene_spec_version, generator_version)`.

2. `QuerySpec`
- Defines executable reasoning program over `SceneIR`.
- Replay key: `(scene_ir, query_seed(optional), query_spec_version, template/operator versions)`.

3. `RenderSpec`
- Defines image packaging (single image, multi-panel, options grid), resolution, style, annotation policy.
- Must produce `RenderMapIR`.

4. `PromptSpec`
- Defines natural language wrapper and output schema/format constraints.
- May include optional glossary/definitions blocks.

5. `VerifierSpec`
- Defines answer equivalence, evidence equivalence, tolerances, cardinality policy, and multi-witness acceptance semantics.

6. `SamplerSpec`
- Defines dataset distribution controls (task-family weights, motif/layout weights, difficulty knobs, anti-degenerate constraints).

7. `InstanceRecordSpec` (canonical output ABI)
- Defines the single versioned instance record shape all tasks must emit.
- Prevents per-task export-format drift and keeps downstream tooling reusable.

## 3. Canonical instance record (ABI)
Each instance must conform to one versioned record schema.

Minimal shape:

```json
{
  "instance_version": "v1",
  "prompt": "...",
  "images": [{"image_id": "img0", "format": "png", "path": "..."}],
  "answer_gt": 7,
  "evidence_gt": {"type": "id_path", "ids": ["cell_0_1", "..."]},
  "payload": {
    "scene_ir": {...},
    "query_spec": {...},
    "render_spec": {...},
    "render_map": {...},
    "execution_trace": {...},
    "canonicalization": {...},
    "versions": {...},
    "seeds": {...}
  },
  "descriptors": {...}
}
```

`InstanceRecordSpec` is the compatibility contract for:
- dataset writers,
- training pipelines,
- evaluation harnesses,
- debuggers.

## 4. Core IR contracts
## 4.1 SceneIR core (domain-agnostic)
Required core fields:
1. `entities`: table of `{entity_id, entity_type, attrs}`
2. `relations`: named relation tables (edge lists and/or typed relation tables)
3. `frames`: coordinate systems used by the scene
4. `provenance`: seeds, versions, hashes

Domain-specific details may live in extension blocks, but core structure remains stable.

## 4.2 RenderMapIR core (domain-agnostic)
Required core shape:
1. `image_id -> panels -> anchors`
2. Anchor geometry kinds: `bbox`, `polygon`, `polyline`, `point`
3. Explicit `coord_space`: `pixel`, `normalized`, or `panel_normalized`
4. Optional: `z_order`, `occlusion_flags`

Render maps are projection artifacts, not semantic truth sources.

## 5. Query program representation
Query programs must use typed SSA-like IR with named outputs.

Example:

```json
{
  "template_id": "shortest_path_v1",
  "program": [
    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
    {"out": "open_cells", "op": "filter", "in": "cells", "predicate": {"blocked": false}},
    {
      "out": "path",
      "op": "shortest_path",
      "cells": "open_cells",
      "relation": "adjacency_open",
      "start": {"entity_id": "cell_0_1"},
      "goal": {"entity_id": "cell_5_4"}
    },
    {"out": "answer", "op": "path_length", "in": "path"}
  ]
}
```

Minimum type system:
- `Set[tile_cell]`, `Path[tile_cell]`, `Int`, `Bool`, `BBox`, `Point`, `Polygon`, `ImageRef`, `ChoiceSet`

Each op declares:
1. input types
2. output type
3. required domain capabilities

Generation must fail fast on:
1. type mismatch
2. arity mismatch
3. missing capability

## 6. Template bundles
`template_id` must resolve to a versioned `TemplateBundle`, not only a raw op list.

A bundle should include:
1. `program_skeleton`
2. `input_schema`
3. `canonicalization_policy`
4. `witness_policy`
5. `evidence_projection_policy`
6. optional `consistency_checker` definition

This makes template versioning semantic and replay-safe.

## 7. Domain plugin contract
Domain is operational via plugins, not a label.

Each domain module must register:
1. entity schemas
2. relation schemas
3. operator implementations
4. anchor projection logic
5. canonicalizers (ordering/tie-break rules)
6. renderer adapters (`RenderSpec` -> image + `RenderMapIR`)
7. capability version

Tasks must declare required capabilities explicitly:

```json
"capabilities_required": {
  "relations": ["adjacency_open", "contains", "overlaps"],
  "ops": ["shortest_path", "path_length"]
}
```

## 8. Evidence contract and verification model
Evidence is defined in two spaces:

1. authoritative witness space (symbolic):
- `id_set`, `id_path`, `pair_set`, ...

2. prompt surface evidence space:
- `id_set`, `point_set`, `bbox_set`, `point_path`, ...

Example:

```json
"evidence_contract": {
  "required": true,
  "witness_type": "id_path",
  "prompt_evidence_type": "point_path",
  "allowed_prompt_types": ["point_path", "bbox_set"],
  "verification": {
    "policy": "exact_on_ids | iou_on_boxes | dist_on_points",
    "tolerances": {"iou": 0.7, "dist_px": 8},
    "cardinality_policy": "exact | subset_ok | superset_ok | min_k",
    "dedupe_policy": "canonical",
    "matching_policy": "hungarian | greedy"
  }
}
```

Evidence normalization rules must be explicit in `PromptSpec`:
1. ID encoding
2. point encoding
3. bbox encoding
4. parsing/rounding policy

## 9. Consistency checker contract
`reward_consistency` must be mechanically defined per task family using a `ConsistencyChecker`.

Required interface:

```text
consistency_checker(answer_pred, evidence_pred, payload) -> [0,1]
```

Typical implementations:
1. witness reconstruction then answer re-derivation
2. constraint satisfaction checks
3. equivalence-class membership for multi-witness tasks

## 10. Choice and distractor model
Choice tasks must be first-class via `choice_spec` and `choice_semantics`.

Supported regimes:
1. `delta_from_base`
- options are generated by applying deltas to a base scene
- store per-option `choice_delta_trace`

2. `independent_scene`
- each option has its own scene/render map
- store per-option scene payloads

Common requirements:
1. explicit layout/labeling
2. distractor uniqueness checks
3. semantic distinctness check (`verifier_equivalence_distinct`)
4. option-local anchor export (`choice_render_map`) when evidence can reference option contents

## 11. Determinism and purity contracts
Determinism requires more than seeds.

Purity constraints:
1. operators are pure over explicit inputs (+ explicit RNG handle if needed)
2. renderers are pure over `(SceneIR, RenderSpec, render_seed)`
3. all iteration over sets/maps is canonicalized

Determinism CI gate:
1. regenerate fixed seed suites
2. compare hashes of `answer_gt`, canonical witness, projected evidence
3. optionally compare `render_map` and image hashes

## 12. Versioning and replay contract
All outputs must be derivable from specs + seeds + versions; no hidden randomness.

Minimum per-instance metadata:
1. `dsl_spec_version`
2. `scene_spec_version`
3. `query_spec_version`
4. `render_spec_version`
5. `prompt_spec_version`
6. `verifier_spec_version`
7. `template_id` + `template_version`
8. `operator_bundle_version`
9. `domain_capability_version`
10. `renderer_version`
11. `code_hash`
12. `scene_seed`
13. `query_seed` (if used)
14. `render_seed` (if used)

If an operator/template change can alter answer, witness, projection, or verifier semantics, it must be versioned.

## 13. Execution trace policy
Execution trace is first-class.

Default storage policy:
1. always store compact summary trace
2. optionally store full trace via debug/config flags (or sidecar files)

Trace content:
1. op-by-op outputs (IDs/scalars)
2. key stats
3. empty/error flags
4. canonicalization decisions

## 14. Distribution control and split integrity
`SamplerSpec` must control generation distributions without code edits.

At minimum:
1. weighted mixture over task families
2. weighted mixture over appearance/layout families
3. difficulty knob distributions
4. anti-degenerate constraints

Fingerprinting policy:
1. `instance_fingerprint` (scene + query + canonical witness)
2. optional `render_fingerprint`
3. optional `semantic_fingerprint`

Use fingerprints for:
1. deduplication
2. split integrity and leakage checks

## 15. RLVR reward contract
Verifier should expose:
1. `reward_answer`
2. `reward_evidence`
3. `reward_consistency`

Anti-hack constraints:
1. evidence verification must be symbolic or anchor-projected, never loose string plausibility
2. strict vs lenient witness acceptance should be a training-stage knob
3. open-ended answer mode should be available when feasible to reduce MC guessability bias

## 16. Difficulty and curriculum descriptors
No subjective fixed complexity score is required.

Log objective structural descriptors:
1. entity counts by type
2. relation counts/sparsity
3. graph stats
4. program stats (`#ops`, op mix, dependency depth)
5. witness stats
6. rendering stats (panel count/options/occlusion where applicable)

Use these descriptors for performance-driven curriculum analysis.

## 17. Authoring SDK requirements
The authoring SDK is a core deliverable.

Required tooling:
1. Python builder API -> compiles to spec + typed IR
2. linter for schema/type/capability/evidence errors
3. visual debugger with overlay + step-through
4. macro/subprogram library support
5. auto-generated docs from registries:
- operator catalog
- domain capability catalog
- evidence policy catalog
- template catalog

## 18. Global coordinate conventions
Coordinate conventions and tolerances must be globally standardized:
1. bbox format `(x1,y1,x2,y2)` with `0 <= x1 < x2 <= 1` and `0 <= y1 < y2 <= 1` (normalized space default)
2. point format `(x,y)` with `0 <= x <= 1` and `0 <= y <= 1` (normalized space default)
3. rounding rules
4. default tolerances by domain family

This prevents verifier drift across tasks.

## 19. Implementation plan
## Phase A: schemas and ABI
1. Define `SceneSpec`, `QuerySpec`, `RenderSpec`, `PromptSpec`, `VerifierSpec`, `SamplerSpec`, `InstanceRecordSpec`.
2. Define `SceneIR`/`RenderMapIR` core contracts.
3. Add schema validators.

## Phase B: typed IR and template bundles
1. Implement SSA IR parser/validator.
2. Implement op typing + capability checks.
3. Implement `TemplateBundle` registry with semantic versioning.

## Phase C: domain plugins and deterministic engine
1. Register domain bundles.
2. Implement purity enforcement and canonical iteration requirements.
3. Add determinism CI harness.

## Phase D: evidence/verifier/consistency layer
1. Implement witness projection and normalization rules.
2. Implement `ConsistencyChecker` per task family.
3. Implement cardinality/matching/minimality policies.

## Phase E: rendering, prompting, and choice framework
1. Implement render/prompt families.
2. Implement `choice_semantics` regimes and distractor framework.
3. Add open-ended vs MC controls.

## Phase F: sampler, fingerprints, and rollout
1. Implement `SamplerSpec` distribution controller.
2. Implement fingerprint-based dedupe/split guards.
3. Enforce blueprint path for all new tasks and migrate legacy wrappers with parity/replay gates.

## Phase G: authoring SDK and documentation
1. Ship Python builder + macro/subprogram library.
2. Ship linter and visual debugger.
3. Auto-generate operator/domain/evidence/template documentation from registries.

## 20. Quality gates
A new DSL task is accepted only if:
1. it emits valid `InstanceRecordSpec`,
2. query program is typed and validated,
3. answer/witness/evidence are derivable from one execution trace,
4. canonicalization is recorded when needed,
5. determinism tests pass,
6. verifier consistency checks pass,
7. required descriptors and fingerprints are present.

## 21. Open questions
1. Should full traces be persisted inline or always sidecar for large-scale datasets?
2. What exact semantic-distinctness checks should be mandatory for each choice family?
3. Which descriptors are mandatory in every export versus optional diagnostics?
4. What migration threshold should gate deprecation of compatibility wrappers?
5. Which domain-specific default tolerances should ship in the first release?

## 22. Recommended defaults
Unless a task family explicitly overrides them:
1. Primary evidence type is fixed per family; alternate prompt evidence types are opt-in overrides.
2. Canonical witness is always stored; strict mode requires canonical match, lenient mode accepts any valid witness under policy.
3. Output envelope is standardized as `{answer, evidence}`; `evidence=null` is valid only when `required=false`.
4. Execution trace storage defaults to compact summary; full traces are enabled via debug config or sidecar outputs.
5. Distractor filtering uses a tiered pipeline: cheap uniqueness checks, then semantic equivalence checks, then bounded resampling.
6. Wrapper deprecation requires policy gates: parity tests, replay stability across releases, migration coverage threshold, and no new wrapper additions.

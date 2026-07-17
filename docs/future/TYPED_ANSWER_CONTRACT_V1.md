# Trace V1 Typed Answer Contract Roadmap

## Status

This is a non-normative future-version proposal. It records design direction
for work after the immediate public release. It must not be used to change the
current Trace v0 task ABI, prompts, reward behavior, or generated datasets.

## Motivation

Trace v0 has two model-facing output paths:

- answer only;
- answer plus annotation.

That distinction supported current annotation-reward experiments, but it also
requires duplicate prompt surfaces and makes spatial answers appear secondary
to symbolic answers. A future version should instead treat integer, string,
numeric, spatial, and structured grounded outputs as ordinary typed answers.

The intended authoring model is simple:

1. Every task defines one canonical prompt family.
2. Every task defines one typed primary answer contract.
3. A generic reward dispatcher scores that answer according to its type.
4. Optional review geometry is internal metadata, not a model response field.

## Immediate Release Boundary

The immediate public release remains Trace v0.

- Keep the existing `answer_gt`, `annotation_gt`, reward contracts, prompt
  variants, and annotation tooling intact.
- Document answer-only training and inference as the primary public path for
  the currently released models.
- Retain annotation infrastructure for reproducibility, task review, and the
  existing reward ablations.
- Do not partially migrate current tasks to this proposal before release.

The v1 work must begin as an explicitly versioned contract change rather than
an incremental reinterpretation of v0 fields.

## V1 Public Response Envelope

Every model response uses one top-level envelope:

```json
{"answer": "<typed value>"}
```

The value can be scalar, spatial, or structured. There is no public
`annotation` response key and no answer-versus-answer-and-annotation runtime
mode.

Examples:

```json
{"answer": 7}
```

```json
{"answer": "B"}
```

```json
{"answer": [612, 284]}
```

```json
{"answer": [100, 80, 240, 150]}
```

The task's typed contract determines how the value is parsed and scored. A
spatial answer is not an annotation; it is the task's primary answer.

## Initial Answer-Type Surface

The first v1 design pass should consider these answer families:

| Family | Example use | Candidate scorer |
| --- | --- | --- |
| `integer` | counts, discrete measurements | normalized exact match |
| `number` | continuous measurements | declared numeric precision/tolerance |
| `string` or `label` | names, categories, visible labels | normalized exact match |
| `point` | GUI click, selected node, visible mark | point-in-region or soft distance |
| `bbox` | selected control, region, or object extent | IoU |
| `point_set` | multiple selected compact objects | unordered spatial matching |
| `bbox_set` | multiple selected regions | unordered IoU matching |
| `point_sequence` | ordered interaction or route | index-aligned spatial matching |
| `segment` or `segment_set` | selected edge, interval, or path | endpoint-distance matching |
| structured answer | grounded count or multi-role interaction | component dispatch |

This list is a design starting point, not an approved ABI. V1 should introduce
only types justified by real task programs.

## Structured Grounded Answers

When both a semantic value and spatial targets are part of the desired reward,
they belong inside one typed answer rather than in separate top-level answer
and annotation fields.

For a grounded count with bounding boxes:

```json
{
  "answer": {
    "count": 4,
    "targets": [
      [100, 80, 150, 130],
      [180, 80, 230, 130],
      [260, 80, 310, 130],
      [340, 80, 390, 130]
    ]
  }
}
```

Its answer contract could declare:

```json
{
  "type": "grounded_count",
  "fields": {
    "count": "integer",
    "targets": "bbox_set"
  }
}
```

The scorer should verify:

- exact count correctness;
- unordered spatial target matching;
- cross-field consistency, including `count == len(targets)`.

This contract is appropriate only for direct visible enumeration where the
targets correspond exactly to the counted units. Derived counts involving
simulation, hidden state, formulas, or game rules should ordinarily remain
integer answers.

An alternative worth testing is returning only the target set and deriving
the count from its cardinality. The structured count form is currently
preferred because it preserves the natural answer to a "how many" question
and permits separate count and localization diagnostics.

## Generic Reward Dispatch

V1 should use one reward entry point. The answer contract declares component
types and scorers; the runtime dispatches without task-specific reward code.

Conceptually:

```text
component_score = scorer(component_prediction, component_target)

answer_reward =
    sum(active_component_weight * component_score)
    / sum(active_component_weight)
```

Examples:

- a scalar integer activates one exact-match component;
- a GUI click activates one point-in-target-region component;
- a grounded count activates count and target-set components.

Component weights and consistency penalties remain open design decisions.
They should be selected globally by answer-contract family, not hand-tuned per
task. Candidate defaults must be validated experimentally; an illustrative
grounded-count split is 0.7 count and 0.3 target localization.

## Contract Versioning And Coexistence

V1 must introduce an explicit `trace_contract_version` in generated records,
reward inputs, and exported datasets.

- V0 and v1 datasets and runs may coexist during development, but one training
  or evaluation job must not mix their response contracts accidentally.
- Loaders and reward code must reject missing, unknown, or incompatible
  contract versions instead of inferring a version from payload shape.
- Prompt generation, answer parsing, reward dispatch, and metrics must resolve
  from the same versioned contract.
- Any temporary v0-to-v1 export tool must be explicit and auditable. Runtime
  compatibility aliases should not become part of the v1 public ABI.
- Removal of v0 support requires a separate release decision after v1 passes
  its acceptance gates.

## Prediction Types And Target Types

Spatial prediction geometry does not always match verifier-target geometry.
The answer contract must declare both when they differ.

For example, GUI grounding may use:

```json
{
  "type": "click_point",
  "prediction_type": "point",
  "target_type": "bbox",
  "scorer": "point_in_bbox"
}
```

The model predicts one point, while the authoritative target is the complete
clickable region. Parsers, review overlays, and reward code must not assume
that prediction and target values have identical shapes.

## Prompt Design

Each task has one canonical semantic prompt family. Task authors do not
maintain separate answer-only and answer-plus-annotation prompt assets.

The final output instruction is generated deterministically from the typed
answer contract. For example:

```text
Return JSON with one integer under "answer".
```

or:

```text
Return JSON with "answer" containing an integer count and a bbox target set.
```

Legitimate task query wording and deterministic template variation remain.
Only the supervision-mode prompt axis is removed. Experimental ablations must
transform contracts automatically rather than require duplicate authored
prompt bundles.

## What Replaces V0 Annotation Responsibilities

V0 `annotation_gt` currently combines several responsibilities. V1 should not
replace it with one differently named public field. Instead, separate those
responsibilities:

| V0 responsibility | V1 location |
| --- | --- |
| authoritative model-answer target | typed `answer_gt` and its verifier target |
| model-supervised spatial output | spatial or structured value under `answer` |
| human review and renderer debugging | optional internal `visual_witness` |
| construction, derivation, and diagnostics | `trace_payload`, `scene_ir`, or `render_map` |

`visual_witness` is the proposed name for optional final-image review geometry.
It is never included in the model prompt or response and is never itself a
rewarded output.

Example:

```json
{
  "answer_gt": {
    "type": "integer",
    "value": 4
  },
  "visual_witness": {
    "type": "point_set",
    "value": [[120, 90], [180, 90], [240, 90], [300, 90]]
  }
}
```

`visual_witness` is optional. If `answer_gt` already contains spatial target
geometry, the review app should derive its overlay from that target instead of
duplicating coordinates.

For example, a click answer can carry its acceptance region directly:

```json
{
  "answer_gt": {
    "type": "click_point",
    "target_bbox": [100, 80, 240, 150]
  }
}
```

The model emits a point under `answer`; the verifier checks whether it falls
inside the target bbox; the review app uses the same bbox as its overlay.

## Coordinate-System Direction

V1 should distinguish model-facing coordinates from canonical render-space
geometry:

- authoritative renderer and verifier targets remain in final-image pixel
  coordinates after all layout, scaling, jitter, and post-processing;
- model-facing spatial answers use one resolution-independent normalized
  convention;
- the scorer converts predictions into the final-image pixel frame before
  applying point, IoU, set, or sequence scoring.

The proposed model-facing default is integer coordinates in `[0, 1000]`
because they are resolution-independent and token-friendly. Normalized
floating-point `[0, 1]` remains an alternative for closer compatibility with
some GUI-grounding evaluation conventions. This choice must be settled through
model and benchmark experiments before the v1 contract is approved.

Every spatial contract must record the coordinate-space id and image size.

The instance trace must also record the complete transform ledger needed to
reproduce model-to-image projection:

- source canvas size;
- final exported image size;
- crop, padding, resize, and rotation operations;
- model-facing coordinate-space id;
- clipping and rounding policy;
- conversion into final-image pixel coordinates.

Property tests must verify that points, boxes, sets, sequences, and segments
remain aligned after every supported transform.

## Spatial Validity And Ambiguity

The v1 contract must define deterministic behavior for:

- multiple valid click locations or target regions;
- overlapping valid regions;
- points exactly on bbox boundaries;
- coordinates outside the declared range;
- inverted, empty, or zero-area boxes;
- duplicate predicted points or boxes;
- valid zero-count and empty-set answers;
- partially visible or occluded targets;
- missing and extra elements in sets and sequences;
- malformed structured answers and missing required fields.

Task construction must still guarantee a unique final answer contract. When a
spatial task intentionally accepts a region or several equivalent locations,
that acceptance set must be explicit in `answer_gt`; it must not be left to a
task-specific heuristic in reward code.

## Reward Robustness And Abuse Tests

Spatial and structured rewards need adversarial validation before use in RLVR.
At minimum, tests must cover predictions that:

- emit many boxes or points to increase accidental overlap;
- use full-image or near-full-image boxes;
- repeat the same target many times;
- report a correct count with unrelated targets;
- report an incorrect count with a correct-size target set;
- omit difficult structured fields;
- exploit clipping, coordinate overflow, or malformed JSON;
- reverse sequence order or segment endpoints where order semantics differ.

Set scorers must penalize both missing and extra targets. Structured scorers
must expose component-level metrics so a high aggregate reward cannot conceal
systematic semantic, spatial, or consistency failure.

## Evaluation Metrics

V1 evaluation should report component metrics in addition to the aggregate
training reward:

- semantic exact or numeric accuracy;
- strict response-schema success;
- point-in-target-region accuracy;
- point-distance score;
- bbox IoU;
- set precision, recall, and matched spatial score;
- sequence accuracy or aligned spatial score;
- structured-answer consistency rate;
- malformed and out-of-range response rates.

V0-versus-v1 comparisons must use a shared semantic metric where possible.
Aggregate v1 reward alone is not comparable with v0 answer accuracy.

## Task Opportunities

Pages is the preferred pilot domain because spatial outputs map naturally to
GUI interactions:

- click a control;
- locate a field, card, row, or panel;
- drag an item from source to destination;
- select several matching controls;
- return an ordered interaction sequence;
- identify an editable or resizable region.

Other candidate domains include:

- graphs: node, edge, or route selection;
- charts: direct mark, region, or interval localization;
- games: source and destination squares or interaction targets;
- illustrations: object localization under a relation;
- tables and forms: direct cell, field, or control selection.

A new output representation does not by itself create a new task. New tasks
must still have a distinct scene-grounded program contract under the active
task-unit policy.

## Collaboration API Goal

V1 task authors should need to define only:

1. the scene and task program;
2. one canonical prompt family;
3. one typed `answer_gt`;
4. the generic scorer id implied by that type;
5. optional `visual_witness` or trace diagnostics when useful.

They should not need to choose a supervision mode, maintain parallel prompt
assets, or implement a task-specific reward function.

## Proposed Delivery Phases

### Phase 0: Freeze and release v0

- Preserve current behavior and reproducibility.
- Publish answer-only as the primary documented model path.
- Keep current annotation experiments and tooling available.

### Phase 1: Contract design

- Specify versioned typed answer schemas.
- Settle coordinate conventions.
- Define composite scoring and consistency behavior.
- Define malformed-output and partial-credit behavior.
- Decide which v0 metadata remains in v1 exports.

### Phase 2: Pages prototype

- Implement a small set of point, bbox, sequence, and grounded-count tasks in
  an isolated v1 prototype.
- Add generic parsers and reward dispatch.
- Compare `[0, 1]` and `[0, 1000]` coordinate conventions.
- Compare spatial-primary tasks against current string/label formulations.

The prototype should cover roughly 10-20 representative tasks rather than a
single answer type. It should include scalar symbolic answers, click points,
region boxes, a set or sequence contract, and at least one structured grounded
count.

### Phase 3: Authoring and review tooling

- Generate output instructions from answer contracts.
- Derive review overlays from spatial answer targets.
- Support optional `visual_witness` for non-spatial answers.
- Validate that collaborators can add tasks without reward-specific code.

### Phase 4: Broader migration decision

- Audit active tasks for natural typed-answer conversions.
- Do not convert tasks where a symbolic answer remains the clearest contract.
- Expand to other domains only after the Pages prototype validates training
  and review behavior.
- Publish an explicit v0-to-v1 data migration tool only if migration is chosen.

## Inventory And Migration Scope

The active registry contains 1000 tasks at the time this roadmap was recorded.
Implementation must remeasure the active inventory when v1 work begins rather
than assuming this count remains fixed.

The full inventory should not be rewritten mechanically:

- ordinary integer, numeric, string, and label tasks should require contract
  adaptation rather than task-program redesign;
- spatial-primary tasks require new answer targets and scorers;
- grounded structured answers require an explicit task-level design decision;
- v0 annotation-supervised tasks require review to decide whether their
  spatial data becomes part of the answer, remains an optional visual witness,
  or is retired from model supervision;
- changing only an output representation does not create a new public task.

Migration should remain prototype-first. No bulk conversion begins until the
Pages pilot passes the go/no-go checkpoint.

## Transition Workflow And Acceptance Gates

Use this sequence for v1 development:

1. Freeze the v0 release contract and establish reproducible baselines.
2. Approve versioned answer, target, coordinate, and structured-output schemas.
3. Implement parsers and scorers behind an isolated v1 contract path.
4. Add unit and property tests before adding task prototypes.
5. Build the Pages pilot and inspect all generated targets in the review app.
6. Run solve-rate and strict-format evaluation for each answer family.
7. Run short RLVR experiments comparing coordinate conventions and reward
   formulations.
8. Evaluate relevant external GUI-grounding benchmarks.
9. Ask a contributor unfamiliar with the implementation to author a typed
   answer task using only the documented API.
10. Make an explicit go/no-go decision before migrating additional domains.

The minimum go/no-go gates are:

- parser and scorer unit tests for every approved answer type;
- transformation property tests for all spatial geometry;
- no unresolved reward-abuse failures;
- correct review-app overlays from answer targets or `visual_witness`;
- stable prompt parsing and solve-rate behavior;
- component metrics available in training and evaluation logs;
- short RLVR runs without obvious reward exploitation or collapse;
- successful external-benchmark coordinate conversion;
- one complete collaborator-authored task without task-specific reward code;
- a documented rollback path that leaves v0 datasets and runs usable.

## Decisions Recorded

Agreed direction:

- v0 remains unchanged for the immediate public release;
- v1 has one canonical prompt family per task;
- v1 has one top-level `answer` response key;
- spatial outputs are primary answer types, not annotations;
- grounded semantic-plus-spatial outputs are structured answers;
- v1 has no public annotation prompt or supervision mode;
- optional internal review geometry is named `visual_witness`;
- authoritative scoring geometry belongs to the answer contract;
- all reward dispatch is type-driven and generic.

Open decisions:

- normalized `[0, 1]` versus integer `[0, 1000]` model coordinates;
- approved initial spatial and structured answer types;
- component weights for structured answers;
- additive versus consistency-gated penalties for malformed composite answers;
- whether some visible-count tasks should return target sets only;
- exact v1 export and migration compatibility policy.

## Success Criteria

The v1 design is ready for implementation only when:

- one parser and reward entry point can score all approved answer types;
- no task requires separately authored supervision-mode prompts;
- spatial answers are resolution-independent at the model boundary;
- renderer/verifier targets remain exact after final-image projection;
- grounded-count rewards penalize missing, extra, and inconsistent targets;
- the review app can inspect tasks without mandatory annotation output;
- a collaborator can add a typed-answer task without writing reward code;
- the Pages prototype shows stable training and benchmark behavior.

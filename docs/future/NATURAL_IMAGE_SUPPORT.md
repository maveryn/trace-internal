# Natural-Image Task Support Proposal

## Status

This is a non-normative future-work proposal. It does not change the current
synthetic-only Trace runtime, taxonomy, task contracts, dataset ABI, or
licensing policy. Natural-image support should begin only through an explicit,
versioned implementation with corresponding updates to the active contracts,
domain docs, source manifests, and validation tooling.

## Decision Summary

A future natural-image extension should:

- introduce a visual domain such as `photos` rather than treating a source
  dataset as a domain;
- retain the public `domain -> scene_id -> task_id` taxonomy;
- use a finite ontology of broad scene families, initially the 16 official
  Places365 level-two meta-categories;
- treat Places365, COCO, and COCO-Stuff as asset sources recorded in trace
  metadata, not as public scenes or sampling units;
- keep equal public task weighting across eligible scene-task combinations;
- sample source images inside a scene-task uniformly from its combined,
  deduplicated eligible asset pool, which makes each source's probability
  proportional to its eligible image count;
- use authoritative source annotations or deterministic transformation traces
  for answers and annotations, never model-predicted geometry;
- split and deduplicate source images before deriving task instances so one
  source image cannot leak across train and test.

## Motivation

Natural images offer much greater within-scene visual diversity than Trace's
current synthetic renderers. A single objective such as missing-patch
selection can be instantiated over thousands of photographic environments.
The public taxonomy still needs bounded, interpretable sampling units, however.

Neither of these extremes is suitable:

- one public scene for all natural images hides meaningful environment
  diversity and gives the entire source pool one scene-task weight;
- one public scene per fine-grained category or image creates hundreds or
  thousands of public sampling units and lets source-dataset size determine
  task weight.

The intended compromise is a small, stable scene ontology with substantial
asset diversity inside each scene.

## Taxonomy

### Domain

Use a visual-domain name such as `photos`. The domain name should describe the
rendered medium, not the reasoning program or source dataset.

Example public task id:

```text
task_photos__shopping_and_dining__jigsaw_arrangement_label
```

`Places365`, `COCO`, and `COCO-Stuff` remain source metadata. They must not
appear as public scene ids merely because they supplied an image.

### Initial Scene Ontology

Places365 has 365 fine-grained environment categories. That is too large for
the initial Trace public scene surface. Places365 also provides a hierarchy
with 16 level-two meta-categories. Trace should use normalized versions of
those 16 groups for `places16_trace_v1`:

| Scene id | Broad environment family |
| --- | --- |
| `indoor_shopping_dining` | Indoor shopping and dining |
| `indoor_workplace` | Offices, factories, laboratories, and other workplaces |
| `indoor_home_lodging` | Homes, hotels, and lodging interiors |
| `indoor_transportation` | Vehicle interiors and transportation stations |
| `indoor_sports_leisure` | Indoor sports and leisure spaces |
| `indoor_cultural_civic` | Art, education, religion, military, law, and civic interiors |
| `outdoor_water_ice_snow` | Water, ice, and snow environments |
| `outdoor_mountain_desert_sky` | Mountains, hills, deserts, and open-sky environments |
| `outdoor_forest_field_jungle` | Forests, fields, and jungle environments |
| `outdoor_natural_with_structures` | Natural environments containing man-made elements |
| `outdoor_transportation` | Roads, parking areas, bridges, boats, and airports |
| `outdoor_cultural_historic` | Cultural and historical buildings and places |
| `outdoor_sports_parks_leisure` | Sports fields, parks, and outdoor leisure spaces |
| `outdoor_industrial_construction` | Industrial and construction environments |
| `outdoor_residential_agricultural` | Houses, cabins, gardens, and farms |
| `outdoor_commercial_urban` | Commercial buildings, shops, markets, cities, and towns |

These are semantic groups, not visual styles. The implementation should retain
the source's fine category and secondary hierarchy tags in metadata. The
public scene id is one deterministic primary category used for taxonomy and
weighting.

Example mapping record:

```json
{
  "source_category": "boardwalk",
  "primary_trace_scene": "outdoor_sports_parks_leisure",
  "secondary_scene_tags": [
    "outdoor_water_ice_snow",
    "outdoor_natural_with_structures"
  ],
  "mapping_version": "places16_trace_v1"
}
```

The initial 16 categories should be retained until contact-sheet review and
coverage statistics demonstrate a concrete reason to merge or split one.

## Source Roles

### Places365

Places365 supplies broad environment coverage and native scene-category
labels. It is appropriate for tasks whose ground truth comes entirely from a
known image transformation, including:

- jigsaw arrangement;
- missing-patch selection;
- rotated, reflected, or swapped tile detection;
- whole-image correspondence or comparison.

Places365 scene labels alone are not sufficient ground truth for instance
counting, object localization, or object-relation tasks.

### COCO And COCO-Stuff

COCO supplies object instances, bounding boxes, and masks. COCO-Stuff adds
stuff-region annotations. These sources can support:

- the transformation-grounded tasks listed above;
- object counting;
- object spatial relations;
- attribute-conditioned counting when the required attribute is authoritative;
- object or region segmentation tasks.

COCO does not provide the same public scene ontology as Places365. A frozen
Places365 classifier can assign each eligible COCO image to the Trace scene
ontology:

```text
COCO image
  -> Places365 fine-category probabilities
  -> aggregate probabilities into places16_trace_v1
  -> select a primary scene
  -> require confidence and top-two margin thresholds
  -> reject ambiguous assignments
```

COCO-Stuff regions and captions may be used as validation signals, but they
must not silently replace the versioned primary-scene assignment rule.

## Task Eligibility

Source eligibility is task-specific:

| Task family | Places365 | COCO/COCO-Stuff | Ground-truth source |
| --- | --- | --- | --- |
| Jigsaw or patch ordering | Yes | Yes | Deterministic transformation trace |
| Missing-patch selection | Yes | Yes | Deterministic crop/transformation trace |
| Rotated or swapped tile detection | Yes | Yes | Deterministic transformation trace |
| Whole-image comparison | Yes | Yes | Deterministic transformation trace |
| Object counting | No | Yes | Authoritative instances/masks |
| Object spatial relations | No | Yes | Authoritative instances/masks |
| Attribute-conditioned counting | No by default | When authoritative | Authoritative structured annotations |
| Region or segmentation tasks | No | Yes | Authoritative masks |

An image is eligible for a scene-task only if it passes all applicable gates:

- allowed source split and audited source license;
- deterministic primary-scene assignment;
- minimum scene-classification confidence and margin;
- required authoritative annotations;
- task-specific object, mask, resolution, and crop constraints;
- image-quality and usable-content checks;
- exact- and near-duplicate removal.

## Weighting And Sampling

### Public Task Weight

Natural-image diversity must not bypass Trace's task-level weighting policy.
Each eligible public scene-task combination receives the same default task
weight as a synthetic task. For example, a jigsaw task implemented for all 16
photo scenes creates 16 public tasks and therefore 16 equal scene-task units.

Do not multiply public task weight by:

- the number of source datasets;
- the number of fine-grained Places categories;
- raw source-dataset size;
- the number of available images in one scene.

### Source Mixing Inside A Scene-Task

Within one scene-task, sample uniformly from the combined eligible,
deduplicated image pool. The implied source probabilities are:

```text
P(Places365 | scene, task)
    = N_places_eligible / (N_places_eligible + N_coco_eligible)

P(COCO | scene, task)
    = N_coco_eligible / (N_places_eligible + N_coco_eligible)
```

This is preferable to a fixed 50/50 source split because it reflects the
actual eligible coverage of each source within that scene and task. It is also
different from weighting by raw dataset size: only assets that pass the
scene-task eligibility, quality, licensing, split, and deduplication gates are
counted.

If a source cannot support a task contract, its eligible count is zero. Source
probabilities and eligible counts must be materialized in a versioned asset
index rather than recomputed implicitly during generation.

## Asset And Trace Metadata

A versioned asset manifest should record at least:

```json
{
  "asset_id": "...",
  "source_dataset": "coco",
  "source_release": "...",
  "source_image_id": "...",
  "source_split": "train",
  "trace_split": "train",
  "primary_scene_id": "outdoor_commercial_urban",
  "secondary_scene_tags": [],
  "scene_mapping_version": "places16_trace_v1",
  "scene_assignment_method": "places365_classifier_v1",
  "scene_confidence": 0.91,
  "scene_margin": 0.24,
  "annotation_kinds": ["bbox", "instance_mask"],
  "content_hash": "...",
  "duplicate_group_id": "...",
  "license_record_id": "..."
}
```

Generated task traces should additionally record the chosen source asset,
task-specific eligibility version, transformation parameters, derived geometry,
and verifier payload version. Random asset selection and all transformations
must remain deterministic from recorded seeds and specs.

## Answers And Annotation

Natural-image tasks retain the same grounding rules as synthetic Trace tasks:

- answers and annotation come from the same execution trace;
- annotations mark minimal visual witnesses in final-image pixel space;
- verifiers use metadata and projected source annotations, not pixels;
- model detections or classifier predictions are never object-level verifier
  ground truth;
- transformed source boxes and masks must be projected after the final crop,
  resize, padding, layout, and option placement.

For transformation tasks, the deterministic transformation trace is
authoritative. For semantic object tasks, only source datasets with suitable
audited annotations are eligible.

## Split And Leakage Policy

Splitting occurs at the source-image or duplicate-group level before task
instances are generated.

- Every crop, patch, option set, and task derived from one source image belongs
  to the same Trace split.
- Exact and perceptual near-duplicates across Places365 and COCO must share one
  duplicate group and one split.
- A source image must not enter both train and test through different tasks,
  scenes, datasets, resolutions, or transformations.
- Split manifests are immutable and versioned once used for a published run.

The first release should report split counts by scene, source, task family,
and duplicate group.

## Licensing Gate

Natural-image support has a separate licensing risk from synthetic Trace
assets. Dataset-code or model licenses do not automatically grant permission
to redistribute the underlying images.

Before implementation, audit and record:

- image-level source and redistribution terms;
- annotation licenses separately from image licenses;
- attribution or notice requirements;
- whether generated crops and transformed images may be redistributed;
- whether training and benchmark-only use have different restrictions;
- removal and provenance procedures for individual assets.

The audit must cover Places365 images, the Places365 model/code, COCO images,
COCO annotations, and COCO-Stuff annotations independently. No source should be
described as permissively licensed solely because its tooling repository is.

## Proposed Implementation Shape

The exact source layout should be approved during implementation, but the
ownership boundaries should remain:

- public task files own task/query semantics, answer binding, annotation
  binding, prompt slots, and final output;
- photo-scene packages own scene-specific eligibility and composition rules;
- domain-shared photo infrastructure owns asset-manifest loading, deterministic
  source selection, transformation geometry, and source-annotation projection;
- source adapters own dataset-specific record parsing without exposing source
  dataset names as public taxonomy;
- a versioned ontology module owns the Places365-to-Trace mapping.

A normalized internal asset record may be introduced, but it must not become a
second public taxonomy.

## Rollout Plan

### Phase 1: Source And Ontology Audit

1. Complete licensing and redistribution review.
2. Freeze `places16_trace_v1` names and mappings.
3. Build contact sheets and coverage counts for all 16 scenes.
4. Define confidence, margin, quality, and ambiguity rejection thresholds.

### Phase 2: Asset Index And Splits

1. Index Places365 and COCO/COCO-Stuff into one normalized manifest.
2. Assign deterministic primary scenes and preserve secondary tags.
3. Compute exact and perceptual duplicate groups.
4. Freeze source-image-level train/test splits.
5. Materialize eligible counts by scene, task family, and source.

### Phase 3: Transformation-Grounded Pilot

Implement a small set of image-only tasks, such as jigsaw arrangement and
missing-patch selection, over both Places365 and COCO. Validate source mixing,
scene balance, transformation projection, review quality, and leakage controls
before adding semantic tasks.

### Phase 4: Annotation-Grounded Tasks

Add COCO/COCO-Stuff tasks that require authoritative instances or masks. Keep
their public taxonomy scene-based and report source eligibility explicitly.

### Phase 5: Calibration And Release Review

Run task review, distribution checks, calibration, supervision-policy review,
and domain-finalization review. Compare source and scene performance to ensure
that one dataset, category, or visual shortcut does not dominate a task.

## Acceptance Gates

Natural-image support is ready for an active contract only when:

- the public scene ontology is finite, versioned, and deterministic;
- every source asset has provenance, license, split, and duplicate metadata;
- train/test leakage checks pass at duplicate-group level;
- public weighting remains equal by eligible scene-task combination;
- source sampling inside each scene-task matches combined eligible pool counts;
- verifier targets use authoritative annotations or deterministic
  transformations;
- ambiguous scene assignments and unusable assets are rejected;
- source, scene, task, and split distributions are reviewable;
- representative samples from every scene-source-task combination pass visual,
  prompt, answer, and annotation review.

## References

- [Places365 repository and category resources](https://github.com/CSAILVision/places365)
- [Places365 category hierarchy](https://docs.google.com/spreadsheets/d/1H7ADoEIGgbF_eXh9kcJjCs5j_r3VJwke4nebhkdzksg/edit?usp=sharing)
- [COCO-Stuff repository and annotation information](https://github.com/nightrome/cocostuff)
- [ADE20K scene parsing dataset](https://ade20k.csail.mit.edu/)


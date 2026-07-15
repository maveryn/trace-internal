# Trace Grounding Benchmark Subsets

Fixed manifest-only subsets for grounding benchmark evaluation.

- sample seed: `42`
- `RefCOCO` is restricted to `split == RefCOCOg_test` and sampled to 1000 rows.
- Other grounding benchmarks are kept at full size.

| benchmark | alias | selected rows | source rows | selection |
| --- | --- | ---: | ---: | --- |
| `refspatial_wo_unseen` | `RefSpatial_wo_unseen` | 200 | 200 | all_rows |
| `osworld_g` | `OSWorld_G` | 564 | 564 | all_rows |
| `refcoco` | `RefCOCO` | 1000 | 57457 | fixed_random_subset ({"split": "RefCOCOg_test"}) |
| `groundingme` | `GroundingME` | 1005 | 1005 | all_rows |
| `tdbench_grounding` | `tdbench_grounding_rot0` | 200 | 200 | all_rows |

# External RLVR Validation

Workflow for building recurring RLVR validation packs from external benchmarks.

## 1) Scope
This workflow is for answer-only external validation during RLVR.

It is intentionally separate from TRACE training export:
- TRACE training data keeps TRACE-native prompts, answers, evidence, and reward contracts.
- External validation keeps benchmark-faithful prompts and answer-only targets.
- The implementation lives under the top-level `benchmark/` package, not under `trace/`.

## 2) Design goals
Use this path when we want recurring benchmark validation with:
- one flat RLVR-ready parquet or JSONL per benchmark,
- benchmark-faithful prompt text stored in the export,
- deterministic `512`-sample subsets,
- stable answer-only parsing via the existing RLVR validation stack,
- and a one-shot build directly from official benchmark sources.

For the current parquet workflow, images are embedded directly into each parquet row as bytes.
That keeps each benchmark export standalone and removes the need for a separate `assets/` tree.

## 3) Source policy
The benchmark builder reads directly from official sources.

Current policy:
1. use official Hugging Face dataset repos whenever possible,
2. prefer `test`,
3. if `test` is unlabeled or unavailable, fall back to `dev`,
4. if neither exists, fall back to `train`,
5. allow benchmark-specific custom readers when the official repo packaging is not directly loadable.

## 4) Prompt policy
We keep the benchmark prompt intact in the exported validation parquet.

If boxed-answer formatting is desired, apply it at validation runtime through RLVR prompt formatting
for example `rlvr/examples/format_prompt/math.jinja`) rather than baking the suffix into the parquet.

Optional export-time suffix styles remain supported for one-off builds:
1. `boxed_final_answer`
2. `boxed_option_letter`

## 5) Frozen shortlist manifest
The current recurring validation shortlist lives in:
- `benchmark/configs/external_validation_v1.yaml`

It freezes the current `8 x 512` plan:
1. `mathvista`
2. `mathvision`
3. `charxiv`
4. `ocrbench_v2`
5. `seephys`
6. `spatialeval`
7. `vgcure`
8. `puzzlevqa`

Split choices in the current manifest:
1. `MathVista` uses `testmini` because the public `test` split is unlabeled.
2. `CharXiv` uses `validation` because the public `test` split is unlabeled.
3. `SeePhys` and `PuzzleVQA` use `train` because they do not expose `test` or `dev`.
4. `VGCure` uses a custom reader over the official Hugging Face `test` files.

## 6) Export command
Run:

```bash
PYTHONPATH=. python scripts/export_external_eval_to_rlvr.py \
  --output-root <rlvr_validation_output_dir>
```

This writes:
1. one standalone RLVR-ready parquet per benchmark
2. no separate image asset directory when using the default parquet mode

## 7) Exported row contract
Each exported validation row currently includes:
1. `uid`
2. `instance_id`
3. `benchmark_id`
4. `source_id`
5. `prompt`
6. `prompt_mode`
7. `images`
8. `ground_truth`
9. `parser_family`
10. `metadata`

Notes:
1. These rows are answer-only on purpose.
2. They use the existing non-TRACE RLVR validation path in `rlvr/verl/utils/val_reward.py`.
3. `parser_family` is exported for bookkeeping today; the current RLVR validator still relies mainly on `ground_truth` shape and MathRuler-backed parsing.
4. The default `external_validation_v1` manifest does not append boxed-answer text inside the parquet; TRACE RLVR runs add the shared validation formatting at runtime.

## 8) What this workflow does not do
This workflow does not yet:
1. add evidence prompting,
2. add LLM-judge grading,
3. cover every raw benchmark schema automatically,
4. guarantee that public `test` splits are labeled unless the manifest explicitly chooses them.

Those are later layers. This workflow is the stable, recurring answer-only validation pack builder.

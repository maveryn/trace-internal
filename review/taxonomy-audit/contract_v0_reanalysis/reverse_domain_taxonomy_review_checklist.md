# Reverse-Domain Taxonomy Review Checklist

This checklist tracks the full contract-v0 taxonomy cleanup pass requested for
all active TRACE domains. `plans/` is retired; keep notes and outputs in this
taxonomy-audit package.

## Scope

- Review all active domains in reverse alphabetical order:
  `three_d`, `puzzles`, `physics`, `pages`, `misc`, `illustrations`, `icons`,
  `graph`, `geometry`, `games`, `charts`.
- Use `docs/core/TAXONOMY.md` and `docs/core/TASK_UNIT_POLICY.md` as the
  taxonomy policy sources.
- Use active code, configs, prompts, docs, review artifacts, and open issue
  threads as factual inputs, not as policy authorities.
- Do not run solve-rate calibration in this pass.

## Per-Domain Workflow

For each domain:

1. Read every open taxonomy issue for the domain before making edits.
2. Classify each issue:
   - `fix_now`: concrete stale id, stale query branch, generic program schema,
     inconsistent naming, missing argument axis, or incorrect program contract.
   - `defer_discussion`: asks a broad task-boundary policy question, requests
     discussion, or affects multiple scenes/domains in a way that needs human
     confirmation before changing task boundaries.
   - `no_change_needed`: already consistent with the core taxonomy and
     task-unit policy; add a repair note explaining why.
3. Inspect the domain rows in:
   - `task_query_analysis.csv`
   - `proposed_task_summary.csv`
   - `source/manual_query_boundary_seed.csv`
   - `source/program_argument_overrides.json`
   - `domain_taxonomies/<domain>.md`
4. Fix concrete taxonomy metadata issues:
   - eliminate stale task/query ids from source seeds and generated outputs;
   - normalize semantically identical program schemas to the same wording;
   - make generic program schemas concrete enough to expose candidate set,
     operand roles, derived computation, final operator, output binding, and
     annotation role template;
   - keep query arguments as bounded parameter metadata, not taxonomy leaves;
   - keep answer/annotation schema names from the shared vocabulary.
5. Rebuild the taxonomy package with
   `PYTHONPATH=. python review/taxonomy-audit/contract_v0_reanalysis/build_contract_v0_reanalysis.py`.
6. Re-review the domain after rebuild for:
   - generic placeholders that remain in finalized rows;
   - inconsistent program code for the same operation;
   - stale proposed task ids or stale query ids;
   - duplicate base program contracts;
   - open issues that still need notes.
7. Add an agent repair note to each relevant issue describing what changed or
   why the issue is deferred. Leave the issue open unless a human explicitly
   asks to resolve it.

## Domain Checklist

- [x] `three_d`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `puzzles`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `misc`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `physics`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `pages`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `illustrations`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `icons`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `graph`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `geometry`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `games`: read issues, fix concrete metadata, rebuild, re-review, note issues.
- [x] `charts`: read issues, fix concrete metadata, rebuild, re-review, note issues.

## Final Checks

- [x] `summary.json` reports `duplicate_base_program_contract_count == 0`.
- [x] `summary.json` reports all program argument rows are `curated`.
- [x] No generated taxonomy rows reference retired task ids in structured fields.
- [x] The review app index is reloaded after taxonomy/review artifact changes.
- [x] Targeted validation commands and any skipped checks are reported.

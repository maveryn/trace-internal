# Games Post-Migration Checklist Issues

Audit date: 2026-06-27

## Open Issues

No open post-migration issues identified for `games` from this follow-up pass.

## Resolved

### GM-010 - Game task docs used compact Program Contract sections

Resolved on: 2026-07-01

Fix:

- Normalized all `164` game task docs under `docs/tasks/games/` so each
  `## Program Contract` section exposes:
  `Program:`, `Candidate set:`, `Operands:`, `Operation:`, `Output binding:`,
  `Annotation witnesses:`, and `Query ids:`.
- Used `scripts/normalize_reviewed_domain_program_contract_docs.py` to preserve
  each existing compact program expression and expand it into reviewable fields.
- This was docs-only; task code, configs, prompts, review artifacts, and solve
  rate were not changed.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 python -B scripts/normalize_reviewed_domain_program_contract_docs.py --check`
- Result: `reviewed-domain task docs scanned: 444`, `docs requiring normalization: 0`.
- Custom structural scan reports `games docs 164`, `missing_any 0`, and no
  placeholder schema wording in normalized game Program Contract sections.

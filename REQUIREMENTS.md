# TRACE Requirements

## Version
`requirements_version: 1.0.0`

## Purpose
This file is the canonical, versioned requirements contract for TRACE.
Use it to track what the project must do (not implementation details).

## Requirements (Current Baseline)
1. TRACE must generate grounded visual reasoning instances with:
- prompt
- typed answer
- image(s)
- metadata-grounded verifier payload
2. Task architecture must follow explicit first-class specs:
- `SceneSpec`, `QuerySpec`, `RenderSpec`, `PromptSpec`, `VerifierSpec`, `SamplerSpec`, `InstanceRecordSpec`
3. Query semantics must be represented as typed IR with named intermediate outputs.
4. Answers and evidence must be derived from the same execution trace.
5. Verifier logic must use metadata contracts/projections as source of truth.
6. Generation and replay must be deterministic using explicit seeds/versions (no hidden randomness).

## Versioning Policy
Use semantic versioning for `requirements_version`:
1. `MAJOR`: breaking requirement changes (remove/replace/meaningfully redefine requirements).
2. `MINOR`: new requirements added in backward-compatible way.
3. `PATCH`: clarifications/wording fixes with no requirement meaning change.

## Update Rule
Whenever requirements are added, removed, or changed:
1. Update `requirements_version` explicitly.
2. Add an entry in `Change Log` with date and summary.
3. Keep `docs/DSL_BLUEPRINT.md` and `AGENTS.md` aligned with this file.

## Change Log
1. `1.0.0` (2026-03-03): Initial requirements baseline created.

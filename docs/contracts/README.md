# Contract Docs

This folder contains repo-wide contracts that should change only when TRACE
runtime semantics change. Keep workflow instructions, migration plans, generated
inventories, and domain-specific policy outside `docs/contracts/`.

- `BLUEPRINT.md` — dataset ABI, determinism, build, and quality gates.
- `SYSTEM_ARCHITECTURE.md` — runtime layers, module boundaries, and lifecycle.
- `TAXONOMY.md` — public `domain -> scene_id -> task_id` taxonomy.
- `TASK_UNIT_POLICY.md` — task/query boundary and merge/split rules.
- `PROGRAM_SCHEMA_CATALOG.md` — reusable program-schema names for task contracts.
- `PROMPT_SYSTEM.md` — prompt asset schema, composition, and metadata.
- `RLVR_REWARD_CONTRACTS.md` — answer/annotation reward dispatch contract.
- `VALIDATION_ERROR_CODES.md` — validation error-code catalog.

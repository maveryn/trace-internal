# Core Docs

This folder contains repo-wide contracts that should change only when TRACE
runtime semantics change. Keep workflow instructions, migration plans, generated
inventories, and domain-specific policy outside `docs/core/`.

- `BLUEPRINT.md` — dataset ABI, determinism, build, and quality gates.
- `SYSTEM_ARCHITECTURE.md` — runtime layers, module boundaries, and lifecycle.
- `TAXONOMY.md` — public `domain -> scene_id -> task_id` taxonomy.
- `TASK_UNIT_POLICY.md` — task/query boundary and merge/split rules.
- `PROMPT_SYSTEM.md` — prompt asset schema, composition, and metadata.
- `RLVR_REWARD_CONTRACTS.md` — answer/annotation reward dispatch contract.

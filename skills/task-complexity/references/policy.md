# Complexity Policy

## Core contract
- `complexity_score` is **within-task only**. Do not interpret it as a cross-task or cross-domain global ranking.
- `complexity_components` should contain **normalized criterion values in `[0,1]`**.
- Config should own **weights**, never raw-value transforms or threshold formulas.
- Missing an active criterion is a design bug; zero-weight criteria may be omitted.

## Scope rule for criteria
- **Domain-level criteria** must be meaningful for every task in the domain.
- **Task-group criteria** must be meaningful for every task in that family.
- **Task-level criteria** are allowed when needed, but they should be rare.
- If a criterion is not meaningfully scorable across the full scope where it lives, move it down a level.

## Ownership split
- **Task code** owns:
  - raw measurements,
  - raw-to-normalized transforms,
  - criterion values in `[0,1]`.
- **Domain config** owns:
  - default criterion vocabulary,
  - default weights.
- **Task-group config** owns:
  - weight overrides for a reasoning family.
- **Task override** owns:
  - rare exceptions when a task truly breaks the family pattern,
  - rare task-specific criteria that do not belong at the broader scopes.

## Preferred scoring rule
Use a weighted mean over the active criteria:

`score = sum(weight_i * criterion_i) / sum(active_weights)`

Rules:
- keep weights non-negative,
- normalize by the active weight sum,
- keep the final score clipped to `[0,1]`.

## Preferred config shape
When editing or implementing complexity config support, mirror the usual TRACE precedence:

```yaml
complexity:
  criteria_weights:
    visual_scan: 0.30
    ambiguity: 0.25
```

Apply it at:
- `configs/domains/<domain>/base.yaml` for domain defaults,
- `configs/domains/<domain>/<task_group>.yaml` for family overrides,
- `task_overrides.<task_id>` only for true outliers.

Do not put min/max raw transforms in config. Those belong in task/domain code.

Interpretation:
- domain config should define the broad baseline criteria,
- task-group config may add family-wide specialized criteria,
- task overrides should mostly adjust weights, not invent new policy.

## Component design rules
- Keep criterion names stable and snake_case.
- Prefer small vocabularies at each scope; do not create a huge domain-level list just because a few task groups need niche criteria.
- Make every criterion monotonic with respect to a real difficulty knob.
- Keep criteria interpretable; a reviewer should understand why a value increased.
- Put raw measurements in trace/debug payloads if they are worth keeping.

## Migrating task-local formulas
Many current tasks still use ad hoc scalar formulas. When touching one:
1. identify the real difficulty knobs,
2. name the normalized criteria,
3. preserve the approximate easy/medium/hard ordering,
4. stop short of inventing a fake cross-domain scale.

## Review questions
- If I increase the obvious hard knob, does the score increase?
- If I simplify the scene/query, does the score decrease?
- Are weights coming from config rather than hidden task-local constants?
- Are `complexity_components` normalized and interpretable?
- Do the domain-level criteria really apply to every task in the domain?
- Do the task-group criteria really apply to every task in the family?
- Is this task override truly necessary, or should the criterion/weight live at a broader level?

# Annotation Contract Migration

This note records the completed repo-wide breaking migration from the old
`evidence` public contract to the current `annotation` contract. TRACE v0 uses
annotation terminology everywhere in active code, prompts, review tooling,
exports, tests, and docs. Do not add compatibility aliases for the old public
fields.

## Current Contract

Canonical answer-plus-annotation JSON:

```json
{"annotation":[[120,160]],"answer":3}
```

Current public fields and modes:

- `annotation_gt`
- `projected_annotation`
- `answer_and_annotation`
- `prompt_answer_and_annotation`
- `ground_truth_answer_and_annotation`
- final response key `"annotation"`
- reward metrics such as `annotation_reward` and `annotation_parse_ok`

## Historical Mapping

Use this mapping only when interpreting old notes or deleting stale artifacts.
New code and docs must use the current annotation names directly.

| Retired term | Current term |
| --- | --- |
| `evidence` public JSON key | `annotation` public JSON key |
| `evidence_gt` | `annotation_gt` |
| `evidence_schema` | `annotation_schema` |
| `evidence_type` | `annotation_type` |
| `evidence_value` | `annotation_value` |
| `projected_evidence` | `projected_annotation` |
| `overlay_evidence` | `overlay_annotation` |
| `answer_and_evidence` | `answer_and_annotation` |
| `prompt_answer_and_evidence` | `prompt_answer_and_annotation` |
| `ground_truth_answer_and_evidence` | `ground_truth_answer_and_annotation` |
| `answer_evidence` review/export column | `answer_annotation` |
| `evidence_hint` | `annotation_hint` |
| `Evidence format` prompt text | `Annotation format` prompt text |

## Required Invariants

- Active task outputs emit `answer_gt`, `annotation_gt`, and
  `trace_payload.projected_annotation`.
- Prompt examples in answer-plus-annotation mode use `"annotation"` and
  `"answer"` only.
- Reward inputs require `answer_gt`, `annotation_gt`, and a v0 reward contract.
- Current reward scoring rejects stale `"evidence"` responses in
  answer-plus-annotation mode.
- Review sidecars and exports use annotation fields only.
- Generated review/calibration artifacts from before this migration must be
  deleted or regenerated, not reused.

## Review Commands

Run the active stale-term scan while excluding this historical note and
historical model outputs:

```bash
rg -n "answer_or_evidence|answer_and_evidence|prompt_answer_and_evidence|ground_truth_answer_and_evidence|projected_evidence|evidence_gt|evidence_hint|Evidence format|\\\"evidence\\\"|\\bevidence\\b|\\bEvidence\\b" \
  CONTRIBUTING.md assets/charts/maps/licenses/NATURAL_EARTH_PUBLIC_DOMAIN.md paper/trace_rlvr_experiment_plan.md \
  rlvr/tests/test_trace_reward.py rlvr/tests/test_trace_validation.py trace rlvr/verl rlvr/examples rlvr/scripts \
  docs scripts tests configs prompts review AGENTS.md \
  --hidden -g '!**/.git/**' -g '!rlvr/outputs/**' -g '!docs/workflows/ANNOTATION_CONTRACT_MIGRATION.md' -g '!**/__pycache__/**'
```

Run focused contract tests:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest rlvr/tests/test_trace_reward.py rlvr/tests/test_trace_validation.py tests/test_reward_scoring.py -q
```

Ignored/generated artifact directories should also be clean:

```bash
rg -n "evidence|Evidence|answer\\+evidence|answer/evidence|answer_and_evidence|evidence_gt|trace_evidence" \
  logs samples rlvr/dataset/train rlvr/wandb review --hidden -g '!**/.git/**'
```

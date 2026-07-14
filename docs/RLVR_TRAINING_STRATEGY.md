# Tentative RLVR Training Strategy

This note records the TRACE RLVR training strategy. It explains why the current
run is staged and what signals matter. Operational commands live in
`docs/workflows/RLVR_TRAINING_RUNBOOK.md`.

## Reference: Vero

The closest public recipe we have reviewed is:

- Paper: `Vero: An Open RL Recipe for General Visual Reasoning`
- arXiv: `https://arxiv.org/abs/2604.04917`
- Local copy: `review/papers/Vero_2604.04917.pdf`

Reported Vero setup:

| item | value |
| --- | --- |
| main dataset | `Vero-600K` |
| source coverage | 59 datasets selected from 250+ candidates |
| category mix | 6 categories, 100K samples each |
| main RL steps | 2,000 |
| framework | VeRL |
| algorithm | GSPO-style RL |
| effective train batch | 256 prompts |
| rollouts per prompt | 8 |
| learning rate | `1e-6` |
| KL coefficient | 0 |

Vero's main result is that broad, uniformly mixed RL data with task-routed
rewards improves several base models by roughly 3.6-5.3 average VeroEval points.
The paper also reports useful partial-scale signals:

- a 100K mixed-task run gives positive transfer across categories;
- full 600K training improves beyond the 100K checkpoint;
- single-category RL often transfers poorly and can harm unrelated categories;
- task-routed rewards outperform a generic `math_verify` reward;
- open-ended instruction-following data is needed to avoid degrading visual chat.

TRACE should borrow these high-level lessons, not copy Vero's exact data or
response-length settings. TRACE has programmatic generators, typed answers,
typed annotation contracts, and task-specific verifiers, so its data can be
sampled online or materialized deterministically from seeds.

## TRACE Training Objective

TRACE responses should include reasoning plus the structured payload selected
for that task by
`docs/workflows/RLVR_TASK_SUPERVISION_POLICY.md`. Answer-only tasks end with:

```text
<think>
Reasoning over the image and task.
</think>
<answer>
{"answer": ...}
</answer>
```

Tasks whose natural supervision includes grounding end with:

```text
<think>
Grounded reasoning over the image and task.
</think>
<answer>
{"answer": ..., "annotation": ...}
</answer>
```

The final payload is verifier-facing. A task uses one stable supervision mode;
different tasks in one scene may use different modes. The reasoning section is
still part of the training target because the model should learn to solve the
visual reasoning problem, not merely emit a short answer object.

Reward components should be logged separately:

- `answer_reward`
- `annotation_reward`
- `format_reward`
- `combined_reward`
- JSON/format validity
- empty or missing annotation rate
- truncation/overlong rate
- response length statistics

Do not use training reward alone to choose the recipe. Use a fixed held-out
TRACE evaluation set and compare answer accuracy, annotation score, invalid
output rate, and per-domain regressions.

## Initial Reward Ablation

The first ablation should test reward composition, not every annotation reward
formula. Per-annotation defaults should be good, monotonic, and inspectable, but
not exhaustively tuned at this stage.

Candidate reward modes:

| run | reward composition | purpose |
| --- | --- | --- |
| A | answer only | baseline solving signal |
| B | 0.8 answer / 0.2 annotation | conservative grounding pressure |
| C | 0.5 answer / 0.5 annotation | stronger grounding pressure |

Annotation-only can be added later as a diagnostic, but it is unlikely to be a
final recipe and should not consume the first ablation budget unless there is a
specific failure mode to investigate.

The ablation should use the full intended TRACE task distribution if possible.
Reducing task scope or rollouts can make the selected reward recipe fail to
transfer to the real run.

Preferred initial settings:

| item | tentative value |
| --- | --- |
| base model | `Qwen/Qwen2.5-VL-3B-Instruct` |
| training data | `maveryn/trace@train` (`900` tasks x `256` samples = `230,400` rows) |
| validation data | `maveryn/trace@validation` (`100` held-out tasks x `25` samples = `2,500` rows) |
| effective batch | 256 prompts/update |
| rollouts per prompt | 8 |
| learning rate | start near `1e-6`, adjust only after instability signals |
| max response tokens | 4096 for ablation |
| ablation checkpoints | 50, 100, 200, optional 250 |

The ablation window is adaptive:

- step 50: smoke checkpoint; kill only hard failures;
- step 100: early comparison; kill obvious collapse;
- step 200: normal decision point;
- step 250: optional tie-breaker if reward curves are still separating.

At batch 256 over the split-v1 `900` train tasks, prompt exposure is:

| steps | prompts seen | prompts/task |
| ---: | ---: | ---: |
| 50 | 12.8K | 14 |
| 100 | 25.6K | 28 |
| 200 | 51.2K | 57 |
| 250 | 64.0K | 71 |

These runs are not expected to give per-task conclusions. They are meant to
compare aggregate behavior by domain, answer type, annotation type, and output
validity.

## Continuing the Winning Run

The winning ablation checkpoint should become the prefix of the real training
run. Do not throw it away and restart unless the ablation itself was only a
smoke/debug pass.

Tentative continuation if targeting 1000 total steps:

| phase | steps | response cap | evaluation |
| --- | ---: | ---: | --- |
| ablation | 0-200/250 | 4096 | 50, 100, 200, optional 250 |
| stabilize winner | 200/250-500 | 4096 | every 100 steps |
| longer reasoning | 500-1000 | 8192 | every 100 steps |

If the final budget is closer to 500 total steps, keep the response cap at 4096
unless truncation statistics show that the model is consistently hitting the
limit.

Do not vary response length across reward-weight ablation candidates. That would
confound the reward comparison. Length changes are acceptable after selecting a
winning reward composition and resuming from that checkpoint.

## Evaluation Cadence

Avoid full evaluation every 10-20 training steps. It is too expensive and tends
to encourage overreacting to noise.

Use cheap training-time telemetry every 10-20 steps:

- combined reward;
- answer reward;
- annotation reward;
- format and JSON validity;
- invalid answer rate;
- missing annotation rate;
- response length mean/p90/p95;
- truncation rate;
- entropy/KL if available;
- sampled reward by domain if cheap.

Use held-out evaluation only at sparse checkpoints:

- ablation: 50, 100, 200, optional 250;
- main continuation: every 100 steps.

Held-out eval should be fixed-seed and stratified by:

- domain;
- answer type;
- annotation type;
- task difficulty if available;
- task/query contract.

Run external benchmarks before training and again at the main ablation decision
checkpoint. The current fixed subset is `external_eval_v1`: `1000` rows each
from `chartqapro`, `charxivreason`, `mathvista`, `mmmu_pro_vision`, `countqa`,
`game_qa_lite`, `blink`, and pooled `screenspotpro`. The manifests live under
`benchmark/subsets/external_eval_v1/` and are mirrored privately at
`maveryn/trace-external-eval-subsets`.

## Data Sampling

TRACE can sample from programmatic generators instead of relying only on a fixed
static dataset. The clean default sampler is:

```text
sample task -> sample query/params/seed -> generate instance
```

The first ablation should use the same sampler family intended for real
training. Candidate sampling policies:

1. task-uniform globally;
2. domain-balanced, then task-uniform inside each domain;
3. hybrid: half global task-uniform, half domain-balanced.

Task-uniform is the cleanest baseline. Domain-balanced may be better if one
domain has many more tasks and would otherwise dominate the training signal.

For rough sizing with split-v1's `900` train tasks:

| total steps | batch | prompts seen | prompts/task |
| ---: | ---: | ---: | ---: |
| 500 | 256 | 128K | 142 |
| 900 | 256 | 230K | 256 |
| 1000 | 256 | 256K | 284 |
| 2000 | 256 | 512K | 569 |

With 8 rollouts per prompt, multiply prompts seen by 8 to estimate generated
responses. A 1000-step run at batch 256 consumes about 2.05M rollouts.

## Annotation Reward Defaults

Do not spend the first ablation budget comparing low-level annotation formulas.
Start with stable defaults:

- `bbox`: soft IoU-style score;
- `bbox_set`: Hungarian matching over boxes;
- `point`: distance-based score normalized by visual scale;
- `point_set`: Hungarian matching over points;
- `segment`: endpoint-pair distance, with reversed endpoints allowed when the
  contract says the segment is unordered;
- `segment_set`: Hungarian matching over segment scores;
- map annotations: score by key, missing keys score 0.

These defaults can be revisited only after answer/annotation reward composition
is understood.

## Current Open Decisions

- Whether the next run uses task-uniform or domain-balanced sampling.
- Whether the next task-conditioned run should test an additional reward
  recipe after the first additive 0.50 comparison. The complete task mapping
  and assignment rules live in
  `docs/workflows/RLVR_TASK_SUPERVISION_POLICY.md`.

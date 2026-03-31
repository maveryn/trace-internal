# Cellwise GRPO in RLVR (Tesserae)

This note documents how the optional cellwise reward mode is implemented in the RLVR trainer so we can revisit the design later.

## Goal
Map per-cell correctness of a Tesserae grid answer onto response tokens, then use GRPO with token-level advantages. This avoids giving the same advantage to all response tokens when only some cells are correct.

## Where it is implemented
- Trainer: `rlvr/verl/trainer/ray_trainer.py`
- Parsing helpers: `rlvr/verl/utils/cellwise_reward.py`
- Config flag: `rlvr/verl/trainer/config.py` (`AlgorithmConfig.reward_mode`)

## Implementation summary (code mapping)
- Entry point: `compute_cellwise_advantage(...)` in `rlvr/verl/trainer/ray_trainer.py`
- Per prompt group (`uid`):
  - Parse ground truth into a binary grid via `to_binary_grid(...)`
  - Decode response tokens, prefer the last `\\boxed{...}` region
  - Parse response grid and per-cell char spans with `parse_matrix_with_cell_char_spans(...)`
  - Map char spans to token spans with `char_spans_to_token_spans(...)`
  - Compute per-cell correctness (1/0) and subtract the per-cell mean across rollouts
  - Fill token-level advantages using the per-cell spans
- KL handling: when `use_kl_loss` is off, KL penalty is subtracted from the token-level advantages (same intent as scalar GRPO)

## Activation (config)
Set:
```
algorithm:
  adv_estimator: grpo
  reward_mode: cellwise
```

If `reward_mode` is not set (or is `scalar`), the behavior is identical to the previous GRPO path.

## Pipeline overview
The cellwise path runs right after reward is computed and before the actor update:

1) Reward: the reward function still returns a scalar overall score placed on the last response token (same as before).
2) Parse ground truth: the trainer expects binary grid ground truth (0/1) in `non_tensor_batch["ground_truth"]`.
3) Decode responses: for each rollout response, decode response tokens to a string.
4) Extract boxed answer: if a `\\boxed{...}` region exists, only its content is parsed.
5) Parse grid + spans: parse the text into a rows x cols matrix of 0/1, and capture char spans per cell.
6) Map to token spans: map each cell char span to a response token span using `offset_mapping`.
7) Cellwise rewards: each cell gets `1` if it matches the ground truth, else `0`.
8) GRPO normalization: for each prompt group (`uid`), compute mean per cell across rollouts and subtract it to form cellwise advantages.
9) Build per-token advantage: fill each cell's token span with the corresponding cellwise advantage.

The result is a per-token `advantages` tensor (same shape as `responses`) used by the existing PPO loss.

## Fallback behavior
The implementation is defensive so training does not stall on parsing issues:

- If the ground truth is not a binary grid, the whole prompt group falls back to scalar GRPO.
- If no rollout in a group can be parsed/mapped, the entire group falls back to scalar GRPO.
- If a particular rollout fails parsing/mapping but others succeed, that rollout gets a broadcast scalar advantage (mean of its cellwise advantages).

These fallbacks keep behavior stable and avoid NaNs.

## Potential pitfalls (if reward looks flat)
- Output format does not match the strict grid parser:
  - The parser extracts exactly `rows * cols` digits (`0`/`1`) from the boxed region. Extra digits or non-binary tokens will make parsing fail.
- Tokenization mismatch:
  - The implementation re-encodes the decoded response and requires token ids to match exactly. If the tokenizer is not fully reversible, mapping fails.
- Most rollouts in a group fail parsing:
  - Cellwise advantages may be dominated by zeros; check the metrics below.
- Model is not producing boxed answers:
  - Parsing still tries the full response, but if the output contains extra digits, parsing often fails.

## Debug checklist
- Monitor metrics:
  - `reward/cellwise_parse_fail_rate`
  - `reward/cellwise_tokenize_fail_rate`
  - `reward/cellwise_mapping_fail_rate`
  - `reward/cellwise_scalar_fallback_groups`
- Ensure prompt asks for a strict matrix-only answer (digits and separators only).
- Confirm `reward_mode: cellwise` and `adv_estimator: grpo`.

## KL handling
When `use_kl_loss` is disabled, KL is applied in the reward path by subtracting it from `token_level_rewards`. In cellwise mode, the trainer applies the same KL penalty to the token-level advantages so the behavior matches the scalar path.

## Metrics
The following metrics are emitted to help evaluate parsing success and signal quality:
- `reward/cellwise_invalid_rate`
- `reward/cellwise_parse_fail_rate`
- `reward/cellwise_tokenize_fail_rate`
- `reward/cellwise_mapping_fail_rate`
- `reward/cellwise_cell_accuracy`
- `reward/cellwise_scalar_fallback_groups`

## Parsing details
Parsing helpers live in `rlvr/verl/utils/cellwise_reward.py`:
- `to_binary_grid`: accepts lists/tuples or numpy arrays; rejects non-0/1 values.
- `extract_boxed_span`: finds the last `\\boxed{...}` region for parsing.
- `parse_matrix_with_cell_char_spans`: extracts exactly `rows * cols` binary digits from the answer string and records char spans.
- `char_spans_to_token_spans`: maps char spans to token spans using tokenizer offsets.

The parser is intentionally strict to avoid ambiguous token mappings.

## Notes and limitations
- Supported only for GRPO: `reward_mode: cellwise` currently requires `adv_estimator: grpo`.
- Binary grid only: assumes answers are 0/1 matrices (Tesserae default).
- Output format sensitivity: if the model emits extra text inside the boxed answer, parse may fail or spans may be wrong. A strict output format is strongly recommended.

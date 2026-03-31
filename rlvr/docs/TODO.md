# Cellwise GRPO: Implementation Plan (Tesserae)

## Goal
Move from **one scalar reward per grid** to **per‑cell advantages mapped onto answer tokens**. Each rollout is rewarded for the cells it gets right *relative to its peers*, not just for the total count.

This fixes the “13/25 vs 12/25” issue: rollouts are credited for *which* cells they solve, not only the average score.

---

## Current pipeline (scalar reward)
**Where it happens today (RLVR):**
- Dataset → prompts + ground truth: `rlvr/verl/utils/dataset.py`
- Reward function (scalar): `rlvr/examples/reward_function/reward_tesserae.py`
- Reward manager (token scores, last token only): `rlvr/verl/workers/reward/function.py`
- Advantage (GRPO): `rlvr/verl/trainer/core_algos.py`
- Actor loss uses `advantages`: `rlvr/verl/workers/actor/dp_actor.py`

**Behavior today:**
- Reward is a **single scalar per response**.
- Reward tensor is token‑level but only the *last response token* is nonzero.
- GRPO normalizes the scalar reward across rollouts and broadcasts the same advantage to all response tokens.

---

## Target pipeline (cellwise advantages)
1) Parse output into a matrix **and** track per‑cell text spans.
2) Map each cell’s char span → token span.
3) Compute per‑cell correctness and per‑cell advantages across rollouts.
4) Build a **per‑token advantage vector** using the cell‑token spans.
5) Run GRPO update exactly as before, but now `advantages` is per‑token instead of a single broadcast value.

---

## Step‑by‑step plan

### 1) Enforce a canonical matrix‑only output format
You only get clean cell‑token credit if the output is strictly parseable.

**Recommended output format** (tokenizer‑friendly):
- Exactly `rows` lines
- Each line has exactly `cols` integers
- Integers separated by single spaces
- No extra text

Example for rows=3, cols=4:
```
0 1 0 0
1 0 1 0
0 0 0 1
```

**Prompt changes** (choose one):
- Strict: “Return ONLY the answer grid as rows lines of cols integers separated by single spaces. No extra text.”
- If reasoning is required: “Put final answer grid after `FINAL:` and nothing after it.” Then parse only after `FINAL:`.

**Where to change:**
- Dataset template (e.g. `rlvr/examples/format_prompt/math.jinja`) or task prompt definitions.

---

### 2) Parse matrix + capture per‑cell char spans
Create a parser:
```
parse_matrix_with_cell_char_spans(text, rows, cols) ->
  pred: rows x cols matrix (or None)
  cell_char_spans: rows x cols of (char_start, char_end)
  is_valid: bool
```

**Behavior:**
- Accept extra whitespace and trailing newline
- Reject wrong row/col count
- Reject non‑integers

**Implementation detail:**
- Scan the original string with a character index so spans match the real text.

**Suggested location:**
- New helper: `rlvr/verl/utils/reward_cellwise.py`

---

### 3) Map char spans → token spans
You must assign a token range to each cell’s text span.

```
cell_token_spans = char_spans_to_token_spans(
  text=answer_text,
  token_offsets=tokenizer(answer_text, return_offsets_mapping=True).offset_mapping,
  cell_char_spans=cell_char_spans
)
```

**Mapping rule:**
- For each cell span [a,b), include all tokens whose offset [ta,tb) overlaps.
- Use `[tok_start, tok_end)` half‑open ranges.

**Edge cases:**
- If no token overlaps (rare), mark invalid and skip or assign to nearest token.

**Where to compute:**
- Prefer inside training (see Step 7) where tokenizer is available.

---

### 4) Compute per‑cell rewards per rollout
For each rollout `k`:
```
correct[k,i,j] = 1 if pred[k,i,j] == gt[i,j] else 0
```

Optional debiasing:
- Binary case (K=2): `r_cell = 2*correct - 1` (expected 0 under random guessing)
- General K: `r_cell = (correct - 1/K) / (1 - 1/K)`

**Parse failures:**
- Simple mode: all cells incorrect (r_cell=0)
- Optional: add a separate formatting penalty

---

### 5) Normalize cellwise across rollouts (GRPO‑style)
For each prompt group (same `uid`), compute per‑cell baselines:
```
mu[i,j]    = mean_k r_cell[k,i,j]
std[i,j]   = std_k  r_cell[k,i,j]
```

**Option A (recommended for stability):**
```
adv_cell[k,i,j] = r_cell[k,i,j] - mu[i,j]
```

**Option B (z‑score):**
```
adv_cell[k,i,j] = (r_cell[k,i,j] - mu[i,j]) / max(std[i,j], min_std)
```

Optional: leave‑one‑out baseline:
```
mu_excl[k,i,j] = mean_{k'!=k} r_cell[k',i,j]
adv_cell = r_cell - mu_excl
```

---

### 6) Build per‑token advantages
For each rollout `k`, create a vector `adv_tok[k, t]` of length `T_k`:

```
adv_tok = zeros(T_k)
for each cell (i,j):
  (s,e) = cell_token_spans[k][i][j]
  adv_tok[s:e] = adv_cell[k,i,j]
```

- Separator tokens (spaces/newlines) often fall outside cell spans → keep them at 0.
- If extra text exists, keep its tokens at 0 or apply a small penalty.

---

### 7) Integrate into the current codebase
You want `advantages` to be **per‑token** instead of broadcast. Two practical options:

#### Option A (least invasive): compute per‑token advantages in the trainer
**Where:** `rlvr/verl/trainer/ray_trainer.py` right after reward is computed and before `compute_advantage(...)` is called.

Steps:
1. Decode each response string from `data.batch["responses"]` (token ids) using the trainer’s tokenizer.
2. Parse + map spans (Steps 2–3) using ground truth from `data.non_tensor_batch["ground_truth"]`.
3. Compute `adv_tok` (Steps 4–6) grouped by `uid` (already in `data.non_tensor_batch["uid"]`).
4. **Set**:
   - `batch.batch["advantages"] = adv_tok`
   - `batch.batch["returns"] = adv_tok` (GRPO uses returns same as adv)
5. **Skip** `compute_advantage(...)` when `reward_mode == "cellwise"`.

This avoids changing core GRPO logic and keeps PPO loss unchanged.

#### Option B: extend GRPO estimator
Add a new estimator (e.g. `grpo_cellwise`) in `rlvr/verl/trainer/core_algos.py` that uses cellwise metadata from `DataProto`. This requires passing parsed spans + r_cell through `DataProto`, which is more intrusive.

**Recommendation:** Start with Option A.

---

### 8) Config knobs (for A/B testing)
Add a config block:
```
reward_mode: "cellwise"  # or "scalar"
cellwise:
  debias_k: 2
  normalization: "center"  # or "zscore"
  min_std: 0.01
  adv_clip: 5.0
  invalid_parse_mode: "all_wrong"  # or "neg_all"
  answer_region: "entire_output"   # or "after_FINAL"
```

---

### 9) Logging (add immediately)
Track per‑batch or per‑step:
- mean cell accuracy (overall + per prompt group)
- parse failure rate
- adv_cell stats (mean/std/max)
- disagreement rate across rollouts

---

### 10) Tests (minimal set)
Create a deterministic test with rows=2, cols=2, N=3.

GT:
```
1 0
0 1
```

Rollouts:
- k0: two correct cells (one diagonal)
- k1: the other two correct cells
- k2: none

Assertions:
- Scalar reward ranks k0 == k1 > k2
- Cellwise adv gives k0 positive on its correct cells, k1 positive on its correct cells, k2 negative everywhere
- Token spans map to correct tokens
- Parser rejects wrong shape
- Parse failure path applied correctly

---

### 11) Performance note
This does **not** increase backprop cost by `rows*cols`.
- Still **one forward/backward per rollout**.
- Extra work is CPU‑side bookkeeping: O(N * rows * cols) + token mapping.

---

## Quick “next action” checklist
- [ ] Add strict output format to prompts
- [ ] Implement `parse_matrix_with_cell_char_spans`
- [ ] Implement `char_spans_to_token_spans`
- [ ] Add cellwise adv computation in `ray_trainer.py` (Option A)
- [ ] Add config + logging + tests

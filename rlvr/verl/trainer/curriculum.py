# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from torch.utils.data import Sampler


def load_bucket_order(path: str) -> list[str]:
    bucket_order_path = Path(path)
    with bucket_order_path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError(f"Curriculum bucket order must be a non-empty JSON list: {bucket_order_path}")
    bucket_order = [str(item) for item in data]
    if len(bucket_order) != len(set(bucket_order)):
        raise ValueError(f"Duplicate bucket ids found in {bucket_order_path}")
    return bucket_order


def build_bucket2indices(bucket_values: Iterable[Any]) -> dict[str, list[int]]:
    bucket2indices: dict[str, list[int]] = defaultdict(list)
    for idx, raw_bucket_id in enumerate(bucket_values):
        bucket_id = str(raw_bucket_id or "").strip()
        if not bucket_id:
            raise ValueError(f"Missing bucket_id_str at dataset row index={idx}")
        bucket2indices[bucket_id].append(idx)
    return dict(bucket2indices)


def _validate_bucket_ids(bucket2indices: dict[str, list[int]], bucket_order: list[str]) -> None:
    bucket_order_set = set(bucket_order)
    missing_buckets = [bucket for bucket in bucket_order if bucket not in bucket2indices]
    if missing_buckets:
        raise ValueError(
            "Buckets from curriculum order are missing in dataset: "
            + ", ".join(sorted(missing_buckets)[:10])
            + (" ..." if len(missing_buckets) > 10 else "")
        )
    extra_buckets = [bucket for bucket in bucket2indices.keys() if bucket not in bucket_order_set]
    if extra_buckets:
        raise ValueError(
            "Dataset contains buckets not present in curriculum order: "
            + ", ".join(sorted(extra_buckets)[:10])
            + (" ..." if len(extra_buckets) > 10 else "")
        )
    for bucket_id in bucket_order:
        if len(bucket2indices[bucket_id]) == 0:
            raise ValueError(f"Bucket has zero rows in dataset: {bucket_id}")


def _bucket_sort_key(bucket_id: str) -> tuple[int, int, int] | tuple[int, str]:
    pieces = bucket_id.split("-", 1)
    if len(pieces) != 2:
        return (1, bucket_id)
    try:
        return (0, int(pieces[0]), int(pieces[1]))
    except ValueError:
        return (1, bucket_id)


def load_bucket_accuracy_map(path: str) -> dict[str, float]:
    stats_path = Path(path)
    with stats_path.open("r", encoding="utf-8") as fp:
        data = json.load(fp)

    out: dict[str, float] = {}

    def _add(bucket_id: Any, value: Any) -> None:
        bucket = str(bucket_id or "").strip()
        if not bucket:
            return
        try:
            acc = float(value)
        except (TypeError, ValueError):
            return
        if not math.isfinite(acc):
            return
        out[bucket] = max(0.0, min(1.0, acc))

    def _from_entry(entry: Any) -> None:
        if not isinstance(entry, dict):
            return
        bucket_id = entry.get("bucket_id_str")
        if bucket_id is None:
            return
        if "accuracy" in entry:
            _add(bucket_id, entry["accuracy"])
            return
        if "acc" in entry:
            _add(bucket_id, entry["acc"])
            return
        if "mu" in entry:
            _add(bucket_id, entry["mu"])
            return

    if isinstance(data, list):
        for entry in data:
            _from_entry(entry)
    elif isinstance(data, dict):
        if "buckets" in data and isinstance(data["buckets"], list):
            for entry in data["buckets"]:
                _from_entry(entry)
        else:
            for bucket_id, value in data.items():
                if isinstance(value, dict):
                    if "accuracy" in value:
                        _add(bucket_id, value["accuracy"])
                    elif "acc" in value:
                        _add(bucket_id, value["acc"])
                    elif "mu" in value:
                        _add(bucket_id, value["mu"])
                else:
                    _add(bucket_id, value)

    if len(out) == 0:
        raise ValueError(f"No bucket accuracy values found in {stats_path}")
    return out


class RankUnlockBucketSampler(Sampler[int]):
    """
    Bucket-aware sampler for offline-fixed curriculum.

    Sampling policy:
    1) sample one bucket uniformly from currently unlocked prefix,
    2) sample one row uniformly from that bucket (with replacement).
    """

    def __init__(
        self,
        *,
        bucket2indices: dict[str, list[int]],
        bucket_order: list[str],
        num_samples: int,
        seed: int = 0,
    ):
        if num_samples <= 0:
            raise ValueError(f"num_samples must be positive, got {num_samples}")
        if len(bucket_order) == 0:
            raise ValueError("bucket_order must be non-empty")

        _validate_bucket_ids(bucket2indices, bucket_order)

        self.bucket2indices = bucket2indices
        self.bucket_order = list(bucket_order)
        self.num_samples = int(num_samples)
        self.seed = int(seed)

        self._rng = random.Random(self.seed)
        self._current_step = 1
        self._total_steps: int | None = None
        self._draw_count = 0

        self._variant_ids = set()
        self._count_bins = set()
        for bucket_id in self.bucket_order:
            task_variant_id, count_bin = self._parse_bucket_id(bucket_id)
            self._variant_ids.add(task_variant_id)
            self._count_bins.add(count_bin)
        self._k_min = self._compute_k_min()

    @staticmethod
    def _parse_bucket_id(bucket_id: str) -> tuple[int, int]:
        pieces = bucket_id.split("-", 1)
        if len(pieces) != 2:
            raise ValueError(f"Invalid bucket id format, expected '<task_variant_id>-<count_bin>': {bucket_id}")
        try:
            return int(pieces[0]), int(pieces[1])
        except ValueError as exc:
            raise ValueError(f"Invalid numeric bucket id: {bucket_id}") from exc

    def _compute_k_min(self) -> int:
        seen_variants: set[int] = set()
        seen_count_bins: set[int] = set()
        for idx, bucket_id in enumerate(self.bucket_order, start=1):
            task_variant_id, count_bin = self._parse_bucket_id(bucket_id)
            seen_variants.add(task_variant_id)
            seen_count_bins.add(count_bin)
            if len(seen_variants) == len(self._variant_ids) and len(seen_count_bins) == len(self._count_bins):
                return idx
        return len(self.bucket_order)

    @property
    def total_buckets(self) -> int:
        return len(self.bucket_order)

    @property
    def k_min(self) -> int:
        return self._k_min

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def current_k(self) -> int:
        return self._compute_current_k()

    def set_total_steps(self, total_steps: int) -> None:
        total_steps = int(total_steps)
        if total_steps <= 0:
            raise ValueError(f"total_steps must be positive, got {total_steps}")
        self._total_steps = total_steps

    def set_step(self, step: int) -> None:
        step = int(step)
        if step <= 0:
            step = 1
        self._current_step = step

    def _compute_current_k(self) -> int:
        b_total = self.total_buckets
        if self._total_steps is None or self._total_steps <= 1:
            return self._k_min

        progress = (self._current_step - 1) / max(1, self._total_steps - 1)
        progress = max(0.0, min(1.0, progress))
        k_float = self._k_min + progress * (b_total - self._k_min)
        return max(self._k_min, min(b_total, int(math.ceil(k_float))))

    def __iter__(self):
        for _ in range(self.num_samples):
            current_k = self._compute_current_k()
            bucket_idx = self._rng.randrange(current_k)
            bucket_id = self.bucket_order[bucket_idx]
            dataset_indices = self.bucket2indices[bucket_id]
            choice_idx = self._rng.randrange(len(dataset_indices))
            self._draw_count += 1
            yield dataset_indices[choice_idx]

    def __len__(self) -> int:
        return self.num_samples

    def state_dict(self) -> dict[str, Any]:
        return {
            "current_step": int(self._current_step),
            "total_steps": int(self._total_steps) if self._total_steps is not None else None,
            "draw_count": int(self._draw_count),
            "rng_state": self._rng.getstate(),
        }

    def load_state_dict(self, state_dict: dict[str, Any]) -> None:
        if "current_step" in state_dict:
            self.set_step(int(state_dict["current_step"]))
        if "total_steps" in state_dict and state_dict["total_steps"] is not None:
            self.set_total_steps(int(state_dict["total_steps"]))
        if "draw_count" in state_dict:
            self._draw_count = int(state_dict["draw_count"])
        if "rng_state" in state_dict:
            self._rng.setstate(state_dict["rng_state"])


class SelfPacedEMABucketSampler(Sampler[int]):
    """
    Self-paced bucket sampler with online EMA competence.

    Sampling policy:
    1) sample bucket by weight w_b = (mu_b * (1 - mu_b) + eps) ** beta,
    2) sample one row uniformly from that bucket (with replacement).
    """

    def __init__(
        self,
        *,
        bucket2indices: dict[str, list[int]],
        num_samples: int,
        seed: int = 0,
        bucket_order: list[str] | None = None,
        mu_init: dict[str, float] | None = None,
        alpha0: float = 0.995,
        eps_floor: float | None = None,
        beta: float = 2.0,
    ):
        if num_samples <= 0:
            raise ValueError(f"num_samples must be positive, got {num_samples}")
        if alpha0 <= 0.0 or alpha0 >= 1.0:
            raise ValueError(f"alpha0 must be in (0, 1), got {alpha0}")
        if beta <= 0.0:
            raise ValueError(f"beta must be > 0, got {beta}")
        if len(bucket2indices) == 0:
            raise ValueError("bucket2indices must be non-empty")

        if bucket_order is None:
            bucket_order = sorted(bucket2indices.keys(), key=_bucket_sort_key)
        else:
            if len(bucket_order) == 0:
                raise ValueError("bucket_order must be non-empty")
            if len(bucket_order) != len(set(bucket_order)):
                raise ValueError("bucket_order contains duplicate bucket ids")
            _validate_bucket_ids(bucket2indices, bucket_order)

        total_buckets = len(bucket_order)
        if eps_floor is None:
            eps_floor = 0.0
        if eps_floor < 0.0:
            raise ValueError(f"eps_floor must be >= 0, got {eps_floor}")

        self.bucket2indices = bucket2indices
        self.bucket_order = list(bucket_order)
        self.num_samples = int(num_samples)
        self.seed = int(seed)
        self.alpha0 = float(alpha0)
        self.eps_floor = float(eps_floor)
        self.beta = float(beta)

        self._rng = random.Random(self.seed)
        self._draw_count = 0
        self._update_count = 0

        self._mu: dict[str, float] = {}
        self._seen: dict[str, int] = {}
        mu_init = mu_init or {}
        for bucket_id in self.bucket_order:
            if len(self.bucket2indices[bucket_id]) == 0:
                raise ValueError(f"Bucket has zero rows in dataset: {bucket_id}")
            init_value = float(mu_init.get(bucket_id, 0.5))
            self._mu[bucket_id] = self._clip_mu(init_value)
            self._seen[bucket_id] = 0

        self._probs: list[float] = []
        self._refresh_probs()

    @staticmethod
    def _clip_mu(value: float) -> float:
        # Numerical guardrail to avoid exact 0/1 collapse.
        return max(1e-4, min(1.0 - 1e-4, float(value)))

    @property
    def total_buckets(self) -> int:
        return len(self.bucket_order)

    @property
    def draw_count(self) -> int:
        return self._draw_count

    @property
    def update_count(self) -> int:
        return self._update_count

    @property
    def mu_values(self) -> list[float]:
        return [self._mu[bucket_id] for bucket_id in self.bucket_order]

    @property
    def prob_values(self) -> list[float]:
        return list(self._probs)

    def get_mu(self, bucket_id: str) -> float:
        return float(self._mu[bucket_id])

    def get_prob(self, bucket_id: str) -> float:
        idx = self.bucket_order.index(bucket_id)
        return float(self._probs[idx])

    def _refresh_probs(self) -> None:
        weights = []
        for bucket_id in self.bucket_order:
            mu = self._mu[bucket_id]
            base = mu * (1.0 - mu) + self.eps_floor
            weights.append(base ** self.beta)
        total_weight = float(sum(weights))
        if total_weight <= 0.0 or not math.isfinite(total_weight):
            uniform = 1.0 / float(len(weights))
            self._probs = [uniform for _ in weights]
            return
        self._probs = [float(w / total_weight) for w in weights]

    def update_from_prompt_rewards(self, prompt_bucket_ids: list[str], prompt_rewards: list[float]) -> None:
        if len(prompt_bucket_ids) != len(prompt_rewards):
            raise ValueError("prompt_bucket_ids and prompt_rewards must have same length")
        if len(prompt_bucket_ids) == 0:
            return

        bucket2reward_sum: dict[str, float] = defaultdict(float)
        bucket2count: dict[str, int] = defaultdict(int)

        for bucket_id_raw, reward_raw in zip(prompt_bucket_ids, prompt_rewards):
            bucket_id = str(bucket_id_raw)
            if bucket_id not in self._mu:
                continue
            reward = float(reward_raw)
            if not math.isfinite(reward):
                continue
            reward = max(0.0, min(1.0, reward))
            bucket2reward_sum[bucket_id] += reward
            bucket2count[bucket_id] += 1

        if len(bucket2count) == 0:
            return

        for bucket_id, n_bucket in bucket2count.items():
            rbar = bucket2reward_sum[bucket_id] / float(n_bucket)
            alpha_bucket = self.alpha0 ** int(n_bucket)
            updated = alpha_bucket * self._mu[bucket_id] + (1.0 - alpha_bucket) * rbar
            self._mu[bucket_id] = self._clip_mu(updated)
            self._seen[bucket_id] += int(n_bucket)

        self._update_count += 1
        self._refresh_probs()

    def __iter__(self):
        for _ in range(self.num_samples):
            bucket_id = self._rng.choices(self.bucket_order, weights=self._probs, k=1)[0]
            dataset_indices = self.bucket2indices[bucket_id]
            choice_idx = self._rng.randrange(len(dataset_indices))
            self._draw_count += 1
            yield dataset_indices[choice_idx]

    def __len__(self) -> int:
        return self.num_samples

    def state_dict(self) -> dict[str, Any]:
        return {
            "draw_count": int(self._draw_count),
            "update_count": int(self._update_count),
            "beta": float(self.beta),
            "mu": {bucket_id: float(self._mu[bucket_id]) for bucket_id in self.bucket_order},
            "seen": {bucket_id: int(self._seen[bucket_id]) for bucket_id in self.bucket_order},
            "rng_state": self._rng.getstate(),
        }

    def load_state_dict(self, state_dict: dict[str, Any]) -> None:
        if "draw_count" in state_dict:
            self._draw_count = int(state_dict["draw_count"])
        if "update_count" in state_dict:
            self._update_count = int(state_dict["update_count"])
        if "beta" in state_dict:
            try:
                beta_saved = float(state_dict["beta"])
                if beta_saved > 0.0 and abs(beta_saved - self.beta) > 1e-12:
                    print(
                        f"[curriculum] warning: checkpoint beta={beta_saved} differs from current beta={self.beta}; "
                        "using current config value."
                    )
            except Exception:
                pass
        if "mu" in state_dict and isinstance(state_dict["mu"], dict):
            for bucket_id, value in state_dict["mu"].items():
                if bucket_id in self._mu:
                    self._mu[bucket_id] = self._clip_mu(float(value))
        if "seen" in state_dict and isinstance(state_dict["seen"], dict):
            for bucket_id, value in state_dict["seen"].items():
                if bucket_id in self._seen:
                    self._seen[bucket_id] = int(value)
        if "rng_state" in state_dict:
            self._rng.setstate(state_dict["rng_state"])
        self._refresh_probs()

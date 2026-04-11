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
"""
PPO Trainer with Ray-based single controller.
This trainer supports model-agonistic model initialization with huggingface.
"""

import json
import os
import uuid
from collections import Counter
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Any, Optional, Type

import numpy as np
import ray
import torch
from ray.experimental.tqdm_ray import tqdm
from torchdata.stateful_dataloader import StatefulDataLoader
from transformers import PreTrainedTokenizer, ProcessorMixin

from ..protocol import DataProto, pad_dataproto_to_divisor, unpad_dataproto
from ..single_controller.base import Worker
from ..single_controller.ray import RayClassWithInitArgs, RayResourcePool, RayWorkerGroup
from ..single_controller.ray.base import create_colocated_worker_cls
from ..utils import torch_functional as VF
from ..utils.cellwise_reward import (
    char_spans_to_token_spans,
    extract_boxed_span,
    parse_matrix_with_cell_char_spans,
    to_binary_grid,
)
from ..utils.checkpoint import CHECKPOINT_TRACKER, find_latest_ckpt, remove_obsolete_ckpt
from ..utils.logger import Tracker
from ..utils.py_functional import convert_dict_to_str, timer, unflatten_dict
from ..utils.val_reward import compute_val_reward
from ..utils.seqlen_balancing import get_seqlen_balanced_partitions, log_seqlen_unbalance
from ..workers.fsdp_workers import FSDPWorker
from ..workers.reward import AutoRewardManager
from .config import PPOConfig
from .curriculum import RankUnlockBucketSampler, SelfPacedEMABucketSampler
from .core_algos import (
    AdvantageEstimator,
    FixedKLController,
    KLController,
    compute_advantage_return,
    compute_kl,
    get_kl_controller,
)
from .metrics import (
    compute_data_metrics,
    compute_length_metrics,
    compute_throughout_metrics,
    compute_timing_metrics,
    reduce_metrics,
)


class Role(IntEnum):
    """
    To create more roles dynamically, you can subclass Role and add new members
    """

    Actor = auto()
    Rollout = auto()
    ActorRollout = auto()
    Critic = auto()
    RefPolicy = auto()
    RewardModel = auto()
    ActorRolloutRef = auto()


@dataclass
class ResourcePoolManager:
    """
    Define a resource pool specification. Resource pool will be initialized first.
    """

    resource_pool_spec: dict[str, list[int]]
    mapping: dict[Role, str]
    resource_pool_dict: dict[str, RayResourcePool] = field(default_factory=dict)

    def create_resource_pool(self):
        """Create ray resource pools for distributed training."""
        for resource_pool_name, process_on_nodes in self.resource_pool_spec.items():
            # max_colocate_count means the number of WorkerGroups (i.e. processes) in each RayResourcePool
            # For FSDP backend, we recommend using max_colocate_count=1 that merge all WorkerGroups into one.
            # For Megatron backend, we recommend using max_colocate_count>1 that can utilize different WorkerGroup for different models
            resource_pool = RayResourcePool(
                process_on_nodes=process_on_nodes, use_gpu=True, max_colocate_count=1, name_prefix=resource_pool_name
            )
            self.resource_pool_dict[resource_pool_name] = resource_pool

        self._check_resource_available()

    def get_resource_pool(self, role: Role) -> RayResourcePool:
        """Get the resource pool of the worker."""
        return self.resource_pool_dict[self.mapping[role]]

    def get_num_gpus(self) -> int:
        """Get the number of gpus in this cluster."""
        return sum([n_gpus for process_on_nodes in self.resource_pool_spec.values() for n_gpus in process_on_nodes])

    def _check_resource_available(self):
        """Check if the resource pool can be satisfied in this ray cluster."""
        gpus_available = ray.available_resources().get("GPU", 0)
        gpus_required = self.get_num_gpus()
        if gpus_available < gpus_required:
            raise ValueError(f"Total available GPUs {gpus_available} is less than total desired GPUs {gpus_required}.")


def apply_kl_penalty(data: DataProto, kl_ctrl: KLController, kl_penalty="kl"):
    """Apply KL penalty to the token-level rewards."""
    token_level_scores = data.batch["token_level_scores"]
    batch_size = data.batch.batch_size[0]
    response_mask = data.batch["response_mask"]

    # compute kl between ref_policy and current policy
    kld = compute_kl(data.batch["old_log_probs"], data.batch["ref_log_probs"], kl_penalty=kl_penalty)
    kld = kld * response_mask  # (batch_size, response_length)

    data.batch["token_level_rewards"] = token_level_scores - kl_ctrl.kl_coef * kld

    current_kl = torch.mean(VF.masked_mean(kld, mask=response_mask, dim=-1)).item()
    metrics = {"actor/kl_penalty": current_kl, "actor/kl_coef": kl_ctrl.kl_coef}

    # According to https://github.com/huggingface/trl/blob/v0.11.0/trl/trainer/ppo_trainer.py#L880
    kl_ctrl.update(current_kl=current_kl, n_steps=batch_size)
    return data, metrics


def compute_advantage(data: DataProto, adv_estimator: AdvantageEstimator, gamma: float = 1.0, lam: float = 1.0):
    """Compute advantage estimates for policy optimization."""
    adv_inputs = {
        "token_level_rewards": data.batch["token_level_rewards"],
        "response_mask": data.batch["response_mask"],
        "index": data.non_tensor_batch["uid"],
        "gamma": gamma,
        "lam": lam,
    }
    if "values" in data.batch:
        adv_inputs["values"] = data.batch["values"]

    if "reward_baselines" in data.batch:
        adv_inputs["reward_baselines"] = data.batch["reward_baselines"]

    advantages, returns = compute_advantage_return(adv_estimator, **adv_inputs)
    data.batch["advantages"] = advantages
    data.batch["returns"] = returns
    return data


def compute_cellwise_advantage(
    data: DataProto,
    tokenizer: PreTrainedTokenizer,
    use_reference_policy: bool,
    use_kl_loss: bool,
    eps: float = 1e-6,
) -> tuple[DataProto, dict[str, float]]:
    """Compute per-token advantages by mapping cellwise correctness to response tokens."""
    response_ids = data.batch["responses"]
    response_mask = data.batch["response_mask"]
    token_level_rewards = data.batch["token_level_rewards"]
    device = response_ids.device

    batch_size, response_length = response_ids.shape
    advantages = torch.zeros((batch_size, response_length), dtype=torch.float32, device=device)
    returns = torch.zeros_like(advantages)

    uids = data.non_tensor_batch.get("uid")
    ground_truths = data.non_tensor_batch.get("ground_truth")
    if uids is None or ground_truths is None:
        raise ValueError("cellwise reward_mode requires `uid` and `ground_truth` in non_tensor_batch.")

    uid2indices: dict[Any, list[int]] = defaultdict(list)
    for idx, uid in enumerate(uids):
        uid2indices[uid].append(idx)

    special_ids = set(tokenizer.all_special_ids)
    parse_failures = 0
    tokenize_failures = 0
    mapping_failures = 0
    invalid_rollouts = 0
    total_rollouts = 0
    cell_correct = 0.0
    cell_total = 0.0
    scalar_fallback_groups = 0

    for indices in uid2indices.values():
        if len(indices) == 0:
            continue
        total_rollouts += len(indices)
        gt_grid = to_binary_grid(ground_truths[indices[0]])
        if gt_grid is None:
            scalar_fallback_groups += 1
            scores = token_level_rewards[indices].sum(dim=-1)
            mean = scores.mean()
            std = scores.std()
            norm_scores = (scores - mean) / (std + eps)
            group_returns = norm_scores.unsqueeze(-1) * response_mask[indices]
            advantages[indices] = group_returns
            returns[indices] = group_returns
            continue

        gt_array = np.array(gt_grid, dtype=np.int8)
        rows, cols = gt_array.shape
        group_size = len(indices)
        r_cells = np.zeros((group_size, rows, cols), dtype=np.float32)
        group_spans: list[Optional[list[list[tuple[int, int]]]]] = [None for _ in range(group_size)]
        group_valid = [False for _ in range(group_size)]
        group_lengths = [0 for _ in range(group_size)]

        for pos, idx in enumerate(indices):
            cur_len = int(response_mask[idx].sum().item())
            group_lengths[pos] = cur_len
            if cur_len <= 0:
                invalid_rollouts += 1
                continue

            resp_ids = response_ids[idx][:cur_len].tolist()
            non_special_positions = []
            non_special_ids = []
            for token_pos, token_id in enumerate(resp_ids):
                if token_id in special_ids:
                    continue
                non_special_positions.append(token_pos)
                non_special_ids.append(token_id)
            if not non_special_ids:
                invalid_rollouts += 1
                continue

            response_text = tokenizer.decode(non_special_ids, skip_special_tokens=True)
            boxed_span = extract_boxed_span(response_text)
            if boxed_span:
                parse_text = response_text[boxed_span[0] : boxed_span[1]]
                base_offset = boxed_span[0]
            else:
                parse_text = response_text
                base_offset = 0

            pred, cell_char_spans, ok = parse_matrix_with_cell_char_spans(
                parse_text, rows, cols, base_offset=base_offset
            )
            if not ok or pred is None or cell_char_spans is None:
                parse_failures += 1
                invalid_rollouts += 1
                continue

            try:
                tokenized = tokenizer(response_text, add_special_tokens=False, return_offsets_mapping=True)
            except Exception:
                tokenize_failures += 1
                invalid_rollouts += 1
                continue

            token_ids = tokenized.get("input_ids")
            offsets = tokenized.get("offset_mapping")
            if token_ids is None or offsets is None or token_ids != non_special_ids:
                tokenize_failures += 1
                invalid_rollouts += 1
                continue

            cell_token_spans = char_spans_to_token_spans(offsets, cell_char_spans)
            if cell_token_spans is None:
                mapping_failures += 1
                invalid_rollouts += 1
                continue

            cell_response_spans: list[list[tuple[int, int]]] = [[(0, 0) for _ in range(cols)] for _ in range(rows)]
            spans_valid = True
            for r in range(rows):
                for c in range(cols):
                    start_tok, end_tok = cell_token_spans[r][c]
                    if start_tok < 0 or end_tok <= start_tok or end_tok > len(non_special_positions):
                        spans_valid = False
                        break
                    resp_start = non_special_positions[start_tok]
                    resp_end = non_special_positions[end_tok - 1] + 1
                    if resp_end > cur_len:
                        spans_valid = False
                        break
                    cell_response_spans[r][c] = (resp_start, resp_end)
                if not spans_valid:
                    break

            if not spans_valid:
                mapping_failures += 1
                invalid_rollouts += 1
                continue

            pred_array = np.array(pred, dtype=np.int8)
            r_cells[pos] = (pred_array == gt_array).astype(np.float32)
            cell_correct += float(r_cells[pos].sum())
            cell_total += float(rows * cols)
            group_spans[pos] = cell_response_spans
            group_valid[pos] = True

        if not any(group_valid):
            scalar_fallback_groups += 1
            scores = token_level_rewards[indices].sum(dim=-1)
            mean = scores.mean()
            std = scores.std()
            norm_scores = (scores - mean) / (std + eps)
            group_returns = norm_scores.unsqueeze(-1) * response_mask[indices]
            advantages[indices] = group_returns
            returns[indices] = group_returns
            continue

        mean_cells = r_cells.mean(axis=0)
        adv_cells = r_cells - mean_cells
        for pos, idx in enumerate(indices):
            adv_tok = torch.zeros(response_length, dtype=torch.float32, device=device)
            cur_len = group_lengths[pos]
            if group_valid[pos] and group_spans[pos] is not None:
                for r in range(rows):
                    for c in range(cols):
                        span_start, span_end = group_spans[pos][r][c]
                        adv_tok[span_start:span_end] = float(adv_cells[pos, r, c])
            else:
                if cur_len > 0:
                    adv_scalar = float(adv_cells[pos].mean())
                    adv_tok[:cur_len] = adv_scalar
            advantages[idx] = adv_tok
            returns[idx] = adv_tok

    advantages = advantages * response_mask
    returns = returns * response_mask

    if use_reference_policy and not use_kl_loss and "token_level_scores" in data.batch:
        kl_penalty = data.batch["token_level_scores"] - data.batch["token_level_rewards"]
        advantages = advantages - kl_penalty
        returns = returns - kl_penalty

    data.batch["advantages"] = advantages
    data.batch["returns"] = returns

    metrics: dict[str, float] = {}
    if total_rollouts > 0:
        metrics["reward/cellwise_invalid_rate"] = invalid_rollouts / total_rollouts
        metrics["reward/cellwise_parse_fail_rate"] = parse_failures / total_rollouts
        metrics["reward/cellwise_tokenize_fail_rate"] = tokenize_failures / total_rollouts
        metrics["reward/cellwise_mapping_fail_rate"] = mapping_failures / total_rollouts
    if cell_total > 0:
        metrics["reward/cellwise_cell_accuracy"] = cell_correct / cell_total
    if scalar_fallback_groups > 0:
        metrics["reward/cellwise_scalar_fallback_groups"] = float(scalar_fallback_groups)

    return data, metrics


def compute_exact_match_rewards(
    data: DataProto,
    tokenizer: PreTrainedTokenizer,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Compute exact-match rewards for binary grid answers (1 if all cells match, else 0)."""
    response_ids = data.batch["responses"]
    response_mask = data.batch["response_mask"]
    token_level_scores = data.batch["token_level_scores"]
    device = response_ids.device

    reward_tensor = torch.zeros_like(response_ids, dtype=torch.float32, device=device)
    ground_truths = data.non_tensor_batch.get("ground_truth")
    if ground_truths is None:
        raise ValueError("exact-match reward_mode requires `ground_truth` in non_tensor_batch.")

    total = len(data)
    parsed = 0
    matches = 0
    parse_fail = 0
    non_grid = 0
    empty = 0

    for i in range(len(data)):
        gt_grid = to_binary_grid(ground_truths[i])
        if gt_grid is None:
            non_grid += 1
            reward_tensor[i] = token_level_scores[i]
            continue

        rows = len(gt_grid)
        cols = len(gt_grid[0]) if rows > 0 else 0
        cur_len = int(response_mask[i].sum().item())
        if cur_len <= 0:
            empty += 1
            continue

        response_str = tokenizer.decode(response_ids[i][:cur_len], skip_special_tokens=True)
        boxed_span = extract_boxed_span(response_str)
        if boxed_span:
            parse_text = response_str[boxed_span[0] : boxed_span[1]]
            base_offset = boxed_span[0]
        else:
            parse_text = response_str
            base_offset = 0

        pred, _, ok = parse_matrix_with_cell_char_spans(parse_text, rows, cols, base_offset=base_offset)
        if not ok or pred is None:
            parse_fail += 1
            reward = 0.0
        else:
            parsed += 1
            if pred == gt_grid:
                matches += 1
                reward = 1.0
            else:
                reward = 0.0

        reward_tensor[i, cur_len - 1] = reward

    metrics: dict[str, float] = {}
    if total > 0:
        metrics["reward/exact_match_rate"] = matches / total
        metrics["reward/exact_parse_fail_rate"] = parse_fail / total
        metrics["reward/exact_non_grid_rate"] = non_grid / total
        metrics["reward/exact_empty_rate"] = empty / total
    if parsed > 0:
        metrics["reward/exact_match_rate_parsed"] = matches / parsed
    return reward_tensor, metrics


class RayPPOTrainer:
    """
    Note that this trainer runs on the driver process on a single CPU/GPU node.
    """

    def __init__(
        self,
        config: PPOConfig,
        tokenizer: PreTrainedTokenizer,
        processor: Optional[ProcessorMixin],
        train_dataloader: StatefulDataLoader,
        val_dataloaders: dict[str, StatefulDataLoader],
        role_worker_mapping: dict[Role, Type[Worker]],
        resource_pool_manager: ResourcePoolManager,
        ray_worker_group_cls: Type[RayWorkerGroup] = RayWorkerGroup,
        reward_fn: Optional[AutoRewardManager] = None,
        val_reward_fn: Optional[AutoRewardManager] = None,
    ):
        self.tokenizer = tokenizer
        self.processor = processor
        self.train_dataloader = train_dataloader
        self.val_dataloaders = val_dataloaders
        self.config = config
        self.reward_fn = reward_fn
        self.val_reward_fn = val_reward_fn

        self.val_reward_score = 0.0
        self.best_val_reward_score = -1.0
        self.best_global_step = None

        self.hybrid_engine = config.worker.hybrid_engine
        self.role_worker_mapping = role_worker_mapping
        self.resource_pool_manager = resource_pool_manager
        self.use_reward_model = Role.RewardModel in role_worker_mapping
        self.ray_worker_group_cls = ray_worker_group_cls

        # define KL control
        if config.algorithm.disable_kl:
            self.use_reference_policy = False
            self.kl_ctrl = FixedKLController(init_kl_coef=0.0)
            print("KL is disabled, no KL metrics will be logged. Please set `kl_coef=0` to log KL metrics.")
        else:
            self.use_reference_policy = True
            self.kl_ctrl = get_kl_controller(config.algorithm)

        if config.algorithm.adv_estimator == AdvantageEstimator.GAE:
            self.use_critic = True
        else:
            self.use_critic = False

        if config.algorithm.adv_estimator not in list(AdvantageEstimator):
            raise NotImplementedError(f"Unknown advantage estimator: {config.algorithm.adv_estimator}.")

        if config.algorithm.reward_mode == "scalar":
            config.algorithm.reward_mode = "scalar_mean"
        if config.algorithm.reward_mode not in ("scalar_mean", "scalar_exact", "cellwise"):
            raise ValueError(f"Unknown reward_mode: {config.algorithm.reward_mode}.")
        if config.algorithm.reward_mode == "cellwise" and config.algorithm.adv_estimator != AdvantageEstimator.GRPO:
            raise NotImplementedError("Cellwise reward_mode currently supports only GRPO.")

        if config.data.rollout_batch_size % config.worker.actor.global_batch_size != 0:
            raise ValueError("Rollout batch size must be divisible by actor global batch size.")

        if (
            config.data.rollout_batch_size * config.worker.rollout.n
        ) % config.worker.actor.micro_batch_size_per_device_for_experience != 0:
            raise ValueError(
                "Rollout batch size * rollout.n must be divisible by actor micro batch size for experience."
            )

        if self.use_critic:
            if config.data.rollout_batch_size % config.worker.critic.global_batch_size != 0:
                raise ValueError("Rollout batch size must be divisible by critic global batch size.")

            if (
                config.data.rollout_batch_size * config.worker.rollout.n
            ) % config.worker.critic.micro_batch_size_per_device_for_experience != 0:
                raise ValueError(
                    "Rollout batch size * rollout.n must be divisible by critic micro batch size for experience."
                )

        if (
            config.algorithm.adv_estimator in (AdvantageEstimator.GRPO, AdvantageEstimator.RLOO)
            and config.worker.rollout.n == 1
        ):
            raise ValueError("GRPO and RLOO algorithm need `config.worker.rollout.n > 1`.")

        if config.trainer.max_steps is not None:
            self.training_steps = config.trainer.max_steps
        elif config.data.mini_rollout_batch_size is not None:
            num_examples = len(train_dataloader) * config.data.mini_rollout_batch_size
            self.training_steps = num_examples // config.data.rollout_batch_size * config.trainer.total_epochs
        else:
            self.training_steps = len(train_dataloader) * config.trainer.total_epochs

        config.worker.actor.optim.training_steps = self.training_steps
        config.worker.critic.optim.training_steps = self.training_steps
        print(f"Total training steps: {self.training_steps}")

        self.curriculum_sampler = getattr(self.train_dataloader, "curriculum_sampler", None)
        if self.curriculum_sampler is not None:
            if isinstance(self.curriculum_sampler, RankUnlockBucketSampler):
                self.curriculum_sampler.set_total_steps(self.training_steps)
                print(
                    "[curriculum] enabled mode=offline_fixed "
                    f"k_min={self.curriculum_sampler.k_min} "
                    f"total_buckets={self.curriculum_sampler.total_buckets} "
                    f"log_interval={self.config.data.curriculum_log_interval}"
                )
            elif isinstance(self.curriculum_sampler, SelfPacedEMABucketSampler):
                print(
                    "[curriculum] enabled mode=self_paced_ema "
                    f"total_buckets={self.curriculum_sampler.total_buckets} "
                    f"alpha0={self.curriculum_sampler.alpha0} "
                    f"eps_floor={self.curriculum_sampler.eps_floor:.6f} "
                    f"beta={self.curriculum_sampler.beta} "
                    f"log_interval={self.config.data.curriculum_log_interval}"
                )

    def init_workers(self) -> None:
        """Init resource pool and worker group"""
        self.resource_pool_manager.create_resource_pool()
        self.resource_pool_to_cls = {pool: {} for pool in self.resource_pool_manager.resource_pool_dict.values()}

        # create actor, rollout and ref
        if self.hybrid_engine:
            resource_pool = self.resource_pool_manager.get_resource_pool(Role.ActorRolloutRef)
            actor_rollout_ref_cls = RayClassWithInitArgs(
                cls=self.role_worker_mapping[Role.ActorRolloutRef], config=self.config.worker, role="actor_rollout_ref"
            )
            self.resource_pool_to_cls[resource_pool]["actor_rollout_ref"] = actor_rollout_ref_cls
        else:
            raise NotImplementedError

        # create critic
        if self.use_critic:
            resource_pool = self.resource_pool_manager.get_resource_pool(Role.Critic)
            critic_cls = RayClassWithInitArgs(
                cls=self.role_worker_mapping[Role.Critic], config=self.config.worker, role="critic"
            )
            self.resource_pool_to_cls[resource_pool]["critic"] = critic_cls

        # create a reward model if reward_fn is None
        if self.use_reward_model:
            # we create a RM here
            resource_pool = self.resource_pool_manager.get_resource_pool(Role.RewardModel)
            rm_cls = RayClassWithInitArgs(
                cls=self.role_worker_mapping[Role.RewardModel], config=self.config.worker, role="reward"
            )
            self.resource_pool_to_cls[resource_pool]["rm"] = rm_cls

        # initialize WorkerGroup
        # NOTE: if you want to use a different resource pool for each role, which can support different parallel size,
        # you should not use `create_colocated_worker_cls`. Instead, directly pass different resource pool to different worker groups.
        # See https://github.com/volcengine/verl/blob/master/examples/ray/tutorial.ipynb for more information.
        all_wg: dict[str, FSDPWorker] = {}
        self.wg_dicts = []
        for resource_pool, class_dict in self.resource_pool_to_cls.items():
            worker_dict_cls = create_colocated_worker_cls(class_dict=class_dict)
            wg_dict = self.ray_worker_group_cls(resource_pool=resource_pool, ray_cls_with_init=worker_dict_cls)
            spawn_wg = wg_dict.spawn(prefix_set=class_dict.keys())
            all_wg.update(spawn_wg)
            # keep the referece of WorkerDict to support ray >= 2.31. Ref: https://github.com/ray-project/ray/pull/45699
            self.wg_dicts.append(wg_dict)

        if self.use_critic:
            self.critic_wg = all_wg["critic"]
            self.critic_wg.init_model()

        if self.use_reward_model:
            self.rm_wg = all_wg["rm"]
            self.rm_wg.init_model()

        # we should create rollout at the end so that vllm can have a better estimation of kv cache memory
        self.actor_rollout_ref_wg = all_wg["actor_rollout_ref"]
        self.actor_rollout_ref_wg.init_model()

    def _save_checkpoint(self) -> None:
        # path: {save_checkpoint_path}/global_step_{global_step}/{actor,critic}
        if self.val_reward_score > self.best_val_reward_score:
            self.best_val_reward_score = self.val_reward_score
            self.best_global_step = self.global_step

        remove_obsolete_ckpt(
            self.config.trainer.save_checkpoint_path,
            self.global_step,
            self.best_global_step,
            self.config.trainer.save_limit,
        )
        folder_path = os.path.join(self.config.trainer.save_checkpoint_path, f"global_step_{self.global_step}")
        actor_path = os.path.join(folder_path, "actor")
        self.actor_rollout_ref_wg.save_checkpoint(actor_path, save_model_only=self.config.trainer.save_model_only)

        if self.use_critic:
            critic_path = os.path.join(folder_path, "critic")
            self.critic_wg.save_checkpoint(critic_path, save_model_only=self.config.trainer.save_model_only)

        dataloader_path = os.path.join(folder_path, "dataloader.pt")
        dataloader_state_dict = self.train_dataloader.state_dict()
        torch.save(dataloader_state_dict, dataloader_path)

        checkpointer_tracker_info = {
            "best_global_step": self.best_global_step,
            "best_val_reward_score": round(self.best_val_reward_score, 4),
            "last_global_step": self.global_step,
            "last_actor_path": os.path.abspath(actor_path),
        }
        checkpointer_tracker_path = os.path.join(self.config.trainer.save_checkpoint_path, CHECKPOINT_TRACKER)
        with open(checkpointer_tracker_path, "w") as f:
            json.dump(checkpointer_tracker_info, f, ensure_ascii=False, indent=2)

    def _load_checkpoint(self) -> None:
        if self.config.trainer.load_checkpoint_path is not None:
            load_checkpoint_path = self.config.trainer.load_checkpoint_path
        elif self.config.trainer.find_last_checkpoint:
            load_checkpoint_path, tracker_info = find_latest_ckpt(self.config.trainer.save_checkpoint_path)
            if tracker_info is not None:
                self.best_val_reward_score = tracker_info.get("best_val_reward_score", 0.0)
                self.best_global_step = tracker_info.get("best_global_step", 0)
        else:
            load_checkpoint_path = None

        if load_checkpoint_path is None:
            return

        if "global_step_" not in load_checkpoint_path.strip(os.path.sep).split(os.path.sep)[-1]:
            raise ValueError("`load_checkpoint_path` should end with `global_step_*`.")

        print(f"Load from checkpoint: {load_checkpoint_path}.")
        self.global_step = int(load_checkpoint_path.strip(os.path.sep).split("global_step_")[-1])
        actor_path = os.path.join(load_checkpoint_path, "actor")
        self.actor_rollout_ref_wg.load_checkpoint(actor_path)
        if self.use_critic:
            critic_path = os.path.join(load_checkpoint_path, "critic")
            self.critic_wg.load_checkpoint(critic_path)

        dataloader_path = os.path.join(load_checkpoint_path, "dataloader.pt")
        if os.path.exists(dataloader_path):
            dataloader_state_dict = torch.load(dataloader_path, weights_only=False)
            self.train_dataloader.load_state_dict(dataloader_state_dict)
        else:
            print(f"No dataloader state found at {dataloader_path}, will start from scratch.")

    def _maybe_log_val_generations(
        self, inputs: list[str], outputs: list[str], labels: list[str], scores: list[float]
    ) -> None:
        """Log a table of validation samples"""
        if self.config.trainer.val_generations_to_log <= 0:
            return

        # Create tuples of (input, output, score) and sort by input text
        samples = list(zip(inputs, outputs, labels, scores))
        samples.sort(key=lambda x: x[0])  # Sort by input text

        # Use fixed random seed for deterministic shuffling
        rng = np.random.RandomState(42)
        rng.shuffle(samples)

        samples = samples[: self.config.trainer.val_generations_to_log]
        self.logger.log_generation(samples, self.global_step)

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, torch.Tensor):
            return value.detach().cpu().tolist()
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, dict):
            return {str(k): RayPPOTrainer._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [RayPPOTrainer._to_jsonable(v) for v in value]
        return value

    def _maybe_dump_val_predictions(self, name: str, rows: list[dict[str, Any]], metrics: dict[str, Any]) -> None:
        dump_root = self.config.trainer.val_predictions_dump_dir
        if not dump_root:
            return

        dataset_dir = os.path.join(dump_root, f"global_step_{self.global_step}", name)
        os.makedirs(dataset_dir, exist_ok=True)

        predictions_path = os.path.join(dataset_dir, "predictions.jsonl")
        with open(predictions_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(self._to_jsonable(row), ensure_ascii=False) + "\n")

        metrics_path = os.path.join(dataset_dir, "metrics.json")
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(self._to_jsonable(metrics), f, ensure_ascii=False, indent=2)

    def _validate(self) -> dict[str, Any]:
        if len(self.val_dataloaders) == 0:
            return {}
        metrics: dict[str, Any] = {}
        reward_scores = []
        total_accuracy_scores = []
        extraction_rate_scores = []

        for name, dataloader in self.val_dataloaders.items():
            print(name)

        # assuming self.val_dataloaders is a dict-like object
        names = list(self.val_dataloaders.keys())

        # write to txt file, one per line
        with open("val_dataloaders.txt", "w") as f:
            for name in names:
                f.write(f"{name}\n")

        for name, dataloader in self.val_dataloaders.items():
            reward_tensor_lst = []
            sample_inputs, sample_outputs, sample_labels, sample_scores = [], [], [], []
            sample_rows: list[dict[str, Any]] = []
            reward_metrics_lst = defaultdict(list)
            length_metrics_lst = defaultdict(list)
            print(f"Start validation on {name}...")
            self.actor_rollout_ref_wg.prepare_rollout_engine()
            for batch_dict in dataloader:
                test_batch = DataProto.from_single_dict(batch_dict)
                test_gen_batch = test_batch.pop(
                    batch_keys=["input_ids", "attention_mask", "position_ids"],
                    non_tensor_batch_keys=["raw_prompt_ids", "multi_modal_data"],
                )
                val_override_config = dict(self.config.worker.rollout.val_override_config)
                if "max_tokens" in val_override_config and val_override_config["max_tokens"] is not None:
                    val_override_config["max_tokens"] = int(val_override_config["max_tokens"])
                repeat_times = val_override_config.get("n", 1)
                test_gen_batch.meta_info = val_override_config
                test_gen_batch.meta_info["min_pixels"] = self.config.data.min_pixels
                test_gen_batch.meta_info["max_pixels"] = self.config.data.max_pixels
                test_gen_batch.meta_info["video_fps"] = self.config.data.video_fps

                test_gen_batch, pad_size = pad_dataproto_to_divisor(
                    test_gen_batch, self.actor_rollout_ref_wg.world_size
                )
                test_output_gen_batch = self.actor_rollout_ref_wg.generate_sequences(test_gen_batch)
                test_output_gen_batch = unpad_dataproto(test_output_gen_batch, pad_size=pad_size * repeat_times)

                test_batch = test_batch.repeat(repeat_times=repeat_times, interleave=True)
                test_batch = test_batch.union(test_output_gen_batch)

                reward_result = compute_val_reward(
                    test_batch,
                    tokenizer=self.tokenizer,
                    dataset_name=name,
                    skip_special_tokens=self.config.worker.reward.skip_special_tokens,
                    return_details=bool(self.config.trainer.val_predictions_dump_dir),
                )
                if self.config.trainer.val_predictions_dump_dir:
                    reward_tensor, reward_metrics, reward_details = reward_result
                else:
                    reward_tensor, reward_metrics = reward_result
                    reward_details = None

                input_ids = test_batch.batch["prompts"]
                input_texts = [self.tokenizer.decode(ids, skip_special_tokens=True) for ids in input_ids]
                output_ids = test_batch.batch["responses"]
                output_texts = [self.tokenizer.decode(ids, skip_special_tokens=True) for ids in output_ids]
                scores = reward_tensor.sum(-1).cpu().tolist()
                sample_inputs.extend(input_texts)
                sample_outputs.extend(output_texts)
                sample_labels.extend(test_batch.non_tensor_batch["ground_truth"].tolist())
                sample_scores.extend(scores)
                if reward_details is not None:
                    uids = test_batch.non_tensor_batch.get("uid")
                    finish_reasons = test_batch.non_tensor_batch.get("finish_reason")
                    stop_reasons = test_batch.non_tensor_batch.get("stop_reason")
                    for idx, detail in enumerate(reward_details):
                        sample_rows.append(
                            {
                                "uid": None if uids is None else uids[idx],
                                "prompt": input_texts[idx],
                                "response": output_texts[idx],
                                "ground_truth": test_batch.non_tensor_batch["ground_truth"][idx],
                                "score": detail["overall"],
                                "format_score": detail["format"],
                                "hit": detail["hit"],
                                "extracted": detail["extracted"],
                                "extracted_answer": detail["extracted_answer"],
                                "parser_output": detail["parser_output"],
                                "parser_family": detail["parser_family"],
                                "metadata": detail["metadata"],
                                "generated_tokens": detail["generated_tokens"],
                                "finish_reason": None if finish_reasons is None else finish_reasons[idx],
                                "stop_reason": None if stop_reasons is None else stop_reasons[idx],
                            }
                        )

                reward_tensor_lst.append(reward_tensor)
                for key, value in reward_metrics.items():
                    reward_metrics_lst[key].extend(value)

                length_metrics = compute_length_metrics(test_batch)
                length_metrics_lst["response_length/mean"].append(length_metrics["response_length/mean"])

            self.actor_rollout_ref_wg.release_rollout_engine()
            self._maybe_log_val_generations(sample_inputs, sample_outputs, sample_labels, sample_scores)
            reduced_metrics = reduce_metrics(reward_metrics_lst)

            hits = reward_metrics_lst.get("hit", [])
            extracted_flags = reward_metrics_lst.get("extracted", [])
            total_count = float(len(hits))
            extracted_count = float(np.sum(extracted_flags)) if extracted_flags else 0.0
            hit_count = float(np.sum(hits)) if hits else 0.0
            acc_on_extracted = (hit_count / extracted_count) if extracted_count > 0 else 0.0
            acc_on_total = (hit_count / total_count) if total_count > 0 else 0.0
            extraction_rate = (extracted_count / total_count) if total_count > 0 else 0.0

            # Use extracted-only accuracy as the canonical validation accuracy.
            metrics[f"val/{name}/accuracy_on_extracted"] = acc_on_extracted
            metrics[f"val/{name}/accuracy_on_total"] = acc_on_total
            metrics[f"val/{name}/extraction_rate"] = extraction_rate

            reward_scores.append(acc_on_extracted)
            total_accuracy_scores.append(acc_on_total)
            extraction_rate_scores.append(extraction_rate)

            reduced_length = reduce_metrics(length_metrics_lst)
            if "response_length/mean" in reduced_length:
                metrics[f"val/{name}_response_length/mean"] = reduced_length["response_length/mean"]
            finish_reason_counts = Counter()
            for row in sample_rows:
                finish_reason_counts[str(row.get("finish_reason"))] += 1
            if sample_rows:
                total_rows = float(len(sample_rows))
                for reason, count in finish_reason_counts.items():
                    metrics[f"val/{name}/finish_reason/{reason}"] = float(count)
                    metrics[f"val/{name}/finish_reason_rate/{reason}"] = float(count) / total_rows
                self._maybe_dump_val_predictions(
                    name=name,
                    rows=sample_rows,
                    metrics={
                        "accuracy_on_extracted": acc_on_extracted,
                        "accuracy_on_total": acc_on_total,
                        "extraction_rate": extraction_rate,
                        "response_length_mean": reduced_length.get("response_length/mean"),
                        "finish_reason_counts": dict(finish_reason_counts),
                        "num_rows": len(sample_rows),
                    },
                )
            print(f"Finish validation on {name}.")

        if reward_scores:
            self.val_reward_score = float(np.mean(reward_scores))
            metrics["val/accuracy_on_extracted"] = self.val_reward_score
            if total_accuracy_scores:
                metrics["val/accuracy_on_total"] = float(np.mean(total_accuracy_scores))
            if extraction_rate_scores:
                metrics["val/extraction_rate"] = float(np.mean(extraction_rate_scores))
        else:
            self.val_reward_score = 0.0
        return metrics

    def _compute_zero_solve_metrics(self, batch: DataProto, token_level_scores: torch.Tensor) -> dict[str, float]:
        """Compute zero-solve rate/count based on max reward per uid."""
        if token_level_scores.dim() == 2:
            seq_scores = token_level_scores.sum(-1)
        elif token_level_scores.dim() == 1:
            seq_scores = token_level_scores
        else:
            raise ValueError(f"Unexpected reward shape: {tuple(token_level_scores.shape)}")

        uids = batch.non_tensor_batch.get("uid")
        if uids is None:
            return {}

        uid_list = np.asarray(uids, dtype=object).tolist()
        if len(uid_list) != seq_scores.shape[0]:
            raise ValueError("UID count does not match number of token-level scores.")

        threshold = float(self.config.algorithm.zero_solve_threshold)
        eps = 1e-8
        seq_scores_np = seq_scores.detach().cpu().numpy()
        uid_max: dict[object, float] = {}
        for uid, score in zip(uid_list, seq_scores_np):
            current = uid_max.get(uid)
            if current is None or score > current:
                uid_max[uid] = float(score)

        num_groups = len(uid_max)
        # Treat exact-zero (within epsilon) as unsolved by default.
        # Users can still raise `zero_solve_threshold` for stricter criteria.
        zero_count = sum(1 for score in uid_max.values() if score <= (threshold + eps))

        return {
            "rlvr_stats/zero_solve_rate": float(zero_count / max(1, num_groups)),
            "rlvr_stats/zero_solve_count": float(zero_count),
        }

    def _balance_batch(self, batch: DataProto, metrics: dict[str, Any], logging_prefix: str = "global_seqlen") -> None:
        """Reorder the data on single controller such that each dp rank gets similar total tokens"""
        attention_mask = batch.batch["attention_mask"]
        batch_size = attention_mask.shape[0]
        global_seqlen_lst = batch.batch["attention_mask"].view(batch_size, -1).sum(-1).tolist()  # (train_batch_size,)
        world_size = self.actor_rollout_ref_wg.world_size
        global_partition_lst = get_seqlen_balanced_partitions(
            global_seqlen_lst, k_partitions=world_size, equal_size=True
        )
        # reorder based on index. The data will be automatically equally partitioned by dispatch function
        global_idx = torch.tensor([j for partition in global_partition_lst for j in partition])
        batch.reorder(global_idx)
        global_balance_stats = log_seqlen_unbalance(
            seqlen_list=global_seqlen_lst, partitions=global_partition_lst, prefix=logging_prefix
        )
        metrics.update(global_balance_stats)

    def _make_batch_data(self, metrics: dict[str, Any]) -> DataProto:
        batch = None
        all_metrics = defaultdict(list)
        num_try_make_batch = 0
        print("Start generating batch...")
        while True:
            num_try_make_batch += 1
            try:
                batch_dict = next(self.data_iterator)
            except StopIteration:
                self.data_iterator = iter(self.train_dataloader)
                batch_dict = next(self.data_iterator)

            meta_info = {
                "min_pixels": self.config.data.min_pixels,
                "max_pixels": self.config.data.max_pixels,
                "video_fps": self.config.data.video_fps,
            }
            new_batch: DataProto = DataProto.from_single_dict(batch_dict, meta_info=meta_info)
            new_batch.non_tensor_batch["uid"] = np.array(
                [str(uuid.uuid4()) for _ in range(len(new_batch.batch))], dtype=object
            )

            # pop those keys for generation
            gen_batch = new_batch.pop(
                batch_keys=["input_ids", "attention_mask", "position_ids"],
                non_tensor_batch_keys=["raw_prompt_ids", "multi_modal_data"],
                meta_info_keys=["min_pixels", "max_pixels", "video_fps"],
            )

            # generate a batch
            gen_batch_output = self.actor_rollout_ref_wg.generate_sequences(gen_batch)

            if self.config.algorithm.adv_estimator == "remax":
                gen_baseline_batch = deepcopy(gen_batch)
                gen_baseline_batch.meta_info["temperature"] = 0
                gen_baseline_batch.meta_info["n"] = 1
                gen_baseline_output = self.actor_rollout_ref_wg.generate_sequences(gen_baseline_batch)

                new_batch = new_batch.union(gen_baseline_output)
                reward_baseline_tensor, _ = ray.get(self.reward_fn.compute_reward.remote(new_batch))
                reward_baseline_tensor = reward_baseline_tensor.sum(dim=-1)

                new_batch.pop(batch_keys=list(gen_baseline_output.batch.keys()))
                new_batch.batch["reward_baselines"] = reward_baseline_tensor
                del gen_baseline_batch, gen_baseline_output

            # repeat to align with repeated responses in rollout
            new_batch = new_batch.repeat(repeat_times=self.config.worker.rollout.n, interleave=True)
            new_batch = new_batch.union(gen_batch_output)

            # filter group
            if self.config.algorithm.online_filtering:
                reward_tensor, reward_metrics = ray.get(self.reward_fn.compute_reward.remote(new_batch))
                new_batch.batch["token_level_scores"] = reward_tensor
                for k, v in reward_metrics.items():
                    all_metrics[k].extend(v)

                filter_scores = reward_metrics[self.config.algorithm.filter_key]
                uids = new_batch.non_tensor_batch["uid"]
                uid2scores = defaultdict(list)
                for uid, score in zip(uids, filter_scores):
                    uid2scores[uid].append(score)

                uid2mean = {uid: np.mean(scores) for uid, scores in uid2scores.items()}
                kept_uids = [
                    uid
                    for uid, avg_score in uid2mean.items()
                    if avg_score > self.config.algorithm.filter_low and avg_score < self.config.algorithm.filter_high
                ]
                kept_sample_idxs = [idx for idx, uid in enumerate(uids) if uid in kept_uids]
                if len(kept_sample_idxs) == 0:
                    raise RuntimeError("No sample is kept after filtering. Please check your data.")

                new_batch = new_batch[kept_sample_idxs]

            batch = DataProto.concat([batch, new_batch]) if batch is not None else new_batch
            current_batch_size = len(batch) // self.config.worker.rollout.n
            rollout_batch_size = self.config.data.rollout_batch_size
            if current_batch_size < rollout_batch_size:
                print(f"{current_batch_size=} < {rollout_batch_size=}")
                max_try_make_batch = self.config.trainer.max_try_make_batch
                if max_try_make_batch <= 0 or num_try_make_batch < max_try_make_batch:
                    print(f"{num_try_make_batch=}. Continue generating...")
                else:
                    raise RuntimeError(
                        f"{num_try_make_batch=} >= {max_try_make_batch=}. Generated too many. Please check your data."
                    )
            else:
                print(f"{current_batch_size=} >= {rollout_batch_size=}. Finish generating.")
                if self.config.algorithm.online_filtering:
                    metrics.update({f"reward/{k}": v for k, v in reduce_metrics(all_metrics).items()})

                return batch[: self.config.data.rollout_batch_size * self.config.worker.rollout.n]

    def fit(self):
        """
        The training loop of PPO.
        The driver process only need to call the compute functions of the worker group through RPC to construct the PPO dataflow.
        The light-weight advantage computation is done on the driver process.
        """
        self.logger = Tracker(loggers=self.config.trainer.logger, config=self.config.to_dict())
        self.global_step = 0
        main_tqdm = tqdm(range(self.training_steps), desc="Running step", position=0)
        val_metrics: Optional[dict[str, Any]] = None

        # load checkpoint before doing anything
        self._load_checkpoint()
        main_tqdm.update(self.global_step)

        # perform validation before training
        # currently, we only support validation using the reward_function.
        if (
            self.val_reward_fn is not None
            and len(self.val_dataloaders) > 0
            and self.config.trainer.val_before_train
        ):
            val_metrics = self._validate()
            self.logger.log(data=val_metrics, step=self.global_step)
            if self.config.trainer.val_only:
                return


        self.data_iterator = iter(self.train_dataloader)
        while self.global_step < self.training_steps:
            self.global_step += 1
            if isinstance(self.curriculum_sampler, RankUnlockBucketSampler):
                self.curriculum_sampler.set_step(self.global_step)

            metrics, timing_raw = {}, {}
            with timer("step", timing_raw):
                # make a batch of data
                with timer("gen", timing_raw):
                    self.actor_rollout_ref_wg.prepare_rollout_engine()
                    batch = self._make_batch_data(metrics=metrics)
                    self.actor_rollout_ref_wg.release_rollout_engine()

                # balance the number of valid tokens on each dp rank.
                # NOTE: this breaks the order of data inside the batch.
                # Please take care when you implement group based adv computation such as GRPO and rloo
                self._balance_batch(batch, metrics=metrics)

                # compute global valid tokens
                batch.meta_info["global_token_num"] = torch.sum(batch.batch["attention_mask"], dim=-1).tolist()

                # compute reward
                if "token_level_scores" not in batch.batch:
                    with timer("reward", timing_raw):
                        reward_ref = self.reward_fn.compute_reward.remote(batch)

                # recompute old_log_probs
                with timer("old", timing_raw):
                    old_log_probs = self.actor_rollout_ref_wg.compute_log_probs(batch)
                    batch = batch.union(old_log_probs)

                # compute ref_log_probs
                if self.use_reference_policy:
                    with timer("ref", timing_raw):
                        ref_log_probs = self.actor_rollout_ref_wg.compute_ref_log_probs(batch)
                        batch = batch.union(ref_log_probs)

                # compute values
                if self.use_critic:
                    with timer("values", timing_raw):
                        values = self.critic_wg.compute_values(batch)
                        batch = batch.union(values)

                with timer("adv", timing_raw):
                    if "token_level_scores" not in batch.batch:
                        # get token level scores asynchronously
                        reward_tensor, reward_metrics = ray.get(reward_ref)
                        batch.batch["token_level_scores"] = reward_tensor
                        reward_metrics = {f"reward/{k}": v for k, v in reduce_metrics(reward_metrics).items()}
                        metrics.update(reward_metrics)

                    # apply kl penalty if available
                    if not self.config.algorithm.use_kl_loss and self.use_reference_policy:
                        # apply kl penalty to reward
                        batch, kl_metrics = apply_kl_penalty(batch, self.kl_ctrl, self.config.algorithm.kl_penalty)
                        metrics.update(kl_metrics)
                    else:
                        batch.batch["token_level_rewards"] = batch.batch["token_level_scores"]

                    # compute advantages, executed on the driver process
                    if self.config.algorithm.reward_mode == "cellwise":
                        batch, cell_metrics = compute_cellwise_advantage(
                            batch,
                            tokenizer=self.tokenizer,
                            use_reference_policy=self.use_reference_policy,
                            use_kl_loss=self.config.algorithm.use_kl_loss,
                        )
                        metrics.update(cell_metrics)
                    else:
                        if self.config.algorithm.reward_mode == "scalar_exact":
                            exact_rewards, exact_metrics = compute_exact_match_rewards(
                                batch,
                                tokenizer=self.tokenizer,
                            )
                            if not self.config.algorithm.use_kl_loss and self.use_reference_policy:
                                kl_penalty = batch.batch["token_level_scores"] - batch.batch["token_level_rewards"]
                                exact_rewards = exact_rewards - kl_penalty
                            batch.batch["token_level_rewards"] = exact_rewards
                            metrics.update(exact_metrics)
                        batch = compute_advantage(
                            batch,
                            adv_estimator=self.config.algorithm.adv_estimator,
                            gamma=self.config.algorithm.gamma,
                            lam=self.config.algorithm.lam,
                        )

                # update critic
                if self.use_critic:
                    with timer("update_critic", timing_raw):
                        critic_output = self.critic_wg.update_critic(batch)

                    critic_metrics = reduce_metrics(critic_output.non_tensor_batch)
                    metrics.update(critic_metrics)

                # update actor
                if self.config.trainer.critic_warmup <= self.global_step:
                    with timer("update_actor", timing_raw):
                        actor_output = self.actor_rollout_ref_wg.update_actor(batch)

                    actor_metrics = reduce_metrics(actor_output.non_tensor_batch)
                    metrics.update(actor_metrics)

                # validate
                if (
                    self.val_reward_fn is not None
                    and len(self.val_dataloaders) > 0
                    and self.config.trainer.val_freq > 0
                    and self.global_step % self.config.trainer.val_freq == 0
                ):
                    with timer("validation", timing_raw):
                        val_metrics = self._validate()

                    metrics.update(val_metrics)

                if self.config.trainer.save_freq > 0 and self.global_step % self.config.trainer.save_freq == 0:
                    with timer("save_checkpoint", timing_raw):
                        self._save_checkpoint()

            # collect metrics
            num_gpus = self.resource_pool_manager.get_num_gpus()
            metrics.update(compute_data_metrics(batch=batch, use_critic=self.use_critic))
            metrics.update(compute_timing_metrics(batch=batch, timing_raw=timing_raw))
            metrics.update(compute_throughout_metrics(batch=batch, timing_raw=timing_raw, num_gpus=num_gpus))
            token_level_scores = batch.batch.get("token_level_scores")
            if token_level_scores is not None:
                metrics.update(self._compute_zero_solve_metrics(batch, token_level_scores))
                metrics.update(self._update_curriculum_sampler(batch, token_level_scores))
            if self.curriculum_sampler is not None:
                metrics.update(self._compute_curriculum_metrics(batch))

            self.logger.log(data=metrics, step=self.global_step)
            main_tqdm.update()

        # perform validation after training
        if self.val_reward_fn is not None and len(self.val_dataloaders) > 0:
            if (
                val_metrics is None
                or self.config.trainer.val_freq <= 0
                or self.global_step % self.config.trainer.val_freq != 0
            ):
                val_metrics = self._validate()
                self.logger.log(data=val_metrics, step=self.global_step)

            print(f"Final validation metrics:\n{convert_dict_to_str(unflatten_dict(val_metrics))}")

        if self.config.trainer.save_freq <= 0 or self.global_step % self.config.trainer.save_freq != 0:
            self._save_checkpoint()

    def _extract_prompt_bucket_ids(self, batch: DataProto) -> list[str]:
        bucket_ids = batch.non_tensor_batch.get("bucket_id_str")
        if bucket_ids is None:
            return []
        uids = batch.non_tensor_batch.get("uid")
        if uids is not None and len(uids) == len(bucket_ids):
            uid_to_bucket: dict[Any, str] = {}
            for uid, bucket_id in zip(uids, bucket_ids):
                if uid not in uid_to_bucket:
                    uid_to_bucket[uid] = str(bucket_id)
            return list(uid_to_bucket.values())
        return [str(bucket_id) for bucket_id in bucket_ids]

    def _extract_prompt_bucket_rewards(
        self, batch: DataProto, token_level_scores: torch.Tensor
    ) -> tuple[list[str], list[float]]:
        if token_level_scores.dim() == 2:
            seq_scores = token_level_scores.sum(-1)
        elif token_level_scores.dim() == 1:
            seq_scores = token_level_scores
        else:
            raise ValueError(f"Unexpected reward shape for curriculum update: {tuple(token_level_scores.shape)}")

        bucket_ids = batch.non_tensor_batch.get("bucket_id_str")
        uids = batch.non_tensor_batch.get("uid")
        if bucket_ids is None or uids is None:
            return [], []
        if len(bucket_ids) != seq_scores.shape[0] or len(uids) != seq_scores.shape[0]:
            return [], []

        uid_to_bucket: dict[Any, str] = {}
        uid_to_scores: dict[Any, list[float]] = defaultdict(list)
        seq_scores_np = seq_scores.detach().cpu().numpy()
        for uid, bucket_id, score in zip(uids, bucket_ids, seq_scores_np):
            if uid not in uid_to_bucket:
                uid_to_bucket[uid] = str(bucket_id)
            uid_to_scores[uid].append(float(score))

        prompt_bucket_ids: list[str] = []
        prompt_rewards: list[float] = []
        for uid, score_list in uid_to_scores.items():
            if not score_list:
                continue
            prompt_bucket_ids.append(uid_to_bucket[uid])
            prompt_rewards.append(float(np.mean(score_list)))
        return prompt_bucket_ids, prompt_rewards

    def _update_curriculum_sampler(self, batch: DataProto, token_level_scores: torch.Tensor) -> dict[str, float]:
        if not isinstance(self.curriculum_sampler, SelfPacedEMABucketSampler):
            return {}
        prompt_bucket_ids, prompt_rewards = self._extract_prompt_bucket_rewards(batch, token_level_scores)
        if len(prompt_bucket_ids) == 0:
            return {}
        self.curriculum_sampler.update_from_prompt_rewards(prompt_bucket_ids, prompt_rewards)
        return {
            "curriculum/update_prompt_count": float(len(prompt_bucket_ids)),
            "curriculum/update_reward_mean": float(np.mean(prompt_rewards)),
            "curriculum/update_reward_std": float(np.std(prompt_rewards)),
        }

    def _compute_curriculum_metrics(self, batch: DataProto) -> dict[str, float]:
        metrics: dict[str, float] = {}
        if isinstance(self.curriculum_sampler, RankUnlockBucketSampler):
            metrics.update(
                {
                    "curriculum/k_current": float(self.curriculum_sampler.current_k),
                }
            )
        elif isinstance(self.curriculum_sampler, SelfPacedEMABucketSampler):
            mu_values = np.asarray(self.curriculum_sampler.mu_values, dtype=np.float32)
            prob_values = np.asarray(self.curriculum_sampler.prob_values, dtype=np.float32)
            top_idx = int(np.argmax(prob_values))
            top_bucket_id = self.curriculum_sampler.bucket_order[top_idx]
            top_bucket_mu = float(self.curriculum_sampler.mu_values[top_idx])
            top_bucket_prob = float(prob_values[top_idx])
            entropy = float(-np.sum(prob_values * np.log(np.clip(prob_values, 1e-12, 1.0))))
            topk = min(5, len(prob_values))
            topk_mass = float(np.sort(prob_values)[-topk:].sum())
            eff_buckets = float(np.exp(entropy))
            metrics.update(
                {
                    "curriculum/mu_min": float(np.min(mu_values)),
                    "curriculum/mu_mean": float(np.mean(mu_values)),
                    "curriculum/mu_median": float(np.median(mu_values)),
                    "curriculum/mu_max": float(np.max(mu_values)),
                    "curriculum/mu_std": float(np.std(mu_values)),
                    "curriculum/prob_entropy": entropy,
                    "curriculum/prob_eff_buckets": eff_buckets,
                    "curriculum/top_bucket_prob": top_bucket_prob,
                    "curriculum/top_bucket_mu": top_bucket_mu,
                    "curriculum/top5_prob_mass": topk_mass,
                }
            )
            try:
                variant_id_str, count_bin_str = top_bucket_id.split("-", 1)
                metrics["curriculum/top_bucket_variant_id"] = float(int(variant_id_str))
                metrics["curriculum/top_bucket_count_bin"] = float(int(count_bin_str))
            except Exception:
                pass
            mu_std = float(np.std(mu_values))
            prob_std = float(np.std(prob_values))
            if mu_std > 1e-12 and prob_std > 1e-12:
                corr = float(np.corrcoef(mu_values, prob_values)[0, 1])
            else:
                corr = 0.0
            metrics["curriculum/mu_prob_corr"] = corr

        prompt_bucket_ids = self._extract_prompt_bucket_ids(batch)
        if len(prompt_bucket_ids) == 0:
            return metrics

        bucket_counts = Counter(prompt_bucket_ids)
        prompt_count = float(len(prompt_bucket_ids))
        metrics["curriculum/sampled_prompt_count"] = prompt_count
        metrics["curriculum/sampled_unique_buckets"] = float(len(bucket_counts))
        if isinstance(self.curriculum_sampler, SelfPacedEMABucketSampler):
            metrics["curriculum/sampled_unique_frac"] = float(len(bucket_counts)) / float(
                self.curriculum_sampler.total_buckets
            )
            if len(bucket_counts) > 0:
                sampled_fracs = np.asarray([count / prompt_count for count in bucket_counts.values()], dtype=np.float32)
                metrics["curriculum/sampled_top_bucket_frac"] = float(np.max(sampled_fracs))
                metrics["curriculum/sampled_frac_entropy"] = float(
                    -np.sum(sampled_fracs * np.log(np.clip(sampled_fracs, 1e-12, 1.0)))
                )

        return metrics

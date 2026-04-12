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
PPO config
"""

import os
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from typing import Optional, Tuple

from ..utils.py_functional import get_abs_path
from ..workers.config import WorkerConfig


def recursive_post_init(dataclass_obj):
    if hasattr(dataclass_obj, "post_init"):
        dataclass_obj.post_init()

    for attr in fields(dataclass_obj):
        if is_dataclass(getattr(dataclass_obj, attr.name)):
            recursive_post_init(getattr(dataclass_obj, attr.name))


@dataclass
class DataConfig:
    train_files: str = ""
    val_files: list[str] = field(default_factory=list)
    dataset_mode: str = "none"
    curriculum_mode: str = "none"
    curriculum_backend: str = "prebuilt"
    curriculum_bucket_order_path: Optional[str] = None
    curriculum_mu_init_path: Optional[str] = None
    curriculum_alpha0: float = 0.995
    curriculum_eps_floor: Optional[float] = None
    curriculum_beta: float = 2.0
    curriculum_log_interval: int = 50
    prompt_key: str = "prompt"
    answer_key: str = "answer"
    image_key: str = "images"
    video_key: str = "videos"
    image_dir: Optional[str] = None
    video_fps: float = 2.0
    max_prompt_length: int = 512
    max_response_length: int = 512
    rollout_batch_size: int = 512
    mini_rollout_batch_size: Optional[int] = None
    val_batch_size: int = -1
    train_dataloader_num_workers: int = 8
    val_dataloader_num_workers: int = 8
    format_prompt: Optional[str] = None
    format_prompt_variant: str = "boxed_only"
    val_format_prompt: Optional[str] = None
    val_format_prompt_variant: Optional[str] = None
    override_chat_template: Optional[str] = None
    shuffle: bool = True
    seed: int = 1
    min_pixels: Optional[int] = 262144
    max_pixels: Optional[int] = 4194304
    filter_overlong_prompts: bool = True
    filter_overlong_prompts_workers: int = 16
    filter_overlong_prompts_val: bool = False
    filter_overlong_prompts_workers_val: int = 16
    log_dataset_download_status: bool = True

    def post_init(self):
        if isinstance(self.val_files, str):
            self.val_files = [self.val_files]
        self.dataset_mode = (self.dataset_mode or "none").lower()
        if self.dataset_mode not in {"none", "integer", "bbox", "trace"}:
            raise ValueError(f"Unsupported data.dataset_mode: {self.dataset_mode}")
        self.curriculum_mode = (self.curriculum_mode or "none").lower()
        # Backward-compatible alias kept for previous docs/configs.
        if self.curriculum_mode == "offline_online_hybrid":
            self.curriculum_mode = "self_paced_ema"
        if self.curriculum_mode not in {"none", "offline_fixed", "self_paced_ema"}:
            raise ValueError(f"Unsupported data.curriculum_mode: {self.curriculum_mode}")
        self.curriculum_backend = (self.curriculum_backend or "prebuilt").lower()
        if self.curriculum_backend not in {"prebuilt", "api"}:
            raise ValueError(f"Unsupported data.curriculum_backend: {self.curriculum_backend}")
        if self.curriculum_log_interval <= 0:
            raise ValueError("data.curriculum_log_interval must be > 0")
        if self.curriculum_alpha0 <= 0.0 or self.curriculum_alpha0 >= 1.0:
            raise ValueError("data.curriculum_alpha0 must be in (0, 1)")
        if self.curriculum_eps_floor is not None and self.curriculum_eps_floor < 0.0:
            raise ValueError("data.curriculum_eps_floor must be >= 0 when provided")
        if self.curriculum_beta <= 0.0:
            raise ValueError("data.curriculum_beta must be > 0")
        if self.train_dataloader_num_workers < 0:
            raise ValueError("data.train_dataloader_num_workers must be >= 0")
        if self.val_dataloader_num_workers < 0:
            raise ValueError("data.val_dataloader_num_workers must be >= 0")
        self.image_dir = get_abs_path(self.image_dir, prompt="Image directory")
        self.format_prompt = get_abs_path(self.format_prompt, prompt="Format prompt file")
        self.val_format_prompt = get_abs_path(self.val_format_prompt, prompt="Validation format prompt file")
        self.format_prompt_variant = (self.format_prompt_variant or "boxed_only").lower()
        if self.format_prompt_variant not in {"boxed_only", "legacy_think_boxed"}:
            raise ValueError(
                "data.format_prompt_variant must be one of {'boxed_only', 'legacy_think_boxed'}, "
                f"got {self.format_prompt_variant}"
            )
        if self.val_format_prompt_variant is not None:
            self.val_format_prompt_variant = self.val_format_prompt_variant.lower()
            if self.val_format_prompt_variant not in {"boxed_only", "legacy_think_boxed"}:
                raise ValueError(
                    "data.val_format_prompt_variant must be one of {'boxed_only', 'legacy_think_boxed'}, "
                    f"got {self.val_format_prompt_variant}"
                )
        self.override_chat_template = get_abs_path(self.override_chat_template, prompt="Chat template file")
        self.curriculum_bucket_order_path = get_abs_path(
            self.curriculum_bucket_order_path, prompt="Curriculum bucket order file"
        )
        self.curriculum_mu_init_path = get_abs_path(
            self.curriculum_mu_init_path, prompt="Curriculum mu-init stats file"
        )
        if self.curriculum_mode == "offline_fixed" and self.curriculum_backend != "prebuilt":
            raise ValueError("data.curriculum_mode=offline_fixed currently supports only data.curriculum_backend=prebuilt")
        if self.curriculum_mode == "offline_fixed" and not self.curriculum_bucket_order_path:
            raise ValueError(
                "data.curriculum_mode=offline_fixed requires data.curriculum_bucket_order_path to an existing JSON file"
            )
        if self.curriculum_mode == "self_paced_ema" and self.curriculum_backend != "prebuilt":
            raise ValueError(
                "data.curriculum_mode=self_paced_ema currently supports only data.curriculum_backend=prebuilt"
            )


@dataclass
class AlgorithmConfig:
    gamma: float = 1.0
    """discount factor for ppo gae advantage estimator"""
    lam: float = 1.0
    """lambda value for ppo gae advantage estimator"""
    adv_estimator: str = "grpo"
    """advantage estimator, support `gae`, `grpo`, `reinforce_plus_plus`, `remax`, `rloo`"""
    reward_mode: str = "scalar_mean"
    """reward mode: `scalar_mean` (default), `scalar_exact`, or `cellwise`"""
    disable_kl: bool = False
    """disable reference model"""
    use_kl_loss: bool = False
    """use kl loss instead of kl in reward"""
    kl_penalty: str = "kl"
    """kl penalty type, support `kl`, `abs`, `mse`, `low_var_kl`, `full`"""
    kl_coef: float = 1e-3
    """kl coefficient"""
    kl_type: str = "fixed"
    """kl controller type, support `fixed`, `adaptive`"""
    kl_horizon: float = 10000.0
    """kl horizon for adaptive kl controller"""
    kl_target: float = 0.1
    """target kl for adaptive kl controller"""
    online_filtering: bool = False
    """use online filtering"""
    filter_key: str = "overall"
    """reward key for filtering samples"""
    filter_low: float = 0.01
    """filter out low reward samples if online filtering"""
    filter_high: float = 0.99
    """filter out high reward samples if online filtering"""
    zero_solve_threshold: float = 0.0
    """threshold below which a sample is counted as zero-solve (default: only zero-reward)"""


@dataclass
class TrainerConfig:
    total_epochs: int = 15
    """total epochs for training"""
    max_steps: Optional[int] = None
    """max steps for training, if specified, total_epochs is ignored"""
    project_name: str = "easy_r1"
    """project name for logger"""
    experiment_name: str = "demo"
    """experiment name for logger"""
    logger: Tuple[str] = ("console", "wandb")
    """logger type, support `console`, `mlflow`, `swanlab`, `tensorboard`, `wandb`"""
    nnodes: int = 1
    """number of nodes for training"""
    n_gpus_per_node: int = 8
    """number of gpus per node for training"""
    max_try_make_batch: int = 20
    """max number of generations for online filtering, -1 means no limit"""
    critic_warmup: int = 0
    """critic warmup steps"""
    val_freq: int = -1
    """validation frequency, -1 means no validation"""
    val_before_train: bool = True
    """validate before training"""
    val_only: bool = False
    """validate only, skip training"""
    val_generations_to_log: int = 0
    """number of generations to log for validation"""
    val_predictions_dump_dir: Optional[str] = None
    """optional directory to dump full per-sample validation predictions and scores"""
    save_freq: int = -1
    """save frequency, -1 means no saving"""
    save_limit: int = -1
    """max number of checkpoints to save, -1 means no limit"""
    save_model_only: bool = False
    """save model only, no optimizer state dict"""
    save_checkpoint_path: Optional[str] = None
    """save checkpoint path, if not specified, use `checkpoints/project_name/experiment_name`"""
    load_checkpoint_path: Optional[str] = None
    """load checkpoint path"""
    ray_timeline: Optional[str] = None
    """file to save ray timeline"""
    find_last_checkpoint: bool = True
    """automatically find the last checkpoint in the save checkpoint path to resume training"""

    def post_init(self):
        if self.save_checkpoint_path is None:
            self.save_checkpoint_path = os.path.join("checkpoints", self.project_name, self.experiment_name)

        self.save_checkpoint_path = os.path.abspath(self.save_checkpoint_path)  # may be not exist
        self.load_checkpoint_path = get_abs_path(self.load_checkpoint_path, prompt="Model checkpoint")
        if self.val_predictions_dump_dir is not None:
            self.val_predictions_dump_dir = os.path.abspath(self.val_predictions_dump_dir)


@dataclass
class PPOConfig:
    data: DataConfig = field(default_factory=DataConfig)
    worker: WorkerConfig = field(default_factory=WorkerConfig)
    algorithm: AlgorithmConfig = field(default_factory=AlgorithmConfig)
    trainer: TrainerConfig = field(default_factory=TrainerConfig)

    def post_init(self):
        self.worker.rollout.prompt_length = self.data.max_prompt_length
        self.worker.rollout.response_length = self.data.max_response_length
        self.worker.rollout.trust_remote_code = self.worker.actor.model.trust_remote_code
        self.worker.actor.disable_kl = self.algorithm.disable_kl
        self.worker.actor.use_kl_loss = self.algorithm.use_kl_loss
        self.worker.actor.kl_penalty = self.algorithm.kl_penalty
        self.worker.actor.kl_coef = self.algorithm.kl_coef

        dataset_mode = (self.data.dataset_mode or "none").lower()
        if dataset_mode in {"integer", "bbox"}:
            self.worker.reward.reward_function_kwargs.setdefault("dataset_mode", dataset_mode)

    def deep_post_init(self):
        recursive_post_init(self)

    def to_dict(self):
        return asdict(self)

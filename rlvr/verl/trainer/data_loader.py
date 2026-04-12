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

import os
from pathlib import Path
from typing import Optional

import torch
from torch.utils.data import RandomSampler, SequentialSampler
from torchdata.stateful_dataloader import StatefulDataLoader
from transformers import PreTrainedTokenizer, ProcessorMixin

from ..utils.dataset import RLHFDataset, collate_fn
from .config import DataConfig
from .curriculum import (
    RankUnlockBucketSampler,
    SelfPacedEMABucketSampler,
    build_bucket2indices,
    load_bucket_accuracy_map,
    load_bucket_order,
)


def _val_name_from_source(src: str) -> str:
    """
    Turn a val source like:
      - 'Tanvirul/symrl@test_iid'  -> 'symrl@test_iid'
      - 'Tanvirul/symrl@test_ood'  -> 'symrl@test_ood'
      - '.../test-iid.parquet'     -> 'test-iid'
      - 'Tanvirul/symrl/validation'-> 'symrl@validation'
    into a unique, readable key.
    """
    # HF repo with '@split'
    if "@" in src and not os.path.exists(src):
        repo, split = src.split("@", 1)
        return f"{repo.split('/')[-1]}@{split}"

    # HF 'repo/split' style (fallback)
    parts = src.split("/")
    if len(parts) >= 2 and not src.endswith(".parquet") and not os.path.exists(src):
        repo = parts[-2]
        split = parts[-1]
        return f"{repo}@{split}"

    # file path(s): use stem
    stem = Path(src).stem
    return stem or "val"


def create_dataloader(
    config: DataConfig,
    tokenizer: PreTrainedTokenizer,
    processor: Optional[ProcessorMixin],
    *,
    model_type: Optional[str] = None,
) -> None:
    train_dataset = RLHFDataset(
        data_path=config.train_files,
        tokenizer=tokenizer,
        processor=processor,
        model_type=model_type,
        dataset_mode=config.dataset_mode,
        prompt_key=config.prompt_key,
        answer_key=config.answer_key,
        image_key=config.image_key,
        video_key=config.video_key,
        image_dir=config.image_dir,
        video_fps=config.video_fps,
        max_prompt_length=config.max_prompt_length,
        truncation="right",
        format_prompt=config.format_prompt,
        format_prompt_variant=config.format_prompt_variant,
        min_pixels=config.min_pixels,
        max_pixels=config.max_pixels,
        filter_overlong_prompts=config.filter_overlong_prompts,
        filter_overlong_prompts_workers=config.filter_overlong_prompts_workers,
        log_dataset_download_status=config.log_dataset_download_status,
    )
    curriculum_sampler = None

    # use sampler for better ckpt resume
    if config.curriculum_mode == "none":
        if config.shuffle:
            train_dataloader_generator = torch.Generator()
            train_dataloader_generator.manual_seed(config.seed)
            sampler = RandomSampler(data_source=train_dataset, generator=train_dataloader_generator)
        else:
            sampler = SequentialSampler(data_source=train_dataset)
    else:
        if config.curriculum_backend != "prebuilt":
            raise NotImplementedError(
                f"data.curriculum_backend={config.curriculum_backend} is not implemented. "
                "Supported curriculum backend: prebuilt."
            )
        if "bucket_id_str" not in train_dataset.dataset.column_names:
            available = ", ".join(sorted(train_dataset.dataset.column_names))
            raise ValueError(
                "Curriculum mode requires dataset column `bucket_id_str`, "
                f"but available columns are: {available}"
            )
        bucket2indices = build_bucket2indices(train_dataset.dataset["bucket_id_str"])
        if config.curriculum_mode == "offline_fixed":
            bucket_order = load_bucket_order(config.curriculum_bucket_order_path)
            curriculum_sampler = RankUnlockBucketSampler(
                bucket2indices=bucket2indices,
                bucket_order=bucket_order,
                num_samples=len(train_dataset),
                seed=config.seed,
            )
            sampler = curriculum_sampler
            print(
                "[curriculum] mode=offline_fixed "
                f"buckets={curriculum_sampler.total_buckets} k_min={curriculum_sampler.k_min} "
                f"order_path={config.curriculum_bucket_order_path}"
            )
        elif config.curriculum_mode == "self_paced_ema":
            bucket_order = load_bucket_order(config.curriculum_bucket_order_path) if config.curriculum_bucket_order_path else None
            mu_init = (
                load_bucket_accuracy_map(config.curriculum_mu_init_path) if config.curriculum_mu_init_path else None
            )
            curriculum_sampler = SelfPacedEMABucketSampler(
                bucket2indices=bucket2indices,
                bucket_order=bucket_order,
                mu_init=mu_init,
                num_samples=len(train_dataset),
                seed=config.seed,
                alpha0=float(config.curriculum_alpha0),
                eps_floor=config.curriculum_eps_floor,
                beta=float(config.curriculum_beta),
            )
            sampler = curriculum_sampler
            print(
                "[curriculum] mode=self_paced_ema "
                f"buckets={curriculum_sampler.total_buckets} alpha0={curriculum_sampler.alpha0} "
                f"eps_floor={curriculum_sampler.eps_floor:.6f} "
                f"beta={curriculum_sampler.beta} "
                f"mu_init={'stats' if mu_init is not None else 'uniform_0.5'} "
                f"mu_path={config.curriculum_mu_init_path or 'null'} "
                f"order_path={config.curriculum_bucket_order_path or 'null'}"
            )
        else:
            raise NotImplementedError(
                f"data.curriculum_mode={config.curriculum_mode} is not implemented. "
                "Supported modes: none, offline_fixed, self_paced_ema."
            )

    if config.mini_rollout_batch_size is not None:
        train_batch_size = config.mini_rollout_batch_size
    else:
        train_batch_size = config.rollout_batch_size

    train_dataloader = StatefulDataLoader(
        dataset=train_dataset,
        batch_size=train_batch_size,
        sampler=sampler,
        num_workers=config.train_dataloader_num_workers,
        collate_fn=collate_fn,
        pin_memory=False,
        drop_last=True,
    )
    if curriculum_sampler is not None:
        # Expose sampler to trainer for per-step unlock updates and curriculum logging.
        setattr(train_dataloader, "curriculum_sampler", curriculum_sampler)

    # val_dataset = RLHFDataset(
    #     data_path=config.val_files,
    #     tokenizer=tokenizer,
    #     processor=processor,
    #     prompt_key=config.prompt_key,
    #     answer_key=config.answer_key,
    #     image_key=config.image_key,
    #     video_key=config.video_key,
    #     image_dir=config.image_dir,
    #     video_fps=config.video_fps,
    #     max_prompt_length=config.max_prompt_length,
    #     truncation="right",
    #     format_prompt=config.format_prompt,
    #     min_pixels=config.min_pixels,
    #     max_pixels=config.max_pixels,
    #     filter_overlong_prompts=config.filter_overlong_prompts,
    # )

    # if config.val_batch_size == -1:
    #     val_batch_size = len(val_dataset)
    # else:
    #     val_batch_size = config.val_batch_size

    # val_dataloader = StatefulDataLoader(
    #     dataset=val_dataset,
    #     batch_size=val_batch_size,
    #     shuffle=False,
    #     num_workers=8,
    #     collate_fn=collate_fn,
    #     pin_memory=False,
    #     drop_last=False,
    # )

    # assert len(train_dataloader) >= 1
    # assert len(val_dataloader) >= 1
    # print(f"Size of train dataloader: {len(train_dataloader)}")
    # print(f"Size of val dataloader: {len(val_dataloader)}")
    # return train_dataloader, val_dataloader
    val_dataloaders: dict[str, StatefulDataLoader] = {}

    def _get_name(path: str) -> str:
        return _val_name_from_source(path)

    for val_file in config.val_files:
        val_dataset = RLHFDataset(
            data_path=val_file,
            tokenizer=tokenizer,
            processor=processor,
            model_type=model_type,
            dataset_mode=config.dataset_mode,
            prompt_key=config.prompt_key,
            answer_key=config.answer_key,
            image_key=config.image_key,
            image_dir=config.image_dir,
            max_prompt_length=config.max_prompt_length,
            truncation="right",
            format_prompt=config.val_format_prompt or config.format_prompt,
            format_prompt_variant=config.val_format_prompt_variant or config.format_prompt_variant,
            min_pixels=config.min_pixels,
            max_pixels=config.max_pixels,
            filter_overlong_prompts=config.filter_overlong_prompts_val,
            filter_overlong_prompts_workers=config.filter_overlong_prompts_workers_val,
            log_dataset_download_status=config.log_dataset_download_status,
        )

        if config.val_batch_size == -1:
            val_batch_size = len(val_dataset)
        else:
            val_batch_size = config.val_batch_size

        val_dataloader = StatefulDataLoader(
            dataset=val_dataset,
            batch_size=val_batch_size,
            shuffle=False,
            num_workers=config.val_dataloader_num_workers,
            collate_fn=collate_fn,
            pin_memory=False,
            drop_last=False,
        )

        assert len(val_dataloader) >= 1
        name = _get_name(val_file)
        val_dataloaders[name] = val_dataloader
        print(f"Size of val dataloader ({name}): {len(val_dataloader)}")

    assert len(train_dataloader) >= 1
    print(f"Size of train dataloader: {len(train_dataloader)}")
    return train_dataloader, val_dataloaders

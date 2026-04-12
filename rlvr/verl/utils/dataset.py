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

import hashlib
import math
import os
import json
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import torch
from datasets import load_dataset
from jinja2 import Template
from PIL import Image
from PIL.Image import Image as ImageObject
from qwen_vl_utils.vision_process import fetch_video
from torch.utils.data import Dataset
from transformers import PreTrainedTokenizer, ProcessorMixin

from . import torch_functional as VF


def _hf_home_dir() -> Path:
    return Path(os.environ.get("HF_HOME") or (Path.home() / ".cache" / "huggingface"))


def _hub_cache_dir() -> Path:
    return Path(
        os.environ.get("HF_HUB_CACHE")
        or os.environ.get("HUGGINGFACE_HUB_CACHE")
        or (_hf_home_dir() / "hub")
    )


def _datasets_cache_dir() -> Path:
    return Path(os.environ.get("HF_DATASETS_CACHE") or (_hf_home_dir() / "datasets"))


def _dataset_repo_cache_paths(repo_id: str) -> list[Path]:
    safe_hub = repo_id.replace("/", "--")
    safe_ds = repo_id.replace("/", "___")
    return [
        _hub_cache_dir() / f"datasets--{safe_hub}",
        _datasets_cache_dir() / safe_ds,
    ]


def _has_any_dataset_cache(repo_id: str) -> tuple[bool, list[str]]:
    found: list[str] = []
    for path in _dataset_repo_cache_paths(repo_id):
        if path.exists():
            found.append(str(path))
    return len(found) > 0, found


def _stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


def collate_fn(features: list[dict[str, Any]]) -> dict[str, Any]:
    tensors = defaultdict(list)
    non_tensors = defaultdict(list)
    for feature in features:
        for key, value in feature.items():
            if isinstance(value, torch.Tensor):
                tensors[key].append(value)
            else:
                non_tensors[key].append(value)

    for key, value in tensors.items():
        tensors[key] = torch.stack(value, dim=0)

    for key, value in non_tensors.items():
        non_tensors[key] = np.array(value, dtype=object)

    return {**tensors, **non_tensors}


def process_image(
    image: Union[dict[str, Any], ImageObject, str], min_pixels: Optional[int], max_pixels: Optional[int]
) -> ImageObject:
    if isinstance(image, str):
        image = Image.open(image)
    elif isinstance(image, dict):
        if "bytes" in image:
            image = Image.open(BytesIO(image["bytes"]))
        elif "path" in image:
            image = Image.open(str(image["path"]))
        else:
            raise KeyError("image dict must include either 'bytes' or 'path'")
    elif isinstance(image, bytes):
        image = Image.open(BytesIO(image))

    image.load()  # avoid "Too many open files" errors
    if max_pixels is not None and (image.width * image.height) > max_pixels:
        resize_factor = math.sqrt(max_pixels / (image.width * image.height))
        width, height = int(image.width * resize_factor), int(image.height * resize_factor)
        image = image.resize((width, height))

    if min_pixels is not None and (image.width * image.height) < min_pixels:
        resize_factor = math.sqrt(min_pixels / (image.width * image.height))
        width, height = int(image.width * resize_factor), int(image.height * resize_factor)
        image = image.resize((width, height))

    if image.mode != "RGB":
        image = image.convert("RGB")

    return image


def process_video(
    video: str, min_pixels: Optional[int], max_pixels: Optional[int], video_fps: float, return_fps: bool = False
) -> Union[list[ImageObject], tuple[list[ImageObject], list[float]]]:
    vision_info = {"video": video, "min_pixels": min_pixels, "max_pixels": max_pixels, "fps": video_fps}
    return fetch_video(vision_info, return_video_sample_fps=return_fps)


def resolve_qwen_vl_get_rope_index(
    processor: Optional[ProcessorMixin], model_type: Optional[str] = None
):
    """Resolve the multimodal RoPE helper for supported Qwen VLM families."""

    if processor is None:
        return None

    image_processor = getattr(processor, "image_processor", None)
    image_processor_name = image_processor.__class__.__name__ if image_processor is not None else ""
    if "Qwen2VLImageProcessor" not in image_processor_name:
        return None

    normalized_model_type = str(model_type or "").strip().lower()
    if normalized_model_type.startswith("qwen3_5"):
        from ..models.transformers.qwen3_5 import get_rope_index

        return get_rope_index

    processor_name = processor.__class__.__name__
    if "Qwen3VLProcessor" in processor_name:
        from ..models.transformers.qwen3_vl import get_rope_index

        return get_rope_index

    from ..models.transformers.qwen2_vl import get_rope_index

    return get_rope_index


class RLHFDataset(Dataset):
    """
    We assume the dataset contains a column that contains prompts and other information
    """

    def __init__(
        self,
        data_path: str,
        tokenizer: PreTrainedTokenizer,
        processor: Optional[ProcessorMixin],
        model_type: Optional[str] = None,
        dataset_mode: str = "none",
        prompt_key: str = "prompt",
        answer_key: str = "answer",
        image_key: str = "images",
        video_key: str = "videos",
        image_dir: Optional[str] = None,
        video_fps: float = 2.0,
        max_prompt_length: int = 1024,
        truncation: str = "error",
        format_prompt: Optional[str] = None,
        format_prompt_variant: str = "boxed_only",
        min_pixels: Optional[int] = None,
        max_pixels: Optional[int] = None,
        filter_overlong_prompts: bool = True,
        filter_overlong_prompts_workers: int = 16,
        log_dataset_download_status: bool = True,
    ):
        self.tokenizer = tokenizer
        self.processor = processor
        self.model_type = str(model_type or "").strip().lower() or None
        self.dataset_mode = (dataset_mode or "none").lower()
        self.prompt_key = prompt_key
        self.answer_key = answer_key
        self.image_key = image_key
        self.video_key = video_key
        self.image_dir = image_dir
        self.video_fps = video_fps
        self.max_prompt_length = max_prompt_length
        self.truncation = truncation
        self.format_prompt_variant = (format_prompt_variant or "boxed_only").lower()
        self.min_pixels = min_pixels
        self.max_pixels = max_pixels
        self.log_dataset_download_status = bool(log_dataset_download_status)
        if self.dataset_mode not in {"none", "integer", "bbox", "trace"}:
            raise ValueError(f"Unsupported dataset_mode: {self.dataset_mode}")

        original_data_path = data_path
        if "@" in data_path:
            data_path, data_split = data_path.split("@")
        else:
            data_split = "train"

        is_local_dir = os.path.isdir(data_path)
        is_local_file = os.path.isfile(data_path)
        source_kind = "remote_hf" if not (is_local_dir or is_local_file) else ("local_dir" if is_local_dir else "local_file")
        cache_hit_before = False
        cache_paths_before: list[str] = []
        if self.log_dataset_download_status:
            print(
                f"[dataset] source={original_data_path} resolved={data_path} split={data_split} kind={source_kind}"
            )
            if source_kind == "remote_hf":
                cache_hit_before, cache_paths_before = _has_any_dataset_cache(data_path)
                if cache_hit_before:
                    print(f"[dataset] cache_before=HIT path={cache_paths_before[0]}")
                else:
                    print("[dataset] cache_before=MISS (dataset will download if not otherwise cached)")

        if is_local_dir:
            self.dataset_root = Path(data_path).resolve()
            # when we use dataset builder, we should always refer to the train split
            file_type = os.path.splitext(os.listdir(data_path)[0])[-1][1:].replace("jsonl", "json")
            self.dataset = load_dataset(file_type, data_dir=data_path, split=data_split)
        elif is_local_file:
            self.dataset_root = Path(data_path).resolve().parent
            file_type = os.path.splitext(data_path)[-1][1:].replace("jsonl", "json")
            self.dataset = load_dataset(file_type, data_files=data_path, split=data_split)
        else:
            self.dataset_root = None
            # load remote dataset from huggingface hub
            self.dataset = load_dataset(data_path, split=data_split)
            if self.log_dataset_download_status:
                cache_hit_after, cache_paths_after = _has_any_dataset_cache(data_path)
                if cache_hit_before:
                    print("[dataset] cache_after=HIT (reused local cache)")
                elif cache_hit_after:
                    print(f"[dataset] cache_after=HIT (downloaded and cached at {cache_paths_after[0]})")
                else:
                    print("[dataset] cache_after=MISS (cache location not detected; check custom cache env vars)")

        self.format_prompt = None
        if format_prompt:
            with open(format_prompt, encoding="utf-8") as f:
                self.format_prompt = f.read()

        if filter_overlong_prompts:
            total_before = len(self.dataset)
            cache_file_name = self._overlong_filter_cache_file_name(
                original_data_path=original_data_path,
                data_path=data_path,
                data_split=data_split,
            )
            if self.log_dataset_download_status:
                cache_path = Path(cache_file_name)
                cache_shards = list(cache_path.parent.glob(f"{cache_path.stem}*.arrow"))
                cache_status = "HIT" if cache_shards else "MISS"
                print(f"[dataset] overlong_filter_cache={cache_status} path={cache_path}")
            self.dataset = self.dataset.filter(
                self._filter_overlong_prompts_batch,
                batched=True,
                batch_size=32,
                desc="Filtering overlong prompts",
                cache_file_name=cache_file_name,
                load_from_cache_file=True,
                num_proc=filter_overlong_prompts_workers,
            )
            total_after = len(self.dataset)
            dropped = total_before - total_after
            print(
                "[dataset] overlong_filter "
                f"kept={total_after}/{total_before} dropped={dropped} "
                f"max_prompt_length={self.max_prompt_length}"
            )

    def _resolve_media_path(self, raw_path: str) -> str:
        path = Path(str(raw_path))
        if path.is_absolute():
            return str(path)

        candidates: list[Path] = []
        if self.image_dir is not None:
            candidates.append(Path(self.image_dir) / path)
        if self.dataset_root is not None:
            candidates.append(self.dataset_root / path)
        candidates.append(path)

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return str(candidates[0])

    def _normalize_image_entries(self, images: list[Any]) -> list[Any]:
        if not images:
            return images
        normalized: list[Any] = []
        for image in images:
            if isinstance(image, dict):
                if image.get("bytes") is not None:
                    normalized.append(image)
                    continue
                path = image.get("path")
                if path not in (None, ""):
                    normalized.append(self._resolve_media_path(str(path)))
                    continue
            normalized.append(image)
        return normalized

    def _resolve_prompt_answer_keys(self, example: dict[str, Any]) -> tuple[str, str]:
        if self.dataset_mode == "integer":
            dataset_prompt_key, dataset_answer_key = "problem_integer", "answer_integer"
            if dataset_prompt_key in example and dataset_answer_key in example:
                return dataset_prompt_key, dataset_answer_key
        elif self.dataset_mode == "bbox":
            dataset_prompt_key, dataset_answer_key = "problem_bbox", "answer_bbox"
            if dataset_prompt_key in example and dataset_answer_key in example:
                return dataset_prompt_key, dataset_answer_key
        elif self.dataset_mode == "trace":
            if self.prompt_key in example and self.answer_key in example:
                return self.prompt_key, self.answer_key
            if "prompt" in example and "answer_gt" in example:
                return "prompt", "answer_gt"
            # External validation packs are answer-only and keep benchmark-native
            # prompt/ground_truth columns instead of TRACE train-time answer_gt.
            if "prompt" in example and "ground_truth" in example:
                return "prompt", "ground_truth"

        if self.prompt_key not in example or self.answer_key not in example:
            available = ", ".join(sorted(example.keys()))
            raise KeyError(
                "Prompt/answer columns are missing from dataset row. "
                f"Expected ({self.prompt_key}, {self.answer_key}) for dataset_mode={self.dataset_mode}. "
                f"Available keys: {available}"
            )
        return self.prompt_key, self.answer_key

    def _normalize_trace_metadata_fields(self, example: dict[str, Any]) -> dict[str, Any]:
        if self.dataset_mode != "trace":
            return example

        normalized = dict(example)
        for key in ("answer_gt", "evidence_gt", "reward_contract", "trace_ref"):
            value = normalized.get(key)
            if not isinstance(value, str):
                continue
            stripped = value.strip()
            if not stripped or stripped[0] not in "[{":
                continue
            try:
                normalized[key] = json.loads(stripped)
            except json.JSONDecodeError:
                continue
        return normalized

    def _build_messages(self, example: dict[str, Any], prompt_key: Optional[str] = None) -> list[dict[str, Any]]:
        if prompt_key is None:
            prompt_key, _ = self._resolve_prompt_answer_keys(example)

        prompt_str: str = example[prompt_key]
        if self.format_prompt:
            format_prompt = Template(self.format_prompt.strip())
            prompt_str = format_prompt.render(content=prompt_str, format_prompt_variant=self.format_prompt_variant)

        if self.image_key in example:
            images = example.get(self.image_key) or []
            if images and "<image>" not in prompt_str:
                # External validation rows are single-/multi-image answer-only prompts and
                # may omit explicit multimodal placeholders. vLLM requires the placeholders
                # to align with the provided image items, so normalize them here.
                prompt_str = ("<image>" * len(images)) + prompt_str
            # https://huggingface.co/docs/transformers/en/tasks/image_text_to_text
            content_list = []
            for i, content in enumerate(prompt_str.split("<image>")):
                if i != 0:
                    content_list.append({"type": "image"})

                if content:
                    content_list.append({"type": "text", "text": content})

            return [{"role": "user", "content": content_list}]
        elif self.video_key in example:
            content_list = []
            for i, content in enumerate(prompt_str.split("<video>")):
                if i != 0:
                    content_list.append({"type": "video"})

                if content:
                    content_list.append({"type": "text", "text": content})

            return [{"role": "user", "content": content_list}]
        else:
            return [{"role": "user", "content": prompt_str}]

    def _apply_chat_template(self, messages: list[dict[str, Any]]) -> str:
        if self.processor is not None and getattr(self.processor, "chat_template", None):
            return self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        return self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)

    def _get_image_hw(self, image: Any) -> Optional[tuple[int, int]]:
        if hasattr(image, "size"):
            width, height = image.size
            return int(height), int(width)
        if isinstance(image, str):
            with Image.open(image) as img:
                width, height = img.size
                return int(height), int(width)
        if isinstance(image, dict):
            if "bytes" in image and image["bytes"] is not None:
                with Image.open(BytesIO(image["bytes"])) as img:
                    width, height = img.size
                    return int(height), int(width)
            if "path" in image:
                with Image.open(str(image["path"])) as img:
                    width, height = img.size
                    return int(height), int(width)
        return None

    def _get_num_image_tokens(self, image: Any) -> Optional[int]:
        if self.processor is None:
            return None
        image_processor = getattr(self.processor, "image_processor", None)
        if image_processor is None or not hasattr(image_processor, "get_number_of_image_patches"):
            return None
        image_hw = self._get_image_hw(image)
        if image_hw is None:
            return None
        height, width = image_hw
        num_patches = image_processor.get_number_of_image_patches(
            height,
            width,
            {
                "min_pixels": self.min_pixels,
                "max_pixels": self.max_pixels,
            },
        )
        merge_size = getattr(image_processor, "merge_size", 1)
        return int(num_patches // (merge_size**2))

    def _expand_prompt_for_length_only(self, example: dict[str, Any]) -> Optional[str]:
        prompt_key, _ = self._resolve_prompt_answer_keys(example)
        messages = self._build_messages(example, prompt_key=prompt_key)
        prompt = self._apply_chat_template(messages)

        if self.video_key in example:
            return None
        if self.image_key not in example:
            return prompt

        image_token = getattr(self.processor, "image_token", None) if self.processor is not None else None
        if image_token is None:
            return None

        expanded_prompt = prompt
        for image in self._normalize_image_entries(list(example[self.image_key])):
            num_image_tokens = self._get_num_image_tokens(image)
            if num_image_tokens is None:
                return None
            expanded_prompt = expanded_prompt.replace(image_token, "<|placeholder|>" * num_image_tokens, 1)
        return expanded_prompt.replace("<|placeholder|>", image_token)

    def _overlong_filter_cache_file_name(self, *, original_data_path: str, data_path: str, data_split: str) -> str:
        cache_dir = _datasets_cache_dir() / "verl_overlong_prompt_filter"
        cache_dir.mkdir(parents=True, exist_ok=True)
        format_prompt_hash = (
            hashlib.sha256(self.format_prompt.encode("utf-8")).hexdigest() if self.format_prompt is not None else None
        )
        payload = {
            "dataset_fingerprint": getattr(self.dataset, "_fingerprint", None),
            "original_data_path": original_data_path,
            "data_path": data_path,
            "data_split": data_split,
            "tokenizer_name_or_path": getattr(self.tokenizer, "name_or_path", None),
            "processor_name_or_path": getattr(self.processor, "name_or_path", None),
            "processor_class": self.processor.__class__.__name__ if self.processor is not None else None,
            "model_type": self.model_type,
            "dataset_mode": self.dataset_mode,
            "prompt_key": self.prompt_key,
            "answer_key": self.answer_key,
            "image_key": self.image_key,
            "video_key": self.video_key,
            "max_prompt_length": self.max_prompt_length,
            "min_pixels": self.min_pixels,
            "max_pixels": self.max_pixels,
            "video_fps": self.video_fps,
            "format_prompt_hash": format_prompt_hash,
            "format_prompt_variant": self.format_prompt_variant,
        }
        return str(cache_dir / f"{_stable_hash(payload)}.arrow")

    def _filter_overlong_prompts(self, example: dict[str, Any]) -> bool:
        expanded_prompt = self._expand_prompt_for_length_only(example)
        if expanded_prompt is not None:
            input_ids = self.tokenizer(expanded_prompt, add_special_tokens=False)["input_ids"]
            return len(input_ids) <= self.max_prompt_length

        prompt_key, _ = self._resolve_prompt_answer_keys(example)
        messages = self._build_messages(example, prompt_key=prompt_key)
        if self.image_key in example:
            prompt = self._apply_chat_template(messages)
            images = self._normalize_image_entries(list(example[self.image_key]))

            processed_images = [] if len(images) != 0 else None  # text-only data
            for image in images:
                processed_images.append(process_image(image, self.min_pixels, self.max_pixels))

            model_inputs = self.processor(processed_images, [prompt], add_special_tokens=False, return_tensors="pt")
            return model_inputs["input_ids"].size(-1) <= self.max_prompt_length
        elif self.video_key in example:
            prompt = self._apply_chat_template(messages)
            videos = example[self.video_key]
            if self.image_dir is not None and len(videos) != 0 and isinstance(videos[0], str):  # video paths
                videos = [os.path.join(self.image_dir, video) for video in videos]

            processed_videos = [] if len(videos) != 0 else None  # text-only data
            for video in videos:
                processed_videos.append(process_video(video, self.min_pixels, self.max_pixels, self.video_fps))

            model_inputs = self.processor(
                videos=processed_videos, text=[prompt], add_special_tokens=False, return_tensors="pt"
            )
            return model_inputs["input_ids"].size(-1) <= self.max_prompt_length
        else:
            input_ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True)
            return len(input_ids) <= self.max_prompt_length

    def _filter_overlong_prompts_batch(self, batch: dict[str, list[Any]]) -> list[bool]:
        """Fast path for image-backed datasets: cheap token-length estimation plus batched tokenization."""
        row_count = len(next(iter(batch.values()))) if batch else 0
        keep_mask = [False] * row_count
        batched_prompt_indices: list[int] = []
        batched_prompts: list[str] = []

        for row_idx in range(row_count):
            example = {key: values[row_idx] for key, values in batch.items()}
            expanded_prompt = self._expand_prompt_for_length_only(example)
            if expanded_prompt is None:
                keep_mask[row_idx] = self._filter_overlong_prompts(example)
                continue
            batched_prompt_indices.append(row_idx)
            batched_prompts.append(expanded_prompt)

        if batched_prompt_indices:
            tokenized = self.tokenizer(batched_prompts, add_special_tokens=False)
            lengths = [len(input_ids) for input_ids in tokenized["input_ids"]]
            for row_idx, prompt_length in zip(batched_prompt_indices, lengths):
                keep_mask[row_idx] = int(prompt_length) <= self.max_prompt_length

        return keep_mask

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        example: dict = self._normalize_trace_metadata_fields(dict(self.dataset[index]))
        prompt_key, answer_key = self._resolve_prompt_answer_keys(example)
        messages = self._build_messages(example, prompt_key=prompt_key)
        example.pop(prompt_key, None)

        if self.image_key in example:
            prompt = self._apply_chat_template(messages)
            images = example.pop(self.image_key)
            images = self._normalize_image_entries(list(images))

            processed_images = [] if len(images) != 0 else None  # text-only data
            for image in images:
                processed_images.append(process_image(image, self.min_pixels, self.max_pixels))

            model_inputs = self.processor(processed_images, [prompt], add_special_tokens=False, return_tensors="pt")
            input_ids = model_inputs.pop("input_ids")[0]
            attention_mask = model_inputs.pop("attention_mask")[0]
            example["multi_modal_data"] = {"images": images}
        elif self.video_key in example:
            prompt = self._apply_chat_template(messages)
            videos = example.pop(self.video_key)
            if self.image_dir is not None and len(videos) != 0 and isinstance(videos[0], str):  # video paths
                videos = [os.path.join(self.image_dir, video) for video in videos]

            processed_videos = [] if len(videos) != 0 else None  # text-only data
            video_fps_list = []
            for video in videos:
                processed_video, video_fps = process_video(
                    video, self.min_pixels, self.max_pixels, self.video_fps, return_fps=True
                )
                processed_videos.append(processed_video)
                video_fps_list.append(video_fps)

            model_inputs = self.processor(
                videos=processed_videos, text=[prompt], add_special_tokens=False, return_tensors="pt"
            )
            if "second_per_grid_ts" in self.processor.model_input_names:
                model_inputs["second_per_grid_ts"] = [2.0 / video_sample_fps for video_sample_fps in video_fps_list]

            input_ids = model_inputs.pop("input_ids")[0]
            attention_mask = model_inputs.pop("attention_mask")[0]
            example["multi_modal_data"] = {"videos": videos}
        else:
            prompt = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
            model_inputs = self.tokenizer([prompt], add_special_tokens=False, return_tensors="pt")
            input_ids = model_inputs.pop("input_ids")[0]
            attention_mask = model_inputs.pop("attention_mask")[0]

        qwen_vl_get_rope_index = resolve_qwen_vl_get_rope_index(self.processor, self.model_type)
        if qwen_vl_get_rope_index is not None:
            # qwen-vl mrope
            rope_kwargs = {
                "input_ids": input_ids,
                "image_grid_thw": model_inputs.get("image_grid_thw", None),
                "video_grid_thw": model_inputs.get("video_grid_thw", None),
                "second_per_grid_ts": model_inputs.get("second_per_grid_ts", None),
                "attention_mask": attention_mask,
            }
            if self.model_type is not None and self.model_type.startswith("qwen3_5"):
                rope_kwargs["mm_token_type_ids"] = model_inputs.get("mm_token_type_ids", None)
            vision_position_ids = qwen_vl_get_rope_index(
                self.processor,
                **rope_kwargs,
            )  # (3, seq_length)
            text_position_ids = torch.arange(len(input_ids)).unsqueeze(0)  # (1, seq_length)
            position_ids = torch.cat((text_position_ids, vision_position_ids), dim=0)  # (4, seq_length)
        else:
            position_ids = torch.clip(attention_mask.cumsum(dim=0) - 1, min=0, max=None)  # (seq_length,)

        input_ids, attention_mask, position_ids = VF.postprocess_data(
            input_ids=input_ids,
            attention_mask=attention_mask,
            position_ids=position_ids,
            max_length=self.max_prompt_length,
            pad_token_id=self.tokenizer.pad_token_id,
            left_pad=True,
            truncation=self.truncation,
        )
        raw_prompt_ids = self.tokenizer.encode(prompt, add_special_tokens=False)
        if len(raw_prompt_ids) > self.max_prompt_length:
            if self.truncation == "left":
                raw_prompt_ids = raw_prompt_ids[-self.max_prompt_length :]
            elif self.truncation == "right":
                raw_prompt_ids = raw_prompt_ids[: self.max_prompt_length]
            elif self.truncation == "error":
                raise RuntimeError(f"Prompt length {len(raw_prompt_ids)} is longer than {self.max_prompt_length}.")

        example["input_ids"] = input_ids
        example["attention_mask"] = attention_mask
        example["position_ids"] = position_ids
        example["raw_prompt_ids"] = raw_prompt_ids
        ground_truth = example.pop(answer_key)
        if isinstance(ground_truth, dict) and "type" in ground_truth and "value" in ground_truth:
            example["answer_gt"] = ground_truth
            example["ground_truth"] = ground_truth.get("value")
        else:
            example["ground_truth"] = ground_truth
        return example

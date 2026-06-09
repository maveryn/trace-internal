from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
import torch
from datasets import concatenate_datasets, load_dataset
from jinja2 import Template
from omegaconf import DictConfig, ListConfig
from PIL import Image
from PIL.Image import Image as ImageObject
from qwen_vl_utils.vision_process import fetch_video
from torch.utils.data import Dataset
from transformers import PreTrainedTokenizer, ProcessorMixin

import verl.utils.torch_functional as VF
from verl.utils.model import compute_position_id_with_mask
from verl.utils.trace_mode import (
    normalize_trace_output_mode,
    resolve_trace_prompt_key,
    resolve_trace_system_prompt,
)
from .rl_dataset import PerBatchDomainSampler, _parse_per_batch_domain_weights


def _stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str).encode("utf-8")).hexdigest()


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

    image.load()
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
):
    vision_info = {"video": video, "min_pixels": min_pixels, "max_pixels": max_pixels, "fps": video_fps}
    return fetch_video(vision_info, return_video_sample_fps=return_fps)


def resolve_qwen_vl_get_rope_index(
    processor: Optional[ProcessorMixin], model_type: Optional[str] = None
):
    if processor is None:
        return None

    image_processor = getattr(processor, "image_processor", None)
    image_processor_name = image_processor.__class__.__name__ if image_processor is not None else ""
    if "Qwen2VLImageProcessor" not in image_processor_name:
        return None

    normalized_model_type = str(model_type or "").strip().lower()
    if normalized_model_type.startswith("qwen3_5"):
        from ...models.transformers.qwen3_5 import get_rope_index

        return get_rope_index

    processor_name = processor.__class__.__name__
    if "Qwen3VLProcessor" in processor_name:
        from ...models.transformers.qwen3_vl import get_rope_index

        return get_rope_index

    from ...models.transformers.qwen2_vl import get_rope_index

    return get_rope_index


class TraceRLHFDataset(Dataset):
    """TRACE-specific RLHF dataset adapter for the Vero-derived PPO stack."""

    def __init__(
        self,
        data_files: str | list[str],
        tokenizer: PreTrainedTokenizer,
        config: DictConfig,
        processor: Optional[ProcessorMixin] = None,
    ):
        if not isinstance(data_files, (list, ListConfig)):
            data_files = [data_files]

        self.data_files = copy.deepcopy(list(data_files))
        self.tokenizer = tokenizer
        self.processor = processor
        self.config = config
        self.dataset_mode = "trace"
        self.trace_output_mode = normalize_trace_output_mode(config.get("trace_output_mode", "answer"))
        self.prompt_key = resolve_trace_prompt_key(
            config.get("prompt_key", "auto"),
            trace_output_mode=self.trace_output_mode,
        )
        self.answer_key = config.get("answer_key", "answer_gt")
        self.image_key = config.get("image_key", "images")
        self.video_key = config.get("video_key", "videos")
        self.image_dir = config.get("image_root", None) or config.get("image_dir", None)
        self.video_fps = config.get("video_fps", 2.0)
        self.max_prompt_length = config.get("max_prompt_length", 1024)
        self.truncation = config.get("truncation", "error")
        self.min_pixels = config.get("min_pixels", None)
        self.max_pixels = config.get("max_pixels", None)
        self.filter_overlong_prompts = bool(config.get("filter_overlong_prompts", True))
        self.filter_overlong_prompts_workers = int(config.get("filter_overlong_prompts_workers", 1))
        self.log_dataset_download_status = bool(config.get("log_dataset_download_status", True))
        self.default_data_source = str(config.get("default_data_source", "trace"))
        self.domain_sampling_key = str(config.get("domain_sampling_key", "domain") or "domain")
        self.per_batch_domain_weights = self._resolve_per_batch_domain_weights(
            config.get("per_batch_domain_weights", None)
        )
        self.domain2indices: dict[str, np.ndarray] | None = None
        self.domain_weights: dict[str, float] | None = None
        self.model_type = self._load_model_type_from_candidate(getattr(tokenizer, "name_or_path", None))

        if bool(config.get("disable_system_prompt", False)):
            self.system_prompt = None
        else:
            self.system_prompt = self._load_prompt_text(
                resolve_trace_system_prompt(
                    config.get("system_prompt", "auto"),
                    trace_output_mode=self.trace_output_mode,
                )
            )
        self.format_prompt = self._load_prompt_text(config.get("format_prompt"))
        self.format_prompt_variant = (config.get("format_prompt_variant", "boxed_only") or "boxed_only").lower()

        datasets_list = [self._load_single_source(source) for source in self.data_files]
        self.dataset = datasets_list[0] if len(datasets_list) == 1 else concatenate_datasets(datasets_list)

        if self.filter_overlong_prompts:
            total_before = len(self.dataset)
            cache_file_name = self._overlong_filter_cache_file_name()
            self.dataset = self.dataset.filter(
                self._filter_overlong_prompts_batch,
                batched=True,
                batch_size=32,
                desc="Filtering overlong TRACE prompts",
                cache_file_name=cache_file_name,
                load_from_cache_file=True,
                num_proc=self.filter_overlong_prompts_workers,
            )
            total_after = len(self.dataset)
            print(
                "[dataset] overlong_filter "
                f"kept={total_after}/{total_before} dropped={total_before - total_after} "
                f"max_prompt_length={self.max_prompt_length}"
            )

        self._prepare_domain_sampling()

    def _resolve_per_batch_domain_weights(self, raw_value: Any) -> dict[str, float] | str | None:
        if raw_value is None:
            return None
        if isinstance(raw_value, str):
            normalized = raw_value.strip()
            if not normalized or normalized.lower() in {"none", "null", "false", "off"}:
                return None
            if normalized.lower() in {"auto", "uniform", "__auto__", "__uniform__"}:
                return "auto"
            return _parse_per_batch_domain_weights(normalized)
        return _parse_per_batch_domain_weights(raw_value)

    def _prepare_domain_sampling(self) -> None:
        if not self.per_batch_domain_weights:
            return
        if self.domain_sampling_key not in self.dataset.column_names:
            raise KeyError(
                "per_batch_domain_weights requires column "
                f"{self.domain_sampling_key!r}; available columns: {sorted(self.dataset.column_names)}"
            )

        values = np.asarray([str(value) for value in self.dataset[self.domain_sampling_key]], dtype=object)
        if values.size == 0:
            raise ValueError("Dataset is empty; cannot build TRACE per-batch domain sampler")

        available_domains = sorted(str(value) for value in np.unique(values) if str(value))
        if not available_domains:
            raise ValueError(f"Column {self.domain_sampling_key!r} contains no usable domain values")

        if self.per_batch_domain_weights == "auto":
            domain_weights = {domain: 1.0 / len(available_domains) for domain in available_domains}
        else:
            filtered_weights = {
                domain: weight
                for domain, weight in self.per_batch_domain_weights.items()
                if domain in set(available_domains)
            }
            if not filtered_weights:
                raise ValueError(
                    "No per_batch_domain_weights entries matched TRACE "
                    f"{self.domain_sampling_key!r} values: {available_domains}"
                )
            total = float(sum(filtered_weights.values()))
            domain_weights = {domain: float(weight) / total for domain, weight in filtered_weights.items()}

        self.domain_weights = domain_weights
        self.domain2indices = {
            domain: np.where(values == domain)[0]
            for domain in domain_weights
        }
        print(
            "[dataset] per_batch_domain_sampling "
            f"key={self.domain_sampling_key} weights={json.dumps(self.domain_weights, sort_keys=True)}"
        )

    def build_domain_sampler(self, batch_size: int, seed: int = 18, shuffle: bool = True) -> PerBatchDomainSampler:
        if self.domain2indices is None or self.domain_weights is None:
            raise RuntimeError("per_batch_domain_weights is not configured for this TRACE dataset")
        return PerBatchDomainSampler(
            domain2indices=self.domain2indices,
            domain_weights=self.domain_weights,
            batch_size=batch_size,
            total_size=len(self.dataset),
            seed=seed,
            shuffle=shuffle,
        )

    def _load_prompt_text(self, configured_value: Optional[str]) -> Optional[str]:
        if not configured_value:
            return None
        if isinstance(configured_value, str) and os.path.exists(configured_value):
            with open(configured_value, encoding="utf-8") as handle:
                return handle.read()
        return configured_value

    def _load_model_type_from_candidate(self, path: Optional[str]) -> Optional[str]:
        if not isinstance(path, str) or not path:
            return None
        candidate = os.path.expanduser(path)
        if os.path.isfile(candidate):
            config_path = candidate if os.path.basename(candidate) == "config.json" else None
        elif os.path.isdir(candidate):
            config_path = os.path.join(candidate, "config.json")
        else:
            return None
        if config_path is None or not os.path.isfile(config_path):
            return None
        try:
            with open(config_path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return None
        model_type = payload.get("model_type")
        return str(model_type).strip().lower() if isinstance(model_type, str) else None

    def _load_single_source(self, raw_source: str):
        source = str(raw_source)
        if "@" in source:
            data_path, data_split = source.rsplit("@", 1)
        else:
            data_path, data_split = source, "train"

        is_local_dir = os.path.isdir(data_path)
        is_local_file = os.path.isfile(data_path)

        if self.log_dataset_download_status:
            source_kind = "remote_hf" if not (is_local_dir or is_local_file) else ("local_dir" if is_local_dir else "local_file")
            print(f"[dataset] source={source} resolved={data_path} split={data_split} kind={source_kind}")

        if is_local_dir:
            self.dataset_root = Path(data_path).resolve()
            first_entry = sorted(os.listdir(data_path))[0]
            file_type = os.path.splitext(first_entry)[-1][1:].replace("jsonl", "json")
            return load_dataset(file_type, data_dir=data_path, split=data_split)
        if is_local_file:
            self.dataset_root = Path(data_path).resolve().parent
            file_type = os.path.splitext(data_path)[-1][1:].replace("jsonl", "json")
            return load_dataset(file_type, data_files=data_path, split=data_split)

        self.dataset_root = None
        return load_dataset(data_path, split=data_split)

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
            elif isinstance(image, str):
                normalized.append(self._resolve_media_path(image))
                continue
            normalized.append(image)
        return normalized

    def _resolve_prompt_answer_keys(self, example: dict[str, Any]) -> tuple[str, str]:
        if self.prompt_key in example and self.answer_key in example:
            return self.prompt_key, self.answer_key
        if self.prompt_key == "prompt_answer" and "prompt_answer_only" in example and self.answer_key in example:
            return "prompt_answer_only", self.answer_key
        if "prompt" in example and "answer_gt" in example:
            return "prompt", "answer_gt"
        if "prompt" in example and "ground_truth" in example:
            return "prompt", "ground_truth"

        available = ", ".join(sorted(example.keys()))
        raise KeyError(
            "Prompt/answer columns are missing from TRACE dataset row. "
            f"Expected ({self.prompt_key}, {self.answer_key}). Available keys: {available}"
        )

    def _normalize_trace_metadata_fields(self, example: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(example)
        for key in ("answer_gt", "annotation_gt", "reward_contract", "trace_ref", "metadata", "extra_info"):
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

        prompt_str = str(example[prompt_key])
        if self.format_prompt:
            prompt_template = Template(self.format_prompt.strip())
            prompt_str = prompt_template.render(content=prompt_str, format_prompt_variant=self.format_prompt_variant)

        messages: list[dict[str, Any]] = []
        if self.system_prompt and self.system_prompt.strip():
            messages.append({"role": "system", "content": self.system_prompt.strip()})

        if self.image_key in example:
            images = example.get(self.image_key) or []
            if images and "<image>" not in prompt_str:
                prompt_str = ("<image>" * len(images)) + prompt_str

            content_list = []
            for index, content in enumerate(prompt_str.split("<image>")):
                if index != 0:
                    content_list.append({"type": "image"})
                if content:
                    content_list.append({"type": "text", "text": content})
            messages.append({"role": "user", "content": content_list})
            return messages

        if self.video_key in example:
            content_list = []
            for index, content in enumerate(prompt_str.split("<video>")):
                if index != 0:
                    content_list.append({"type": "video"})
                if content:
                    content_list.append({"type": "text", "text": content})
            messages.append({"role": "user", "content": content_list})
            return messages

        messages.append({"role": "user", "content": prompt_str})
        return messages

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
        image_kwargs: dict[str, Any] = {}
        if self.min_pixels is not None:
            image_kwargs["min_pixels"] = self.min_pixels
        if self.max_pixels is not None:
            image_kwargs["max_pixels"] = self.max_pixels
        num_patches = image_processor.get_number_of_image_patches(
            height,
            width,
            image_kwargs,
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

    def _overlong_filter_cache_file_name(self) -> str:
        cache_dir = Path(os.environ.get("HF_DATASETS_CACHE", Path.home() / ".cache/huggingface/datasets"))
        cache_dir = cache_dir / "trace_overlong_prompt_filter"
        cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset_fingerprint": getattr(self.dataset, "_fingerprint", None),
            "data_files": list(self.data_files),
            "tokenizer_name_or_path": getattr(self.tokenizer, "name_or_path", None),
            "processor_name_or_path": getattr(self.processor, "name_or_path", None),
            "model_type": self.model_type,
            "prompt_key": self.prompt_key,
            "answer_key": self.answer_key,
            "max_prompt_length": self.max_prompt_length,
            "min_pixels": self.min_pixels,
            "max_pixels": self.max_pixels,
            "video_fps": self.video_fps,
            "system_prompt": self.system_prompt,
            "format_prompt": self.format_prompt,
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
            processed_images = [] if len(images) != 0 else None
            for image in images:
                processed_images.append(process_image(image, self.min_pixels, self.max_pixels))
            model_inputs = self.processor(processed_images, [prompt], add_special_tokens=False, return_tensors="pt")
            return model_inputs["input_ids"].size(-1) <= self.max_prompt_length
        if self.video_key in example:
            prompt = self._apply_chat_template(messages)
            videos = example[self.video_key]
            if self.image_dir is not None and len(videos) != 0 and isinstance(videos[0], str):
                videos = [os.path.join(self.image_dir, video) for video in videos]
            processed_videos = [] if len(videos) != 0 else None
            for video in videos:
                processed_videos.append(process_video(video, self.min_pixels, self.max_pixels, self.video_fps))
            model_inputs = self.processor(
                videos=processed_videos,
                text=[prompt],
                add_special_tokens=False,
                return_tensors="pt",
            )
            return model_inputs["input_ids"].size(-1) <= self.max_prompt_length

        input_ids = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        return len(input_ids) <= self.max_prompt_length

    def _filter_overlong_prompts_batch(self, batch: dict[str, list[Any]]) -> list[bool]:
        row_count = len(next(iter(batch.values()))) if batch else 0
        keep_mask = [False] * row_count
        batched_prompt_indices: list[int] = []
        batched_prompts: list[str] = []

        for row_idx in range(row_count):
            example = {key: values[row_idx] for key, values in batch.items()}
            example = self._normalize_trace_metadata_fields(example)
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

    def __len__(self) -> int:
        return len(self.dataset)

    def __getitem__(self, index: int) -> dict[str, Any]:
        example: dict[str, Any] = self._normalize_trace_metadata_fields(dict(self.dataset[index]))
        prompt_key, answer_key = self._resolve_prompt_answer_keys(example)
        messages = self._build_messages(example, prompt_key=prompt_key)
        example.pop(prompt_key, None)

        if self.image_key in example:
            prompt = self._apply_chat_template(messages)
            images = self._normalize_image_entries(list(example.pop(self.image_key)))
            source_image_sizes: list[tuple[int, int]] = []
            for image in images:
                image_hw = self._get_image_hw(image)
                if image_hw is None:
                    continue
                height, width = image_hw
                source_image_sizes.append((int(width), int(height)))
            if source_image_sizes:
                example["image_sizes"] = source_image_sizes
            processed_images = [] if len(images) != 0 else None
            for image in images:
                processed_images.append(process_image(image, self.min_pixels, self.max_pixels))
            model_inputs = self.processor(processed_images, [prompt], add_special_tokens=False, return_tensors="pt")
            input_ids = model_inputs.pop("input_ids")
            attention_mask = model_inputs.pop("attention_mask")
            example["multi_modal_data"] = {"image": processed_images}
        elif self.video_key in example:
            prompt = self._apply_chat_template(messages)
            videos = example.pop(self.video_key)
            if self.image_dir is not None and len(videos) != 0 and isinstance(videos[0], str):
                videos = [os.path.join(self.image_dir, video) for video in videos]

            processed_videos = [] if len(videos) != 0 else None
            video_fps_list = []
            for video in videos:
                processed_video, video_fps = process_video(
                    video, self.min_pixels, self.max_pixels, self.video_fps, return_fps=True
                )
                processed_videos.append(processed_video)
                video_fps_list.append(video_fps)

            model_inputs = self.processor(
                videos=processed_videos,
                text=[prompt],
                add_special_tokens=False,
                return_tensors="pt",
            )
            if "second_per_grid_ts" in self.processor.model_input_names:
                model_inputs["second_per_grid_ts"] = [2.0 / video_sample_fps for video_sample_fps in video_fps_list]

            input_ids = model_inputs.pop("input_ids")
            attention_mask = model_inputs.pop("attention_mask")
            example["multi_modal_data"] = {"video": [video.numpy() for video in processed_videos]}
        else:
            prompt = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
            model_inputs = self.tokenizer([prompt], add_special_tokens=False, return_tensors="pt")
            input_ids = model_inputs.pop("input_ids")
            attention_mask = model_inputs.pop("attention_mask")

        input_ids, attention_mask = VF.postprocess_data(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_length=self.max_prompt_length,
            pad_token_id=self.tokenizer.pad_token_id,
            left_pad=True,
            truncation=self.truncation,
        )

        qwen_vl_get_rope_index = resolve_qwen_vl_get_rope_index(self.processor, self.model_type)
        if qwen_vl_get_rope_index is not None:
            rope_kwargs = {
                "input_ids": input_ids[0],
                "image_grid_thw": model_inputs.get("image_grid_thw", None),
                "video_grid_thw": model_inputs.get("video_grid_thw", None),
                "second_per_grid_ts": model_inputs.get("second_per_grid_ts", None),
                "attention_mask": attention_mask[0],
            }
            if self.model_type is not None and self.model_type.startswith("qwen3_5"):
                rope_kwargs["mm_token_type_ids"] = model_inputs.get("mm_token_type_ids", None)
            vision_position_ids = qwen_vl_get_rope_index(self.processor, **rope_kwargs)
            valid_mask = attention_mask[0].bool()
            text_position_ids = torch.ones((1, len(input_ids[0])), dtype=torch.long)
            text_position_ids[0, valid_mask] = torch.arange(valid_mask.sum().item())
            position_ids = torch.cat((text_position_ids, vision_position_ids), dim=0)
        else:
            position_ids = compute_position_id_with_mask(attention_mask)[0]

        raw_prompt_ids = self.tokenizer.encode(prompt, add_special_tokens=False)
        if len(raw_prompt_ids) > self.max_prompt_length:
            if self.truncation == "left":
                raw_prompt_ids = raw_prompt_ids[-self.max_prompt_length :]
            elif self.truncation == "right":
                raw_prompt_ids = raw_prompt_ids[: self.max_prompt_length]
            elif self.truncation == "middle":
                left_half = self.max_prompt_length // 2
                right_half = self.max_prompt_length - left_half
                raw_prompt_ids = raw_prompt_ids[:left_half] + raw_prompt_ids[-right_half:]
            elif self.truncation == "error":
                raise RuntimeError(f"Prompt length {len(raw_prompt_ids)} is longer than {self.max_prompt_length}.")

        example["input_ids"] = input_ids[0]
        example["attention_mask"] = attention_mask[0]
        example["position_ids"] = position_ids
        example["raw_prompt_ids"] = raw_prompt_ids

        ground_truth = example.pop(answer_key)
        if isinstance(ground_truth, dict) and "type" in ground_truth and "value" in ground_truth:
            example["answer_gt"] = ground_truth
            reward_ground_truth = ground_truth.get("value")
            example["ground_truth"] = reward_ground_truth
        else:
            reward_ground_truth = ground_truth
            example["ground_truth"] = ground_truth

        existing_reward_model = example.get("reward_model")
        reward_model = dict(existing_reward_model) if isinstance(existing_reward_model, dict) else {}
        reward_model.setdefault("style", "rule")
        reward_model["ground_truth"] = reward_ground_truth
        example["reward_model"] = reward_model

        existing_extra_info = example.get("extra_info")
        extra_info = dict(existing_extra_info) if isinstance(existing_extra_info, dict) else {}
        extra_info.setdefault("prompt", prompt)
        for key in (
            "answer_gt",
            "annotation_gt",
            "reward_contract",
            "trace_ref",
            "metadata",
            "query_id",
            "scene_variant",
            "source_dataset_index",
            "curriculum_probe_rollout_count",
            "curriculum_probe_positive_rollout_count",
            "curriculum_probe_solve_rate",
            "image_size",
            "image_sizes",
            "benchmark_id",
            "parser_family",
        ):
            if key in example:
                extra_info[key] = example[key]
        example["extra_info"] = extra_info
        example.setdefault("data_source", self.default_data_source)

        return example

from __future__ import annotations

import itertools
from typing import Optional

import torch


def _get_vision_position_ids(
    *,
    start_position: int,
    grid_thw: torch.Tensor,
    spatial_merge_size: int,
    device: torch.device,
) -> torch.Tensor:
    """Build one 3-axis vision RoPE block for a single Qwen3.5 image/video grid."""

    llm_grid_t = int(grid_thw[0].item())
    llm_grid_h = int(grid_thw[1].item()) // int(spatial_merge_size)
    llm_grid_w = int(grid_thw[2].item()) // int(spatial_merge_size)

    image_seq_length = llm_grid_h * llm_grid_w * llm_grid_t
    position_width = torch.arange(start_position, start_position + llm_grid_w, device=device).repeat(
        llm_grid_h * llm_grid_t
    )
    position_height = torch.arange(start_position, start_position + llm_grid_h, device=device).repeat_interleave(
        llm_grid_w * llm_grid_t
    )
    position_temporal = torch.full((image_seq_length,), start_position, device=device, dtype=torch.long)
    return torch.stack([position_temporal, position_height, position_width], dim=0)


def get_rope_index(
    processor,
    input_ids: torch.Tensor,
    mm_token_type_ids: Optional[torch.Tensor] = None,
    image_grid_thw: Optional[torch.Tensor] = None,
    video_grid_thw: Optional[torch.Tensor] = None,
    attention_mask: Optional[torch.Tensor] = None,
    **kwargs,
) -> torch.Tensor:
    """Generate Qwen3.5 multimodal RoPE indices for one unbatched example.

    The upstream Qwen3.5 implementation groups tokens by `mm_token_type_ids`
    instead of scanning for image/video token ids directly.
    """

    if mm_token_type_ids is None:
        raise ValueError("Qwen3.5 multimodal RoPE requires processor output `mm_token_type_ids`.")

    if input_ids.dim() > 1:
        input_ids = input_ids[0]
    if mm_token_type_ids.dim() > 1:
        mm_token_type_ids = mm_token_type_ids[0]

    spatial_merge_size = int(processor.image_processor.merge_size)
    device = input_ids.device

    if video_grid_thw is not None:
        video_grid_thw = torch.repeat_interleave(video_grid_thw, video_grid_thw[:, 0], dim=0)
        video_grid_thw[:, 0] = 1

    if attention_mask is None:
        attention_mask = torch.ones_like(input_ids)
    elif attention_mask.dim() > 1:
        attention_mask = attention_mask[0]

    position_ids = torch.zeros(3, input_ids.shape[0], dtype=input_ids.dtype, device=device)
    input_token_type = mm_token_type_ids[attention_mask == 1]
    grid_iters = {
        1: iter(image_grid_thw) if image_grid_thw is not None else None,
        2: iter(video_grid_thw) if video_grid_thw is not None else None,
    }

    current_pos = 0
    llm_pos_ids_list: list[torch.Tensor] = []
    for modality_type, group in itertools.groupby(enumerate(input_token_type.tolist()), lambda item: item[1]):
        grouped_items = list(group)
        start_idx = grouped_items[0][0]
        end_idx = grouped_items[-1][0] + 1
        if modality_type == 0:
            text_len = end_idx - start_idx
            llm_pos_ids_list.append(torch.arange(text_len, device=device).view(1, -1).expand(3, -1) + current_pos)
            current_pos += text_len
            continue

        if modality_type not in grid_iters or grid_iters[modality_type] is None:
            raise ValueError(f"Qwen3.5 multimodal RoPE missing grid metadata for modality type {modality_type}.")
        grid_thw = next(grid_iters[modality_type])
        llm_pos_ids_list.append(
            _get_vision_position_ids(
                start_position=current_pos,
                grid_thw=grid_thw,
                spatial_merge_size=spatial_merge_size,
                device=device,
            )
        )
        current_pos += max(int(grid_thw[1].item()), int(grid_thw[2].item())) // spatial_merge_size

    llm_positions = torch.cat(llm_pos_ids_list, dim=1).reshape(3, -1)
    position_ids[..., attention_mask == 1] = llm_positions.to(device)
    return position_ids


__all__ = ["get_rope_index"]

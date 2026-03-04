"""Shared visual-variation helpers (background/noise/post-processing)."""

from .background import make_background_canvas
from .noise import TRACE_DEFAULT_NOISE_VALUE_RANGES, apply_post_image_noise

__all__ = ["apply_post_image_noise", "TRACE_DEFAULT_NOISE_VALUE_RANGES", "make_background_canvas"]

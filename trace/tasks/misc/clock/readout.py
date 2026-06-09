"""Analog-clock misc task with direct time readout and minute offsets."""

from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
  PROMPT_OUTPUT_MODES,
  build_prompt_trace_artifacts,
  render_task_prompt_variants,
)
from ...shared.text_rendering import temporary_default_font_family
from ..shared.clock_scene import (
  ClockRenderParams,
  SUPPORTED_MISC_CLOCK_SCENE_VARIANTS,
  render_clock_scene,
  resolve_clock_render_params,
)
from ..shared.scene_style import make_misc_scene_background, resolve_misc_scene_style
from ...shared.time_artifact_complexity import (
  build_time_artifact_complexity,
  normalize_float_with_bounds,
  normalize_int_with_bounds,
  resolve_time_artifact_complexity_weights,
)
from ...shared.time_artifact_fixed_query import force_time_artifact_query_params, rewrite_time_artifact_query_output
from ...shared.time_artifact_task_support import resolve_time_artifact_named_variant
from ...shared.time_artifact_style import (
  SUPPORTED_TIME_ARTIFACT_CLOCK_COLOR_NAMES,
  SUPPORTED_TIME_ARTIFACT_CLOCK_STYLE_VARIANTS,
  build_time_artifact_clock_theme,
)
from ...shared.time_format import (
  add_clock_seconds,
  add_clock_minutes,
  clock_hand_angle_gap_deg,
  clock_hand_pair_angle_gaps_deg,
  clock_total_minutes,
  clock_total_seconds,
  format_clock_hhmm,
  format_clock_hhmmss,
  split_clock_total_minutes,
  split_clock_total_seconds,
)
from ..shared.visual_defaults import load_misc_background_defaults, load_misc_noise_defaults


TASK_ID = "misc_clock_readout_base"
CLOCK_OFFSET_TASK_ID = "task_misc__analog_clock__offset_readout"
PUBLIC_SCENE_ID = "analog_clock"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
  "offset_time",
)
_SOURCE_OFFSET_BY_VARIANT = {
  "minutes_after": ("minutes", "after"),
  "minutes_before": ("minutes", "before"),
  "seconds_after": ("seconds", "after"),
  "seconds_before": ("seconds", "before"),
}
_SUPPORTED_OFFSET_UNITS: Tuple[str, ...] = ("minutes", "seconds")
_SUPPORTED_OFFSET_DIRECTIONS: Tuple[str, ...] = ("after", "before")

_TIME_READING_BASE_BY_OFFSET = {
  ("minutes", "before"): 0.00,
  ("minutes", "after"): 0.05,
  ("seconds", "after"): 0.35,
  ("seconds", "before"): 1.00,
}
_VISUAL_SCAN_BASE_BY_SCENE = {
  "classic": 0.34,
  "minimal": 0.22,
  "outline": 0.26,
}
_VISUAL_SCAN_STYLE_BONUS = {
  "studio": 0.00,
  "accented": 0.04,
  "marker": 0.06,
}
_CLUTTER_BASE_BY_SCENE = {
  "classic": 0.32,
  "minimal": 0.12,
  "outline": 0.18,
}
_CLUTTER_STYLE_BONUS = {
  "studio": 0.00,
  "accented": 0.05,
  "marker": 0.08,
}


@dataclass(frozen=True)
class _TaskDefaults:
  """Stable fallback defaults for misc clock-readout scenes."""

  hour_min: int = 1
  hour_max: int = 12
  minute_min: int = 0
  minute_max: int = 55
  minute_step: int = 5
  second_min: int = 0
  second_max: int = 55
  second_step: int = 5
  min_hand_angle_gap_deg: float = 10.0
  canvas_width: int = 640
  canvas_height: int = 640
  outer_margin_px: int = 36
  face_radius_px: int = 236
  bezel_width_px: int = 10
  numeral_font_size_px: int = 28
  major_tick_length_px: int = 18
  minor_tick_length_px: int = 8
  major_tick_width_px: int = 4
  minor_tick_width_px: int = 2
  minor_tick_dot_radius_px: int = 3
  hour_hand_width_px: int = 12
  minute_hand_width_px: int = 8
  second_hand_width_px: int = 3
  hand_bbox_padding_px: int = 6
  center_dot_radius_px: int = 8
  inner_ring_inset_px: int = 18
  inner_ring_width_px: int = 4


@dataclass(frozen=True)
class _ResolvedQuery:
  """Resolved semantic and visual support for one clock-readout instance."""

  query_id: str
  offset_unit: str
  offset_direction: str
  scene_variant: str
  style_variant: str
  accent_color_name: str
  shown_total_minutes: int
  shown_total_seconds: int
  shown_hour: int
  shown_minute: int
  shown_second: int
  delta_minutes: int | None
  delta_seconds: int | None
  answer_time_text: str
  hour_support: Tuple[int, int]
  minute_support: Tuple[int, int, int]
  second_support: Tuple[int, int, int]
  delta_minutes_support: Tuple[int, ...]
  delta_seconds_support: Tuple[int, ...]
  min_hand_angle_gap_deg: float
  query_id_probabilities: Dict[str, float]
  offset_unit_probabilities: Dict[str, float]
  offset_direction_probabilities: Dict[str, float]
  scene_variant_probabilities: Dict[str, float]
  style_variant_probabilities: Dict[str, float]
  accent_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("misc", "clock")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
  _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
  task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_time_artifact_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_misc_background_defaults(task_group="clock")
POST_IMAGE_NOISE_DEFAULTS = load_misc_noise_defaults(task_group="clock", apply_prob=0.0)


def _canonical_hand_example_points() -> dict[str, list[int]]:
  """Return one stable two-hand point-map example for prompt examples."""

  return {
    "clock_center": [320, 320],
    "hour_hand_tip": [430, 350],
    "minute_hand_tip": [484, 461],
  }


def _canonical_second_hand_example_points() -> dict[str, list[int]]:
  """Return one stable three-hand point-map example for prompt examples."""

  points = dict(_canonical_hand_example_points())
  points["second_hand_tip"] = [140, 424]
  return points


def _is_seconds_offset(offset_unit: str) -> bool:
  """Return whether the offset query uses seconds and needs a seconds hand."""

  return str(offset_unit) == "seconds"


def _resolve_offset_support(raw_support: Any, *, name: str) -> Tuple[int, int, int]:
  """Resolve an offset support specification as compact `(min, max, step)`."""

  if isinstance(raw_support, Mapping):
    support_min = int(raw_support.get("min", raw_support.get("start", 0)))
    support_max = int(raw_support.get("max", raw_support.get("stop", support_min)))
    support_step = int(raw_support.get("step", 1))
  else:
    values = [int(value) for value in raw_support] if isinstance(raw_support, Sequence) and not isinstance(raw_support, (str, bytes)) else []
    if not values:
      raise ValueError(f"{name} is empty for misc clock tasks")
    support_min = int(values[0])
    support_max = int(values[-1])
    support_step = int(values[1] - values[0]) if len(values) > 1 else 1
    expected_values = list(range(int(support_min), int(support_max) + 1, int(support_step)))
    if values != expected_values:
      raise ValueError(f"{name} must be an arithmetic range for misc clock tasks")
  if support_step <= 0:
    raise ValueError(f"{name} step must be positive for misc clock tasks")
  if support_min <= 0 or support_max < support_min:
    raise ValueError(f"{name} must have positive min <= max for misc clock tasks")
  if (support_max - support_min) % support_step != 0:
    raise ValueError(f"{name} max must align to min + n*step for misc clock tasks")
  return int(support_min), int(support_max), int(support_step)


def _offset_support_count(support: Tuple[int, int, int]) -> int:
  """Return the number of values in a compact offset support."""

  return int(((int(support[1]) - int(support[0])) // int(support[2])) + 1)


def _offset_value_at(support: Tuple[int, int, int], index: int) -> int:
  """Return a deterministic value from one compact offset support."""

  return int(support[0]) + (int(index) % _offset_support_count(support)) * int(support[2])


def _offset_support_contains(support: Tuple[int, int, int], value: int) -> bool:
  """Return whether one value is in a compact offset support."""

  candidate = int(value)
  return int(support[0]) <= candidate <= int(support[1]) and ((candidate - int(support[0])) % int(support[2])) == 0


def _resolve_decoupled_selection_index(
  *,
  params: Mapping[str, Any],
  instance_seed: int,
  namespace: str,
  multiplier: int,
  offset: int,
) -> int:
  """Return a namespaced selection index for one balanced axis."""

  _ = int(multiplier), int(offset)
  return resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))


def _build_prompt_json_examples(
  *,
  query_id: str,
  offset_unit: str,
  offset_direction: str,
  delta_minutes: int | None,
  delta_seconds: int | None,
) -> tuple[str, str]:
  """Return prompt JSON examples that match the active offset semantics."""

  shown_total_minutes = clock_total_minutes(3, 25)
  shown_total_seconds = clock_total_seconds(3, 25, 40)
  if str(query_id) != "offset_time":
    raise ValueError(f"unsupported misc clock-readout variant: {query_id}")
  if str(offset_unit) == "minutes" and str(offset_direction) == "after":
    answer_text = str(format_clock_hhmm(add_clock_minutes(int(shown_total_minutes), int(delta_minutes))))
  elif str(offset_unit) == "minutes" and str(offset_direction) == "before":
    answer_text = str(format_clock_hhmm(add_clock_minutes(int(shown_total_minutes), -int(delta_minutes))))
  elif str(offset_unit) == "seconds" and str(offset_direction) == "after":
    answer_text = str(format_clock_hhmmss(add_clock_seconds(int(shown_total_seconds), int(delta_seconds))))
  elif str(offset_unit) == "seconds" and str(offset_direction) == "before":
    answer_text = str(format_clock_hhmmss(add_clock_seconds(int(shown_total_seconds), -int(delta_seconds))))
  else:
    raise ValueError(f"unsupported misc clock-readout offset: {offset_unit} {offset_direction}")
  example_points = _canonical_second_hand_example_points() if _is_seconds_offset(str(offset_unit)) else _canonical_hand_example_points()
  answer_and_annotation = {
    "annotation": example_points,
    "answer": str(answer_text),
  }
  answer_only = {"answer": str(answer_text)}
  return (
    json.dumps(answer_and_annotation, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
  )


def _resolve_named_variant(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
  explicit_key: str,
  weights_key: str,
  balance_flag_key: str,
  supported: Tuple[str, ...],
  namespace: str,
) -> Tuple[str, Dict[str, float]]:
  """Resolve one balanced named misc-clock axis."""

  rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
  return resolve_time_artifact_named_variant(
    rng,
    params=params,
    gen_defaults=_GEN_DEFAULTS,
    explicit_key=str(explicit_key),
    weights_key=str(weights_key),
    balance_flag_key=str(balance_flag_key),
    supported=supported,
    instance_seed=int(instance_seed),
    task_id=TASK_ID,
    namespace=str(namespace),
  )


def _resolve_query_id(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
  """Resolve the public clock-readout variant and supported offset aliases."""

  explicit_variant = params.get("query_id")
  if explicit_variant is not None and str(explicit_variant) in _SOURCE_OFFSET_BY_VARIANT:
    return "offset_time", {"offset_time": 1.0}
  return _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="query_id",
    weights_key="query_id_weights",
    balance_flag_key="balanced_query_id_sampling",
    supported=SUPPORTED_QUERY_IDS,
    namespace="query_id",
  )


def _normalize_offset_unit(value: Any) -> str:
  """Normalize one offset unit label."""

  normalized = str(value).strip().lower()
  if normalized in {"minute", "minutes"}:
    return "minutes"
  if normalized in {"second", "seconds"}:
    return "seconds"
  raise ValueError(f"unsupported offset_unit: {value}")


def _normalize_offset_direction(value: Any) -> str:
  """Normalize one offset direction label."""

  normalized = str(value).strip().lower()
  if normalized in _SUPPORTED_OFFSET_DIRECTIONS:
    return normalized
  raise ValueError(f"unsupported offset_direction: {value}")


def _source_offset_from_params(params: Mapping[str, Any]) -> Tuple[str, str] | None:
  """Return an implied `(unit, direction)` pair from source query aliases."""

  source_variant = params.get("query_id")
  if source_variant is not None and str(source_variant) in _SOURCE_OFFSET_BY_VARIANT:
    unit, direction = _SOURCE_OFFSET_BY_VARIANT[str(source_variant)]
    return str(unit), str(direction)
  return None


def _axis_params_for_decoupled_sampling(
  *,
  params: Mapping[str, Any],
  divisor: int,
  explicit_key: str,
) -> Mapping[str, Any]:
  """Return params unchanged for axis-decoupling call sites."""

  _ = int(divisor), str(explicit_key)
  return params


def _resolve_offset_unit(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
  """Resolve whether the offset is expressed in minutes or seconds."""

  source_offset = _source_offset_from_params(params)
  if source_offset is not None:
    selected = str(source_offset[0])
    return selected, {
      key: (1.0 if key == selected else 0.0)
      for key in _SUPPORTED_OFFSET_UNITS
    }

  explicit = params.get("offset_unit", params.get("unit"))
  if explicit is not None:
    selected = _normalize_offset_unit(explicit)
    return selected, {
      key: (1.0 if key == selected else 0.0)
      for key in _SUPPORTED_OFFSET_UNITS
    }

  return _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="offset_unit",
    weights_key="offset_unit_weights",
    balance_flag_key="balanced_offset_unit_sampling",
    supported=_SUPPORTED_OFFSET_UNITS,
    namespace="offset_unit",
  )


def _resolve_offset_direction(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
  """Resolve whether the offset is before or after the shown time."""

  source_offset = _source_offset_from_params(params)
  if source_offset is not None:
    selected = str(source_offset[1])
    return selected, {
      key: (1.0 if key == selected else 0.0)
      for key in _SUPPORTED_OFFSET_DIRECTIONS
    }

  explicit = params.get("offset_direction", params.get("direction"))
  if explicit is not None:
    selected = _normalize_offset_direction(explicit)
    return selected, {
      key: (1.0 if key == selected else 0.0)
      for key in _SUPPORTED_OFFSET_DIRECTIONS
    }

  return _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=_axis_params_for_decoupled_sampling(
      params=params,
      divisor=len(_SUPPORTED_OFFSET_UNITS),
      explicit_key="offset_direction",
    ),
    explicit_key="offset_direction",
    weights_key="offset_direction_weights",
    balance_flag_key="balanced_offset_direction_sampling",
    supported=_SUPPORTED_OFFSET_DIRECTIONS,
    namespace="offset_direction",
  )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
  """Resolve one concrete clock-readout query from balanced supports."""

  query_id, query_id_probabilities = _resolve_query_id(
    instance_seed=int(instance_seed),
    params=params,
  )
  offset_unit, offset_unit_probabilities = _resolve_offset_unit(
    instance_seed=int(instance_seed),
    params=params,
  )
  offset_direction, offset_direction_probabilities = _resolve_offset_direction(
    instance_seed=int(instance_seed),
    params=params,
  )
  scene_variant, scene_variant_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="scene_variant",
    weights_key="scene_variant_weights",
    balance_flag_key="balanced_scene_variant_sampling",
    supported=SUPPORTED_MISC_CLOCK_SCENE_VARIANTS,
    namespace="scene_variant",
  )
  style_variant, style_variant_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="style_variant",
    weights_key="style_variant_weights",
    balance_flag_key="balanced_style_variant_sampling",
    supported=SUPPORTED_TIME_ARTIFACT_CLOCK_STYLE_VARIANTS,
    namespace="style_variant",
  )
  accent_color_name, accent_color_name_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="accent_color_name",
    weights_key="accent_color_name_weights",
    balance_flag_key="balanced_accent_color_name_sampling",
    supported=SUPPORTED_TIME_ARTIFACT_CLOCK_COLOR_NAMES,
    namespace="accent_color_name",
  )

  hour_min = int(params.get("hour_min", group_default(_GEN_DEFAULTS, "hour_min", _DEFAULTS.hour_min)))
  hour_max = int(params.get("hour_max", group_default(_GEN_DEFAULTS, "hour_max", _DEFAULTS.hour_max)))
  minute_min = int(params.get("minute_min", group_default(_GEN_DEFAULTS, "minute_min", _DEFAULTS.minute_min)))
  minute_max = int(params.get("minute_max", group_default(_GEN_DEFAULTS, "minute_max", _DEFAULTS.minute_max)))
  minute_step = int(params.get("minute_step", group_default(_GEN_DEFAULTS, "minute_step", _DEFAULTS.minute_step)))
  second_min = int(params.get("second_min", group_default(_GEN_DEFAULTS, "second_min", _DEFAULTS.second_min)))
  second_max = int(params.get("second_max", group_default(_GEN_DEFAULTS, "second_max", _DEFAULTS.second_max)))
  second_step = int(params.get("second_step", group_default(_GEN_DEFAULTS, "second_step", _DEFAULTS.second_step)))
  min_hand_angle_gap_deg = float(
    params.get(
      "min_hand_angle_gap_deg",
      group_default(_GEN_DEFAULTS, "min_hand_angle_gap_deg", _DEFAULTS.min_hand_angle_gap_deg),
    )
  )
  if minute_step <= 0:
    raise ValueError("minute_step must be positive for misc clock tasks")
  if second_step <= 0:
    raise ValueError("second_step must be positive for misc clock tasks")
  if float(min_hand_angle_gap_deg) < 0.0:
    raise ValueError("min_hand_angle_gap_deg must be non-negative for misc clock tasks")

  minute_support = tuple(range(int(minute_min), int(minute_max) + 1, int(minute_step)))
  if not minute_support:
    raise ValueError("minute support is empty for misc clock tasks")
  if minute_support[0] < 0 or minute_support[-1] > 59:
    raise ValueError("minute support must stay within 0..59 for misc clock tasks")
  second_support = tuple(range(int(second_min), int(second_max) + 1, int(second_step)))
  if not second_support:
    raise ValueError("second support is empty for misc clock tasks")
  if second_support[0] < 0 or second_support[-1] > 59:
    raise ValueError("second support must stay within 0..59 for misc clock tasks")
  hour_support = tuple(range(int(hour_min), int(hour_max) + 1))
  if not hour_support:
    raise ValueError("hour support is empty for misc clock tasks")
  if hour_support[0] < 1 or hour_support[-1] > 12:
    raise ValueError("hour support must stay within 1..12 for misc clock tasks")

  shown_total_minute_support = tuple(
    clock_total_minutes(int(hour), int(minute))
    for hour in hour_support
    for minute in minute_support
    if float(clock_hand_angle_gap_deg(clock_total_minutes(int(hour), int(minute)))) >= float(min_hand_angle_gap_deg)
  )
  if not shown_total_minute_support:
    raise ValueError("shown time support is empty after clock-hand angle-gap filtering")
  shown_total_second_support = tuple(
    clock_total_seconds(int(hour), int(minute), int(second))
    for hour in hour_support
    for minute in minute_support
    for second in second_support
    if min(clock_hand_pair_angle_gaps_deg(clock_total_seconds(int(hour), int(minute), int(second)))) >= float(min_hand_angle_gap_deg)
  )
  if _is_seconds_offset(str(offset_unit)) and not shown_total_second_support:
    raise ValueError("shown time support is empty after seconds-hand angle-gap filtering")
  shown_index = resolve_selection_index(
    params=params,
    instance_seed=int(instance_seed),
    namespace=f"{TASK_ID}:shown_total",
  )

  explicit_hour = params.get("shown_hour")
  explicit_minute = params.get("shown_minute")
  explicit_second = params.get("shown_second")
  explicit_total = params.get("shown_total_minutes")
  explicit_total_seconds = params.get("shown_total_seconds")
  if _is_seconds_offset(str(offset_unit)):
    if explicit_total_seconds is not None:
      shown_total_seconds = int(explicit_total_seconds)
    elif explicit_hour is not None or explicit_minute is not None or explicit_second is not None:
      if explicit_hour is None or explicit_minute is None or explicit_second is None:
        raise ValueError("shown_hour, shown_minute, and shown_second must be provided together for seconds variants")
      shown_total_seconds = clock_total_seconds(int(explicit_hour), int(explicit_minute), int(explicit_second))
    else:
      shown_total_seconds = int(shown_total_second_support[int(shown_index % len(shown_total_second_support))])
    if int(shown_total_seconds) not in shown_total_second_support:
      raise ValueError("shown seconds time is outside configured support for misc clock tasks")
    shown_total_minutes = int(shown_total_seconds // 60)
  elif explicit_total is not None:
    shown_total_minutes = int(explicit_total)
    shown_total_seconds = int(shown_total_minutes * 60)
  elif explicit_hour is not None or explicit_minute is not None:
    if explicit_hour is None or explicit_minute is None:
      raise ValueError("shown_hour and shown_minute must be provided together")
    shown_total_minutes = clock_total_minutes(int(explicit_hour), int(explicit_minute))
    shown_total_seconds = int(shown_total_minutes * 60)
  else:
    shown_total_minutes = int(shown_total_minute_support[int(shown_index % len(shown_total_minute_support))])
    shown_total_seconds = int(shown_total_minutes * 60)
  if not _is_seconds_offset(str(offset_unit)) and int(shown_total_minutes) not in shown_total_minute_support:
    raise ValueError("shown time is outside configured support for misc clock tasks")

  delta_support_raw = params.get("delta_minutes_support", group_default(_GEN_DEFAULTS, "delta_minutes_support", ()))
  delta_support = _resolve_offset_support(delta_support_raw, name="delta_minutes_support")
  delta_seconds_support_raw = params.get("delta_seconds_support", group_default(_GEN_DEFAULTS, "delta_seconds_support", ()))
  delta_seconds_support = _resolve_offset_support(delta_seconds_support_raw, name="delta_seconds_support")
  delta_minutes: int | None = None
  delta_seconds: int | None = None
  if str(offset_unit) == "minutes":
    explicit_delta = params.get("delta_minutes")
    if explicit_delta is not None:
      delta_minutes = int(explicit_delta)
      if not _offset_support_contains(delta_support, int(delta_minutes)):
        raise ValueError("delta_minutes is outside configured support for misc clock tasks")
    else:
      delta_index = _resolve_decoupled_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:delta_minutes",
        multiplier=37,
        offset=17,
      )
      delta_minutes = _offset_value_at(delta_support, int(delta_index))
  if str(offset_unit) == "seconds":
    explicit_delta_seconds = params.get("delta_seconds")
    if explicit_delta_seconds is not None:
      delta_seconds = int(explicit_delta_seconds)
      if not _offset_support_contains(delta_seconds_support, int(delta_seconds)):
        raise ValueError("delta_seconds is outside configured support for misc clock tasks")
    else:
      delta_seconds_index = _resolve_decoupled_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:delta_seconds",
        multiplier=101,
        offset=29,
      )
      delta_seconds = _offset_value_at(delta_seconds_support, int(delta_seconds_index))

  answer_total_minutes = int(shown_total_minutes)
  answer_total_seconds = int(shown_total_seconds)
  if str(offset_unit) == "minutes" and str(offset_direction) == "after":
    answer_total_minutes = add_clock_minutes(int(shown_total_minutes), int(delta_minutes))
    answer_text = str(format_clock_hhmm(int(answer_total_minutes)))
  elif str(offset_unit) == "minutes" and str(offset_direction) == "before":
    answer_total_minutes = add_clock_minutes(int(shown_total_minutes), -int(delta_minutes))
    answer_text = str(format_clock_hhmm(int(answer_total_minutes)))
  elif str(offset_unit) == "seconds" and str(offset_direction) == "after":
    answer_total_seconds = add_clock_seconds(int(shown_total_seconds), int(delta_seconds))
    answer_text = str(format_clock_hhmmss(int(answer_total_seconds)))
  elif str(offset_unit) == "seconds" and str(offset_direction) == "before":
    answer_total_seconds = add_clock_seconds(int(shown_total_seconds), -int(delta_seconds))
    answer_text = str(format_clock_hhmmss(int(answer_total_seconds)))
  else:
    raise ValueError(f"unsupported misc clock-readout offset: {offset_unit} {offset_direction}")

  shown_hour, shown_minute, shown_second = split_clock_total_seconds(int(shown_total_seconds))
  return _ResolvedQuery(
    query_id=str(query_id),
    offset_unit=str(offset_unit),
    offset_direction=str(offset_direction),
    scene_variant=str(scene_variant),
    style_variant=str(style_variant),
    accent_color_name=str(accent_color_name),
    shown_total_minutes=int(shown_total_minutes),
    shown_total_seconds=int(shown_total_seconds),
    shown_hour=int(shown_hour),
    shown_minute=int(shown_minute),
    shown_second=int(shown_second),
    delta_minutes=(int(delta_minutes) if delta_minutes is not None else None),
    delta_seconds=(int(delta_seconds) if delta_seconds is not None else None),
    answer_time_text=str(answer_text),
    hour_support=(int(hour_support[0]), int(hour_support[-1])),
    minute_support=(int(minute_support[0]), int(minute_support[-1]), int(minute_step)),
    second_support=(int(second_support[0]), int(second_support[-1]), int(second_step)),
    delta_minutes_support=tuple(int(value) for value in delta_support),
    delta_seconds_support=tuple(int(value) for value in delta_seconds_support),
    min_hand_angle_gap_deg=float(min_hand_angle_gap_deg),
    query_id_probabilities=dict(query_id_probabilities),
    offset_unit_probabilities=dict(offset_unit_probabilities),
    offset_direction_probabilities=dict(offset_direction_probabilities),
    scene_variant_probabilities=dict(scene_variant_probabilities),
    style_variant_probabilities=dict(style_variant_probabilities),
    accent_color_name_probabilities=dict(accent_color_name_probabilities),
  )


class _MiscClockReadoutBase:
  """Return one minute- or second-offset time from a single analog clock."""

  task_id = TASK_ID
  domain = "misc"
  task_group = "clock"

  def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
    del max_attempts
    query = _resolve_query(int(instance_seed), params=params)
    render_params = resolve_clock_render_params(
      params,
      render_defaults=_RENDER_DEFAULTS,
      fallback_values=asdict(_DEFAULTS),
      instance_seed=int(instance_seed),
    )
    # Preserve the legacy puzzle seed namespace so the domain split does not
    # change sampled fonts for existing analog-clock seeds.
    font_family = sample_font_family(
      role="readout",
      instance_seed=int(instance_seed),
      namespace="puzzles.clock.readout.font",
      params={**dict(_RENDER_DEFAULTS), **dict(params)},
    )
    clock_theme = build_time_artifact_clock_theme(
      accent_color_name=str(query.accent_color_name),
      style_variant=str(query.style_variant),
    )

    scene_style, scene_style_meta = resolve_misc_scene_style(
      instance_seed=int(instance_seed),
      namespace=f"{self.task_id}.clock_background",
    )
    background, background_meta = make_misc_scene_background(
      canvas_width=int(render_params.canvas_width),
      canvas_height=int(render_params.canvas_height),
      style=scene_style,
    )
    with temporary_default_font_family(str(font_family)):
      rendered_scene = render_clock_scene(
        background,
        scene_variant=str(query.scene_variant),
        shown_total_minutes=int(query.shown_total_minutes),
        shown_total_seconds=int(query.shown_total_seconds),
        show_second_hand=_is_seconds_offset(str(query.offset_unit)),
        render_params=render_params,
        visual_theme=clock_theme,
      )
    image, post_noise_meta = apply_post_image_noise(
      rendered_scene.image,
      instance_seed=int(instance_seed),
      params=params,
      default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    prompt_defaults = required_group_defaults(
      _PROMPT_DEFAULTS,
      (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        "object_description_classic",
        "object_description_minimal",
        "object_description_outline",
        "object_description_classic_seconds",
        "object_description_minimal_seconds",
        "object_description_outline_seconds",
        "annotation_hint",
        "annotation_hint_seconds",
        "answer_hint",
        "answer_hint_seconds",
      ),
      context=f"prompt defaults for {self.task_id}",
    )
    is_seconds_offset = _is_seconds_offset(str(query.offset_unit))
    seconds_suffix = "_seconds" if is_seconds_offset else ""
    object_description = str(prompt_defaults[f"object_description_{str(query.scene_variant)}{seconds_suffix}"])
    annotation_hint = str(prompt_defaults["annotation_hint_seconds" if is_seconds_offset else "annotation_hint"])
    answer_hint = str(prompt_defaults["answer_hint_seconds" if is_seconds_offset else "answer_hint"])
    json_example, json_example_answer_only = _build_prompt_json_examples(
      query_id=str(query.query_id),
      offset_unit=str(query.offset_unit),
      offset_direction=str(query.offset_direction),
      delta_minutes=(int(query.delta_minutes) if query.delta_minutes is not None else None),
      delta_seconds=(int(query.delta_seconds) if query.delta_seconds is not None else None),
    )
    prompt_selection = render_task_prompt_variants(
      domain=self.domain,
      task_group=self.task_group,
      bundle_id=str(prompt_defaults["bundle_id"]),
      scene_key=str(prompt_defaults["scene_key"]),
      task_key=str(prompt_defaults["task_key"]),
      query_key=str(query.query_id),
      answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
      slots={
        "object_description": str(object_description),
        "delta_minutes": (str(query.delta_minutes) if query.delta_minutes is not None else ""),
        "delta_seconds": (str(query.delta_seconds) if query.delta_seconds is not None else ""),
        "delta_value": (str(query.delta_seconds) if is_seconds_offset else str(query.delta_minutes)),
        "offset_unit": str(query.offset_unit),
        "offset_direction": str(query.offset_direction),
        "answer_format": "HH:MM:SS" if is_seconds_offset else "HH:MM",
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "annotation_hint": str(annotation_hint),
        "answer_hint": str(answer_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
      },
      instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    annotation_points = {
      "clock_center": [round(float(value), 3) for value in rendered_scene.center_px],
      "hour_hand_tip": [round(float(value), 3) for value in rendered_scene.hour_hand_tip_px],
      "minute_hand_tip": [round(float(value), 3) for value in rendered_scene.minute_hand_tip_px],
    }
    if is_seconds_offset:
      if rendered_scene.second_hand_tip_px is None:
        raise ValueError("seconds variants require second-hand geometry")
      annotation_points["second_hand_tip"] = [round(float(value), 3) for value in rendered_scene.second_hand_tip_px]
    answer_gt = TypedValue(type="string", value=str(query.answer_time_text))
    annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_points))
    shown_time_text = (
      str(format_clock_hhmmss(int(query.shown_total_seconds)))
      if is_seconds_offset
      else str(format_clock_hhmm(int(query.shown_total_minutes)))
    )
    hand_bboxes_px = {
      "hour": [round(float(value), 3) for value in rendered_scene.hour_hand_bbox_px],
      "minute": [round(float(value), 3) for value in rendered_scene.minute_hand_bbox_px],
    }
    hand_tips_px = {
      "hour": [round(float(value), 3) for value in rendered_scene.hour_hand_tip_px],
      "minute": [round(float(value), 3) for value in rendered_scene.minute_hand_tip_px],
    }
    pixel_point_map = dict(annotation_points)
    supporting_parts = ["hour_hand", "minute_hand"]
    if is_seconds_offset:
      if rendered_scene.second_hand_bbox_px is None or rendered_scene.second_hand_tip_px is None:
        raise ValueError("seconds variants require second-hand geometry")
      hand_bboxes_px["second"] = [round(float(value), 3) for value in rendered_scene.second_hand_bbox_px]
      hand_tips_px["second"] = [round(float(value), 3) for value in rendered_scene.second_hand_tip_px]
      pixel_point_map["second_hand_tip"] = [round(float(value), 3) for value in rendered_scene.second_hand_tip_px]
      supporting_parts.append("second_hand")

    trace_payload = {
      "scene_ir": {
        "scene_kind": "misc_clock_single",
        "entities": [dict(entity) for entity in rendered_scene.entities],
        "relations": {
          "query_id": str(query.query_id),
          "offset_unit": str(query.offset_unit),
          "offset_direction": str(query.offset_direction),
          "scene_variant": str(query.scene_variant),
          "shown_total_minutes": int(query.shown_total_minutes),
          "shown_total_seconds": int(query.shown_total_seconds),
          "shown_time_text": str(shown_time_text),
          "delta_minutes": (int(query.delta_minutes) if query.delta_minutes is not None else None),
          "delta_seconds": (int(query.delta_seconds) if query.delta_seconds is not None else None),
          "answer_time_text": str(query.answer_time_text),
        },
      },
      "query_spec": {
        "query_id": str(query.query_id),
        "template_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
        "params": {
          "query_id": str(query.query_id),
          "offset_unit": str(query.offset_unit),
          "offset_direction": str(query.offset_direction),
          "scene_variant": str(query.scene_variant),
          "style_variant": str(query.style_variant),
          "accent_color_name": str(query.accent_color_name),
          "query_id_probabilities": dict(query.query_id_probabilities),
          "offset_unit_probabilities": dict(query.offset_unit_probabilities),
          "offset_direction_probabilities": dict(query.offset_direction_probabilities),
          "scene_variant_probabilities": dict(query.scene_variant_probabilities),
          "style_variant_probabilities": dict(query.style_variant_probabilities),
          "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
          "hour_support": [int(query.hour_support[0]), int(query.hour_support[1])],
          "minute_support": [int(value) for value in query.minute_support],
          "second_support": [int(value) for value in query.second_support],
          "delta_minutes_support": [int(value) for value in query.delta_minutes_support],
          "delta_seconds_support": [int(value) for value in query.delta_seconds_support],
          "min_hand_angle_gap_deg": float(query.min_hand_angle_gap_deg),
        },
      },
      "render_spec": {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": str(query.scene_variant),
        "background_style": dict(background_meta),
        "scene_style": dict(scene_style_meta),
        "post_image_noise": dict(post_noise_meta),
        "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
        "clock_style": {
          "accent_color_name": str(query.accent_color_name),
          "style_variant": str(query.style_variant),
          "face_radius_px": int(render_params.face_radius_px),
          "bezel_width_px": int(render_params.bezel_width_px),
          "numeral_font_size_px": int(render_params.numeral_font_size_px),
          "hour_hand_width_px": int(render_params.hour_hand_width_px),
          "minute_hand_width_px": int(render_params.minute_hand_width_px),
          "second_hand_width_px": int(render_params.second_hand_width_px),
          "minor_tick_dot_radius_px": int(render_params.minor_tick_dot_radius_px),
          "inner_ring_inset_px": int(render_params.inner_ring_inset_px),
          "inner_ring_width_px": int(render_params.inner_ring_width_px),
          "font": {
            "source": "global_font_pool",
            "font_family": str(font_family),
            "font_asset_version": font_asset_version(),
            "scope": "single_clock_face",
          },
          "resolved_colors_rgb": {
            "face_fill": [int(value) for value in clock_theme.face_fill_rgb],
            "face_outline": [int(value) for value in clock_theme.face_outline_rgb],
            "numerals": [int(value) for value in clock_theme.numeral_color_rgb],
            "ticks": [int(value) for value in clock_theme.tick_color_rgb],
            "hour_hand": [int(value) for value in clock_theme.hour_hand_color_rgb],
            "minute_hand": [int(value) for value in clock_theme.minute_hand_color_rgb],
            "second_hand": [int(value) for value in clock_theme.second_hand_color_rgb],
            "center_dot": [int(value) for value in clock_theme.center_dot_color_rgb],
            "inner_ring": (
              [int(value) for value in clock_theme.inner_ring_rgb]
              if clock_theme.inner_ring_rgb is not None
              else None
            ),
          },
          "minor_tick_mode": str(clock_theme.minor_tick_mode),
        },
      },
      "render_map": {
        "image_id": "img0",
        "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
        "face_bbox_px": [round(float(value), 3) for value in rendered_scene.face_bbox_px],
        "center_px": [round(float(value), 3) for value in rendered_scene.center_px],
        "hand_bboxes_px": dict(hand_bboxes_px),
        "hand_tips_px": dict(hand_tips_px),
        "annotation_source": "center_px_and_hand_tips_px",
      },
      "execution_trace": {
        "query_id": str(query.query_id),
        "offset_unit": str(query.offset_unit),
        "offset_direction": str(query.offset_direction),
        "scene_variant": str(query.scene_variant),
        "style_variant": str(query.style_variant),
        "accent_color_name": str(query.accent_color_name),
        "shown_total_minutes": int(query.shown_total_minutes),
        "shown_total_seconds": int(query.shown_total_seconds),
        "shown_hour": int(query.shown_hour),
        "shown_minute": int(query.shown_minute),
        "shown_second": int(query.shown_second),
        "shown_time_text": str(shown_time_text),
        "delta_minutes": (int(query.delta_minutes) if query.delta_minutes is not None else None),
        "delta_seconds": (int(query.delta_seconds) if query.delta_seconds is not None else None),
        "answer_time_text": str(query.answer_time_text),
        "hour_support": [int(query.hour_support[0]), int(query.hour_support[1])],
        "minute_support": [int(value) for value in query.minute_support],
        "second_support": [int(value) for value in query.second_support],
        "delta_minutes_support": [int(value) for value in query.delta_minutes_support],
        "delta_seconds_support": [int(value) for value in query.delta_seconds_support],
        "min_hand_angle_gap_deg": float(query.min_hand_angle_gap_deg),
        "query_id_probabilities": dict(query.query_id_probabilities),
        "offset_unit_probabilities": dict(query.offset_unit_probabilities),
        "offset_direction_probabilities": dict(query.offset_direction_probabilities),
        "scene_variant_probabilities": dict(query.scene_variant_probabilities),
        "style_variant_probabilities": dict(query.style_variant_probabilities),
        "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
        "question_format": str(query.query_id),
        "supporting_parts": list(supporting_parts),
        "supporting_point_roles": list(annotation_points.keys()),
      },
      "witness_symbolic": {
        "type": "keyed_point_map",
        "value": dict(annotation_points),
      },
      "projected_annotation": {
        "type": "keyed_point_map",
        "keyed_point_map": dict(annotation_points),
        "pixel_keyed_point_map": dict(annotation_points),
        "pixel_point_map": dict(pixel_point_map),
        "value": dict(annotation_points),
      },
    }

    minute_complexity = 0.25 if int(query.shown_minute) in {0, 15, 30, 45} else 0.55
    second_complexity = 0.20 if int(query.shown_second) in {0, 15, 30, 45} else 0.55
    hand_angle_gap = abs(
      ((float(rendered_scene.entities[2]["attrs"]["angle_deg"]) - float(rendered_scene.entities[1]["attrs"]["angle_deg"]) + 180.0) % 360.0)
      - 180.0
    )
    if is_seconds_offset:
      hand_angle_gap = min(clock_hand_pair_angle_gaps_deg(int(query.shown_total_seconds)))
    offset_norm = normalize_int_with_bounds(
      int(query.delta_seconds) if is_seconds_offset and query.delta_seconds is not None else int(query.delta_minutes or 0),
      [5, 36000] if is_seconds_offset else [5, 600],
    )
    minute_norm = normalize_int_with_bounds(int(query.shown_minute), [0, 55])
    second_norm = normalize_int_with_bounds(int(query.shown_second), [0, 55])
    complexity = build_time_artifact_complexity(
      weights=_COMPLEXITY_WEIGHTS,
      components={
        "time_reading": min(
          1.0,
          (0.55 * float(_TIME_READING_BASE_BY_OFFSET[(str(query.offset_unit), str(query.offset_direction))]))
          + (0.35 * float(minute_norm))
          + (0.10 * float(offset_norm)),
        ),
        "visual_scan": min(
          1.0,
          float(_VISUAL_SCAN_BASE_BY_SCENE[str(query.scene_variant)])
          + float(_VISUAL_SCAN_STYLE_BONUS[str(query.style_variant)])
          + (0.10 * float(minute_norm))
          + (0.08 if is_seconds_offset else 0.0),
        ),
        "ambiguity": min(
          1.0,
          (0.45 * float(1.0 - normalize_float_with_bounds(float(hand_angle_gap), [20.0, 180.0])))
          + (0.22 * float(minute_complexity))
          + (0.23 * float(second_complexity) if is_seconds_offset else 0.0)
          + (0.12 * float(second_norm) if is_seconds_offset else 0.0)
          + 0.14,
        ),
        "clutter": min(
          1.0,
          float(_CLUTTER_BASE_BY_SCENE[str(query.scene_variant)])
          + float(_CLUTTER_STYLE_BONUS[str(query.style_variant)]),
        ),
      },
    )
    return TaskOutput(
      prompt=str(prompt_artifacts.prompt),
      answer_gt=answer_gt,
      annotation_gt=annotation_gt,
      image=image,
      image_id="img0",
      trace_payload=trace_payload,
      complexity=complexity,
      task_versions=default_task_versions(),
      query_id=str(query.query_id),
      prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


def _readout_query_id(output: TaskOutput) -> str:
  """Return the diagnostic query id for one readout output."""

  execution = output.trace_payload.get("execution_trace", {}) if isinstance(output.trace_payload, Mapping) else {}
  unit = str(execution.get("offset_unit", "")).strip()
  direction = str(execution.get("offset_direction", "")).strip()
  if not unit or not direction:
    return "offset_time"
  return f"{unit}_{direction}"


def _fixed_offset_params(params: Mapping[str, Any], *, offset_unit: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
  """Translate public review aliases into fixed offset query params."""

  generation_params = dict(params)
  fixed_params: Dict[str, Any] = {"offset_unit": str(offset_unit)}
  explicit_variant = generation_params.get("query_id")
  if explicit_variant is not None and str(explicit_variant) in _SOURCE_OFFSET_BY_VARIANT:
    alias_unit, alias_direction = _SOURCE_OFFSET_BY_VARIANT[str(explicit_variant)]
    if str(alias_unit) != str(offset_unit):
      raise ValueError(f"query_id={explicit_variant!r} is not valid for {offset_unit} readout")
    fixed_params["offset_direction"] = str(alias_direction)
    generation_params.pop("query_id", None)
  return generation_params, fixed_params


@register_task
class MiscClockOffsetReadoutTask(_MiscClockReadoutBase):
  """Apply a minute or second offset to a single analog clock."""

  task_id = CLOCK_OFFSET_TASK_ID
  fixed_query_id = "offset_time"

  def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
    generation_params = dict(params)
    fixed_params: Dict[str, Any] = {}
    explicit_variant = generation_params.get("query_id")
    if explicit_variant is not None and str(explicit_variant) in _SOURCE_OFFSET_BY_VARIANT:
      alias_unit, alias_direction = _SOURCE_OFFSET_BY_VARIANT[str(explicit_variant)]
      fixed_params["offset_unit"] = str(alias_unit)
      fixed_params["offset_direction"] = str(alias_direction)
      generation_params.pop("query_id", None)
    output = super().generate(
      int(instance_seed),
      params=force_time_artifact_query_params(
        generation_params,
        query_id="offset_time",
        fixed_params=fixed_params,
      ),
      max_attempts=int(max_attempts),
    )
    return rewrite_time_artifact_query_output(
      output,
      query_id=_readout_query_id(output),
      scene_id=PUBLIC_SCENE_ID,
    )


__all__ = [
  "MiscClockOffsetReadoutTask",
]

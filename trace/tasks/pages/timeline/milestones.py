"""Milestone-timeline page task with ordering and interval-count queries."""

from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
  PROMPT_OUTPUT_MODES,
  build_prompt_trace_artifacts,
  render_task_prompt_variants,
)
from ...shared.time_artifact_complexity import (
  build_time_artifact_complexity,
  normalize_int_with_bounds,
  resolve_time_artifact_complexity_weights,
)
from ...shared.time_artifact_style import (
  SUPPORTED_TIME_ARTIFACT_COLOR_NAMES,
  SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS,
  build_time_artifact_timeline_theme,
)
from ...shared.time_artifact_fixed_query import rewrite_time_artifact_query_output
from ...shared.time_artifact_task_support import resolve_time_artifact_named_variant, resolve_time_artifact_selection_index
from ...shared.time_format import format_month_day_label, month_name
from ..shared.timeline_scene import (
  SUPPORTED_PAGE_TIMELINE_SCENE_VARIANTS,
  TimelineEventSpec,
  TimelineRenderParams,
  render_timeline_scene,
  resolve_timeline_render_params,
)
from ..shared.visual_defaults import load_pages_background_defaults, load_pages_noise_defaults


TASK_ID = "pages_timeline_milestones_base"
INTERVAL_MEMBERSHIP_TASK_ID = "task_pages__timeline__interval_membership_count"
PUBLIC_SCENE_ID = "timeline"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
  "interval_membership_count",
)
_SOURCE_INTERVAL_RELATION_BY_VARIANT = {
  "between_reference_events_count": "between",
  "outside_reference_interval_count": "outside",
}
_SUPPORTED_INTERVAL_RELATIONS: Tuple[str, ...] = ("between", "outside")

_TIMELINE_ORDER_BASE_BY_RELATION = {
  "between": 0.56,
  "outside": 0.62,
}
_VISUAL_SCAN_BASE_BY_SCENE = {
  "classic": 0.40,
  "roadmap": 0.48,
  "minimal": 0.30,
}
_VISUAL_SCAN_STYLE_BONUS = {
  "studio": 0.00,
  "accented": 0.04,
  "marker": 0.06,
}
_CLUTTER_BASE_BY_SCENE = {
  "classic": 0.28,
  "roadmap": 0.34,
  "minimal": 0.20,
}
_CLUTTER_STYLE_BONUS = {
  "studio": 0.00,
  "accented": 0.04,
  "marker": 0.07,
}
_BALANCE_SALT = 73961


@dataclass(frozen=True)
class _TaskDefaults:
  """Stable fallback defaults for milestone-timeline scenes."""

  year_min: int = 2024
  year_max: int = 2030
  event_count_support: Tuple[int, ...] = (6, 7, 8, 9, 10, 11, 12)
  between_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
  outside_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8)
  event_label_pool: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L")
  canvas_width: int = 1120
  canvas_height: int = 700
  outer_margin_px: int = 34
  title_height_px: int = 86
  title_gap_px: int = 18
  panel_corner_radius_px: int = 20
  panel_outline_width_px: int = 3
  axis_width_px: int = 4
  axis_tick_height_px: int = 12
  marker_radius_px: int = 10
  marker_outline_width_px: int = 3
  connector_width_px: int = 3
  card_width_px: int = 106
  card_height_px: int = 70
  card_corner_radius_px: int = 14
  card_outline_width_px: int = 3
  label_font_size_px: int = 22
  date_font_size_px: int = 16
  title_font_size_px: int = 30
  subtitle_font_size_px: int = 18
  event_vertical_gap_px: int = 16
  event_stem_length_px: int = 44


@dataclass(frozen=True)
class _RawTimelineEvent:
  """Task-internal milestone record before rendering."""

  event_id: str
  label: str
  day_of_month: int
  order_index: int
  reference_kind: str = "none"

  @property
  def date_text(self) -> str:
    """Return one placeholder date label for debugging before month binding."""

    return str(self.day_of_month)


@dataclass(frozen=True)
class _ResolvedQuery:
  """Resolved semantic and visual support for one milestone-timeline query."""

  query_variant: str
  interval_relation: str
  scene_variant: str
  style_variant: str
  accent_color_name: str
  year: int
  month: int
  month_name: str
  title_text: str
  subtitle_text: str
  raw_events: Tuple[_RawTimelineEvent, ...]
  answer_value: int
  answer_event_ids: Tuple[str, ...]
  reference_event_ids: Tuple[str, ...]
  event_count_support: Tuple[int, ...]
  between_count_support: Tuple[int, ...]
  outside_count_support: Tuple[int, ...]
  query_variant_probabilities: Dict[str, float]
  interval_relation_probabilities: Dict[str, float]
  scene_variant_probabilities: Dict[str, float]
  style_variant_probabilities: Dict[str, float]
  accent_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "timeline")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
  _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
  task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_time_artifact_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_pages_background_defaults(task_group="timeline")
POST_IMAGE_NOISE_DEFAULTS = load_pages_noise_defaults(task_group="timeline", apply_prob=0.0)


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
  """Resolve one balanced named timeline axis."""

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


def _resolve_int_support(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
  """Resolve one integer support list from config or explicit params."""

  raw_values = params.get(key, group_default(_GEN_DEFAULTS, key, fallback))
  resolved: List[int] = []
  for raw_value in raw_values:
    value = int(raw_value)
    if value not in resolved:
      resolved.append(value)
  if not resolved:
    raise ValueError(f"{key} must not be empty for {TASK_ID}")
  return tuple(int(value) for value in resolved)


def _resolve_str_support(params: Mapping[str, Any], key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
  """Resolve one string support list from config or explicit params."""

  raw_values = params.get(key, group_default(_GEN_DEFAULTS, key, fallback))
  resolved: List[str] = []
  for raw_value in raw_values:
    value = str(raw_value).strip()
    if value and value not in resolved:
      resolved.append(value)
  if not resolved:
    raise ValueError(f"{key} must not be empty for {TASK_ID}")
  return tuple(str(value) for value in resolved)


def _resolve_query_variant(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
  """Resolve the public timeline query variant, accepting old mirror names as aliases."""

  explicit_variant = params.get("query_variant")
  if explicit_variant is not None and str(explicit_variant) in _SOURCE_INTERVAL_RELATION_BY_VARIANT:
    return "interval_membership_count", {"interval_membership_count": 1.0}
  return _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="query_variant",
    weights_key="query_variant_weights",
    balance_flag_key="balanced_query_variant_sampling",
    supported=SUPPORTED_QUERY_VARIANTS,
    namespace="query_variant",
  )


def _normalize_interval_relation(value: Any) -> str:
  """Normalize one timeline interval relation."""

  normalized = str(value).strip().lower()
  if normalized in _SUPPORTED_INTERVAL_RELATIONS:
    return normalized
  raise ValueError(f"unsupported interval_relation: {value}")


def _resolve_interval_relation(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
  """Resolve whether to count events inside or outside the reference interval."""

  source_variant = params.get("query_variant")
  if source_variant is not None and str(source_variant) in _SOURCE_INTERVAL_RELATION_BY_VARIANT:
    selected = str(_SOURCE_INTERVAL_RELATION_BY_VARIANT[str(source_variant)])
    return selected, {
      key: (1.0 if key == selected else 0.0)
      for key in _SUPPORTED_INTERVAL_RELATIONS
    }

  explicit = params.get("interval_relation", params.get("relation"))
  if explicit is not None:
    selected = _normalize_interval_relation(explicit)
    return selected, {
      key: (1.0 if key == selected else 0.0)
      for key in _SUPPORTED_INTERVAL_RELATIONS
    }

  return _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="interval_relation",
    weights_key="interval_relation_weights",
    balance_flag_key="balanced_interval_relation_sampling",
    supported=_SUPPORTED_INTERVAL_RELATIONS,
    namespace="interval_relation",
  )


def _resolve_support_selection_index(
  *,
  params: Mapping[str, Any],
  instance_seed: int,
  namespace: str,
) -> int:
  """Return a support index decoupled from query-variant cycling."""

  return int(resolve_time_artifact_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))


def _decoupled_named_axis_params(
  *,
  params: Mapping[str, Any],
  axis_key: str,
  namespace: str,
) -> Mapping[str, Any]:
  """Return params with one balanced visual axis decoupled from query variants."""

  _ = axis_key, namespace
  return params


def _sample_month(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, int, int]:
  """Sample one Gregorian month and return `(year, month, days_in_month)`."""

  explicit_year = params.get("year")
  explicit_month = params.get("month")
  if explicit_year is not None and explicit_month is None:
    raise ValueError("month must be provided when year is explicit for page timelines")
  if explicit_month is not None and explicit_year is None:
    raise ValueError("year must be provided when month is explicit for page timelines")

  if explicit_year is not None and explicit_month is not None:
    _, days_in_month = calendar.monthrange(int(explicit_year), int(explicit_month))
    return int(explicit_year), int(explicit_month), int(days_in_month)

  year_min = int(params.get("year_min", group_default(_GEN_DEFAULTS, "year_min", _DEFAULTS.year_min)))
  year_max = int(params.get("year_max", group_default(_GEN_DEFAULTS, "year_max", _DEFAULTS.year_max)))
  if int(year_max) < int(year_min):
    raise ValueError("year_max must be >= year_min for page timelines")
  year_support = tuple(range(int(year_min), int(year_max) + 1))
  year = int(
    year_support[
      int(
        _resolve_support_selection_index(
          params=params,
          instance_seed=int(instance_seed),
          namespace=f"{TASK_ID}:year",
        )
        % len(year_support)
      )
    ]
  )
  month = 1 + int(
    _resolve_support_selection_index(
      params=params,
      instance_seed=int(instance_seed),
      namespace=f"{TASK_ID}:month",
    )
    % 12
  )
  _, days_in_month = calendar.monthrange(int(year), int(month))
  return int(year), int(month), int(days_in_month)


def _build_raw_events(
  *,
  month: int,
  day_values: Sequence[int],
  labels: Sequence[str],
  primary_reference_index: int | None,
  secondary_reference_index: int | None,
) -> Tuple[_RawTimelineEvent, ...]:
  """Build one ordered milestone list from sampled labels and dates."""

  del month
  events: List[_RawTimelineEvent] = []
  for index, (label, day_of_month) in enumerate(zip(labels, day_values)):
    reference_kind = "none"
    if primary_reference_index is not None and int(index) == int(primary_reference_index):
      reference_kind = "primary"
    elif secondary_reference_index is not None and int(index) == int(secondary_reference_index):
      reference_kind = "secondary"
    events.append(
      _RawTimelineEvent(
        event_id=f"event_{str(label).lower()}",
        label=str(label),
        day_of_month=int(day_of_month),
        order_index=int(index),
        reference_kind=str(reference_kind),
      )
    )
  return tuple(events)


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
  """Resolve one concrete milestone-timeline query from balanced supports."""

  query_variant, query_variant_probabilities = _resolve_query_variant(
    instance_seed=int(instance_seed),
    params=params,
  )
  interval_relation, interval_relation_probabilities = _resolve_interval_relation(
    instance_seed=int(instance_seed),
    params=params,
  )
  scene_variant, scene_variant_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=_decoupled_named_axis_params(
      params=params,
      axis_key="scene_variant",
      namespace=f"{TASK_ID}:scene_variant",
    ),
    explicit_key="scene_variant",
    weights_key="scene_variant_weights",
    balance_flag_key="balanced_scene_variant_sampling",
    supported=SUPPORTED_PAGE_TIMELINE_SCENE_VARIANTS,
    namespace="scene_variant",
  )
  style_variant, style_variant_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=_decoupled_named_axis_params(
      params=params,
      axis_key="style_variant",
      namespace=f"{TASK_ID}:style_variant",
    ),
    explicit_key="style_variant",
    weights_key="style_variant_weights",
    balance_flag_key="balanced_style_variant_sampling",
    supported=SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS,
    namespace="style_variant",
  )
  accent_color_name, accent_color_name_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=_decoupled_named_axis_params(
      params=params,
      axis_key="accent_color_name",
      namespace=f"{TASK_ID}:accent_color_name",
    ),
    explicit_key="accent_color_name",
    weights_key="accent_color_name_weights",
    balance_flag_key="balanced_accent_color_name_sampling",
    supported=SUPPORTED_TIME_ARTIFACT_COLOR_NAMES,
    namespace="accent_color_name",
  )

  year, month, days_in_month = _sample_month(int(instance_seed), params)
  event_count_support = _resolve_int_support(params, "event_count_support", _DEFAULTS.event_count_support)
  between_count_support = _resolve_int_support(params, "between_count_support", _DEFAULTS.between_count_support)
  outside_count_support = _resolve_int_support(params, "outside_count_support", _DEFAULTS.outside_count_support)
  event_label_pool = _resolve_str_support(params, "event_label_pool", _DEFAULTS.event_label_pool)

  max_event_count = min(int(days_in_month), len(event_label_pool), max(int(value) for value in event_count_support))
  if int(max_event_count) < min(int(value) for value in event_count_support):
    raise ValueError("timeline month does not have enough days for the configured event_count_support")

  if str(interval_relation) == "between":
    feasible_answers = [int(value) for value in between_count_support if 0 <= int(value) <= int(max_event_count - 2)]
    if not feasible_answers:
      raise ValueError("between_count_support has no feasible values for page timelines")
    answer_value = int(
      feasible_answers[
        int(
          _resolve_support_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:between_answer",
          )
          % len(feasible_answers)
        )
      ]
    )
    feasible_event_counts = [int(value) for value in event_count_support if int(answer_value + 2) <= int(value) <= int(max_event_count)]
    event_count = int(
      feasible_event_counts[
        int(
          _resolve_support_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:between_event_count",
          )
          % len(feasible_event_counts)
        )
      ]
    )
    left_index_support = list(range(0, int(event_count - answer_value - 1)))
    primary_reference_index = int(
      left_index_support[
        int(
          _resolve_support_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:between_left_index",
          )
          % len(left_index_support)
        )
      ]
    )
    secondary_reference_index = int(primary_reference_index + answer_value + 1)
    answer_indices = tuple(range(int(primary_reference_index + 1), int(secondary_reference_index)))
  else:
    feasible_answers = [int(value) for value in outside_count_support if 1 <= int(value) <= int(max_event_count - 2)]
    if not feasible_answers:
      raise ValueError("outside_count_support has no feasible values for page timelines")
    answer_value = int(
      feasible_answers[
        int(
          _resolve_support_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:outside_answer",
          )
          % len(feasible_answers)
        )
      ]
    )
    feasible_event_counts = [int(value) for value in event_count_support if int(answer_value + 2) <= int(value) <= int(max_event_count)]
    event_count = int(
      feasible_event_counts[
        int(
          _resolve_support_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:outside_event_count",
          )
          % len(feasible_event_counts)
        )
      ]
    )
    left_outside_support = tuple(range(0, int(answer_value) + 1))
    left_outside_count = int(
      left_outside_support[
        int(
          _resolve_support_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:outside_left_count",
          )
          % len(left_outside_support)
        )
      ]
    )
    right_outside_count = int(answer_value - left_outside_count)
    primary_reference_index = int(left_outside_count)
    secondary_reference_index = int(event_count - right_outside_count - 1)
    answer_indices = tuple(range(0, int(primary_reference_index))) + tuple(
      range(int(secondary_reference_index + 1), int(event_count))
    )

  labels = tuple(str(label) for label in event_label_pool[:event_count])
  rng = spawn_rng(int(instance_seed), f"{TASK_ID}.days")
  day_values = tuple(sorted(int(value) for value in rng.sample(list(range(1, int(days_in_month) + 1)), k=int(event_count))))
  raw_events = _build_raw_events(
    month=int(month),
    day_values=tuple(day_values),
    labels=labels,
    primary_reference_index=(int(primary_reference_index) if primary_reference_index is not None else None),
    secondary_reference_index=(int(secondary_reference_index) if secondary_reference_index is not None else None),
  )
  answer_event_ids = tuple(str(raw_events[index].event_id) for index in answer_indices)
  reference_event_ids = tuple(
    str(raw_events[index].event_id)
    for index in (primary_reference_index, secondary_reference_index)
    if index is not None
  )

  return _ResolvedQuery(
    query_variant=str(query_variant),
    interval_relation=str(interval_relation),
    scene_variant=str(scene_variant),
    style_variant=str(style_variant),
    accent_color_name=str(accent_color_name),
    year=int(year),
    month=int(month),
    month_name=str(month_name(int(month))),
    title_text="Milestone timeline",
    subtitle_text=f"{month_name(int(month))} {int(year)}",
    raw_events=tuple(raw_events),
    answer_value=int(answer_value),
    answer_event_ids=tuple(answer_event_ids),
    reference_event_ids=tuple(reference_event_ids),
    event_count_support=tuple(int(value) for value in event_count_support),
    between_count_support=tuple(int(value) for value in between_count_support),
    outside_count_support=tuple(int(value) for value in outside_count_support),
    query_variant_probabilities=dict(query_variant_probabilities),
    interval_relation_probabilities=dict(interval_relation_probabilities),
    scene_variant_probabilities=dict(scene_variant_probabilities),
    style_variant_probabilities=dict(style_variant_probabilities),
    accent_color_name_probabilities=dict(accent_color_name_probabilities),
  )


def _resolve_card_side(*, scene_variant: str, order_index: int) -> str:
  """Resolve whether one event card sits above or below the timeline axis."""

  if str(scene_variant) == "minimal":
    return "above"
  if str(scene_variant) == "roadmap":
    return "above" if (int(order_index) % 3) != 1 else "below"
  return "above" if (int(order_index) % 2) == 0 else "below"


class _PagesTimelineMilestonesBase:
  """Reason over one milestone timeline with several numeric ordering queries."""

  task_id = TASK_ID
  domain = "pages"
  task_group = "timeline"

  def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
    del max_attempts
    query = _resolve_query(int(instance_seed), params=params)
    render_params = resolve_timeline_render_params(
      params,
      render_defaults=_RENDER_DEFAULTS,
      fallback_values=asdict(_DEFAULTS),
      instance_seed=int(instance_seed),
    )
    timeline_theme = build_time_artifact_timeline_theme(
      accent_color_name=str(query.accent_color_name),
      style_variant=str(query.style_variant),
    )

    background, background_meta = make_background_canvas(
      canvas_width=int(render_params.canvas_width),
      canvas_height=int(render_params.canvas_height),
      instance_seed=int(instance_seed),
      params=params,
      default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    image = background.copy().convert("RGB")
    rendered_events = tuple(
      TimelineEventSpec(
        event_id=str(event.event_id),
        label=str(event.label),
        date_text=str(format_month_day_label(int(query.month), int(event.day_of_month))),
        order_index=int(event.order_index),
        anchor_x_px=0.0,
        card_side=str(_resolve_card_side(scene_variant=str(query.scene_variant), order_index=int(event.order_index))),
        reference_kind=str(event.reference_kind),
      )
      for event in query.raw_events
    )
    rendered_scene = render_timeline_scene(
      image,
      title_text=str(query.title_text),
      subtitle_text=str(query.subtitle_text),
      events=rendered_events,
      scene_variant=str(query.scene_variant),
      render_params=render_params,
      visual_theme=timeline_theme,
    )
    image, post_noise_meta = apply_post_image_noise(
      image,
      instance_seed=int(instance_seed),
      params=params,
      default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    evidence_bboxes = [
      [round(float(value), 3) for value in rendered_scene.event_bboxes_by_id[str(event_id)]]
      for event_id in query.answer_event_ids
    ]

    answer_hint_key = f"answer_hint_{query.interval_relation}"
    evidence_hint_key = f"evidence_hint_{query.interval_relation}"
    object_description_key = f"object_description_{query.query_variant}"
    interval_relation_description_key = f"interval_relation_description_{query.interval_relation}"
    json_example_key = f"json_example_{query.interval_relation}"
    json_example_answer_only_key = f"json_example_answer_only_{query.interval_relation}"
    prompt_defaults = required_group_defaults(
      _PROMPT_DEFAULTS,
      (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        object_description_key,
        interval_relation_description_key,
        answer_hint_key,
        evidence_hint_key,
        json_example_key,
        json_example_answer_only_key,
      ),
      context=f"prompt defaults for {self.task_id}",
    )
    object_description = str(prompt_defaults[object_description_key]).format(
      month_name_text=str(query.month_name),
      year=int(query.year),
    )
    slots: Dict[str, str] = {
      "object_description": str(object_description),
      "interval_relation_description": str(prompt_defaults[interval_relation_description_key]),
      "json_output_contract": str(prompt_defaults["json_output_contract"]),
      "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
      "evidence_hint": str(prompt_defaults[evidence_hint_key]),
      "answer_hint": str(prompt_defaults[answer_hint_key]),
      "json_example": str(prompt_defaults[json_example_key]),
      "json_example_answer_only": str(prompt_defaults[json_example_answer_only_key]),
    }

    prompt_selection = render_task_prompt_variants(
      domain=self.domain,
      task_group=self.task_group,
      bundle_id=str(prompt_defaults["bundle_id"]),
      scene_key=str(prompt_defaults["scene_key"]),
      task_key=str(prompt_defaults["task_key"]),
      query_key=str(query.query_variant),
      answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
      slots=slots,
      instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    answer_gt = TypedValue(type="integer", value=int(query.answer_value))
    evidence_gt = TypedValue(type="bbox_set", value=[list(box) for box in evidence_bboxes])

    event_records = [
      {
        "event_id": str(event.event_id),
        "label": str(event.label),
        "day_of_month": int(event.day_of_month),
        "date_text": str(format_month_day_label(int(query.month), int(event.day_of_month))),
        "order_index": int(event.order_index),
        "reference_kind": str(event.reference_kind),
        "card_side": str(_resolve_card_side(scene_variant=str(query.scene_variant), order_index=int(event.order_index))),
      }
      for event in query.raw_events
    ]

    trace_payload = {
      "scene_ir": {
        "scene_kind": "pages_milestone_timeline",
        "entities": [dict(entity) for entity in rendered_scene.entities],
        "relations": {
          "query_variant": str(query.query_variant),
          "interval_relation": str(query.interval_relation),
          "scene_variant": str(query.scene_variant),
          "style_variant": str(query.style_variant),
          "accent_color_name": str(query.accent_color_name),
          "year": int(query.year),
          "month": int(query.month),
          "month_name": str(query.month_name),
          "reference_event_ids": [str(value) for value in query.reference_event_ids],
        },
      },
      "query_spec": {
        "query_variant": str(query.query_variant),
        "template_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
        "params": {
          "query_variant": str(query.query_variant),
          "interval_relation": str(query.interval_relation),
          "scene_variant": str(query.scene_variant),
          "style_variant": str(query.style_variant),
          "accent_color_name": str(query.accent_color_name),
          "year": int(query.year),
          "month": int(query.month),
          "month_name": str(query.month_name),
          "event_count_support": [int(value) for value in query.event_count_support],
          "between_count_support": [int(value) for value in query.between_count_support],
          "outside_count_support": [int(value) for value in query.outside_count_support],
          "query_variant_probabilities": dict(query.query_variant_probabilities),
          "interval_relation_probabilities": dict(query.interval_relation_probabilities),
          "scene_variant_probabilities": dict(query.scene_variant_probabilities),
          "style_variant_probabilities": dict(query.style_variant_probabilities),
          "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
        },
      },
      "render_spec": {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": str(query.scene_variant),
        "background_style": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
        "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
        "timeline_style": {
          "accent_color_name": str(query.accent_color_name),
          "style_variant": str(query.style_variant),
          "title_text": str(query.title_text),
          "subtitle_text": str(query.subtitle_text),
          "resolved_colors_rgb": {
            "panel_fill": [int(value) for value in timeline_theme.panel_fill_rgb],
            "panel_outline": [int(value) for value in timeline_theme.panel_outline_rgb],
            "axis_line": [int(value) for value in timeline_theme.axis_line_rgb],
            "event_fill": [int(value) for value in timeline_theme.event_fill_rgb],
            "event_outline": [int(value) for value in timeline_theme.event_outline_rgb],
            "primary_reference_fill": [int(value) for value in timeline_theme.primary_reference_fill_rgb],
            "secondary_reference_fill": [int(value) for value in timeline_theme.secondary_reference_fill_rgb],
          },
        },
      },
      "render_map": {
        "image_id": "img0",
        "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
        "panel_bbox_px": [round(float(value), 3) for value in rendered_scene.panel_bbox_px],
        "axis_bbox_px": [round(float(value), 3) for value in rendered_scene.axis_bbox_px],
        "title_text": str(rendered_scene.title_text),
        "subtitle_text": str(rendered_scene.subtitle_text),
        "event_bboxes_by_id": {
          str(event_id): [round(float(value), 3) for value in bbox]
          for event_id, bbox in rendered_scene.event_bboxes_by_id.items()
        },
        "reference_event_ids": [str(value) for value in query.reference_event_ids],
        "answer_event_ids": [str(value) for value in query.answer_event_ids],
      },
      "execution_trace": {
        "query_variant": str(query.query_variant),
        "interval_relation": str(query.interval_relation),
        "scene_variant": str(query.scene_variant),
        "style_variant": str(query.style_variant),
        "accent_color_name": str(query.accent_color_name),
        "year": int(query.year),
        "month": int(query.month),
        "month_name": str(query.month_name),
        "event_count": len(query.raw_events),
        "answer_value": int(query.answer_value),
        "answer_event_ids": [str(value) for value in query.answer_event_ids],
        "reference_event_ids": [str(value) for value in query.reference_event_ids],
        "events": event_records,
        "query_variant_probabilities": dict(query.query_variant_probabilities),
        "interval_relation_probabilities": dict(query.interval_relation_probabilities),
        "scene_variant_probabilities": dict(query.scene_variant_probabilities),
        "style_variant_probabilities": dict(query.style_variant_probabilities),
        "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
      },
      "witness_symbolic": {
        "type": "bbox_set",
        "value": [list(box) for box in evidence_bboxes],
      },
      "projected_evidence": {
        "bbox_set": [list(box) for box in evidence_bboxes],
      },
    }

    event_count = len(query.raw_events)
    reference_index = next(
      int(event.order_index)
      for event in query.raw_events
      if str(event.reference_kind) == "primary"
    )
    secondary_index = next(
      int(event.order_index)
      for event in query.raw_events
      if str(event.reference_kind) == "secondary"
    )
    reference_span = int(secondary_index - reference_index)
    reference_edge_distance = int(min(reference_index, max(0, event_count - 1 - secondary_index)))

    complexity = build_time_artifact_complexity(
      weights=_COMPLEXITY_WEIGHTS,
      components={
        "timeline_order_reasoning": min(
          1.0,
          float(_TIMELINE_ORDER_BASE_BY_RELATION[str(query.interval_relation)])
          + (
            0.18
            * float(
              normalize_int_with_bounds(
                int(query.answer_value),
                [0, 8],
              )
            )
          )
          + (0.08 * float(normalize_int_with_bounds(int(reference_span), [0, 7]))),
        ),
        "visual_scan": min(
          1.0,
          float(_VISUAL_SCAN_BASE_BY_SCENE[str(query.scene_variant)])
          + float(_VISUAL_SCAN_STYLE_BONUS[str(query.style_variant)])
          + (0.24 * float(normalize_int_with_bounds(int(event_count), [6, 12]))),
        ),
        "ambiguity": min(
          1.0,
          0.10
          + (0.16 * float(normalize_int_with_bounds(int(event_count), [6, 12])))
          + (
            0.24
            * float(
              normalize_int_with_bounds(
                int(reference_edge_distance),
                [0, 4],
              )
            )
          )
          + (
            0.12
            * float(
              normalize_int_with_bounds(
                int(query.answer_value),
                [0, 8],
              )
            )
          ),
        ),
        "clutter": min(
          1.0,
          float(_CLUTTER_BASE_BY_SCENE[str(query.scene_variant)])
          + float(_CLUTTER_STYLE_BONUS[str(query.style_variant)])
          + (0.20 * float(normalize_int_with_bounds(int(event_count), [6, 12]))),
        ),
      },
    )

    return TaskOutput(
      prompt=str(prompt_artifacts.prompt),
      answer_gt=answer_gt,
      evidence_gt=evidence_gt,
      image=image,
      image_id="img0",
      trace_payload=trace_payload,
      complexity=complexity,
      task_versions=default_task_versions(),
      query_variant=str(query.query_variant),
      prompt_variants=dict(prompt_artifacts.prompt_variants),
    )


def _timeline_query_id(output: TaskOutput) -> str:
  """Return the diagnostic query id for one timeline interval output."""

  execution = output.trace_payload.get("execution_trace", {}) if isinstance(output.trace_payload, Mapping) else {}
  relation = str(execution.get("interval_relation", "")).strip()
  if relation == "between":
    return "between_reference_events_count"
  if relation == "outside":
    return "outside_reference_interval_count"
  return "interval_membership_count"


@register_task
class PagesTimelineIntervalMembershipCountTask(_PagesTimelineMilestonesBase):
  """Count timeline events inside or outside a highlighted reference interval."""

  task_id = INTERVAL_MEMBERSHIP_TASK_ID
  fixed_query_variant = "interval_membership_count"

  def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
    output = super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts))
    return rewrite_time_artifact_query_output(
      output,
      query_id=_timeline_query_id(output),
      scene_id=PUBLIC_SCENE_ID,
    )


__all__ = ["PagesTimelineIntervalMembershipCountTask"]

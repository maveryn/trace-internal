"""Month-view calendar page task with date lookup and marked-date counting queries."""

from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
  PROMPT_OUTPUT_MODES,
  build_prompt_trace_artifacts,
  render_task_prompt_variants,
)
from ..shared.calendar_scene import (
  CalendarRenderParams,
  SUPPORTED_PAGE_CALENDAR_SCENE_VARIANTS,
  render_month_calendar_scene,
  resolve_calendar_render_params,
)
from ...shared.time_artifact_complexity import (
  build_time_artifact_complexity,
  normalize_int_with_bounds,
  resolve_time_artifact_complexity_weights,
)
from ...shared.time_artifact_fixed_query import force_time_artifact_query_params, rewrite_time_artifact_query_output
from ...shared.time_artifact_style import (
  SUPPORTED_TIME_ARTIFACT_COLOR_NAMES,
  SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS,
  build_time_artifact_calendar_theme,
)
from ...shared.time_artifact_task_support import resolve_time_artifact_named_variant
from ...shared.time_format import month_name, ordinal_label, weekday_name
from ..shared.visual_defaults import load_pages_background_defaults, load_pages_noise_defaults


TASK_ID = "pages_calendar_month_view_base"
WEEKDAY_OCCURRENCE_TASK_ID = "task_pages__calendar__weekday_occurrence_date"
MARKED_DAY_CLASS_TASK_ID = "task_pages__calendar__marked_day_class_count"
PUBLIC_SCENE_ID = "calendar"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
  "date_of_weekday_occurrence",
  "count_marked_day_class",
)
_SOURCE_MARKED_DAY_CLASS_BY_VARIANT = {
  "count_marked_weekend_days": "weekend",
  "count_marked_weekday_days": "weekday",
}
_SUPPORTED_MARKED_DAY_CLASSES: Tuple[str, ...] = ("weekend", "weekday")

_CALENDAR_LOOKUP_BASE_BY_VARIANT = {
  "date_of_weekday_occurrence": 0.56,
  "count_marked_day_class": 0.45,
}
_VISUAL_SCAN_BASE_BY_SCENE = {
  "classic": 0.44,
  "minimal": 0.32,
  "outline": 0.38,
}
_VISUAL_SCAN_STYLE_BONUS = {
  "studio": 0.00,
  "accented": 0.04,
  "marker": 0.06,
}
_CLUTTER_BASE_BY_SCENE = {
  "classic": 0.34,
  "minimal": 0.18,
  "outline": 0.24,
}
_CLUTTER_STYLE_BONUS = {
  "studio": 0.00,
  "accented": 0.04,
  "marker": 0.08,
}


@dataclass(frozen=True)
class _TaskDefaults:
  """Stable fallback defaults for month-view calendar scenes."""

  year_min: int = 2022
  year_max: int = 2030
  weekend_weekday_indices: Tuple[int, int] = (5, 6)
  date_occurrence_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
  marked_weekend_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
  marked_weekday_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
  marked_weekday_distractor_support: Tuple[int, ...] = (1, 2, 3, 4)
  marked_weekend_distractor_support: Tuple[int, ...] = (1, 2, 3, 4)
  canvas_width: int = 860
  canvas_height: int = 760
  outer_margin_px: int = 34
  title_height_px: int = 64
  title_bottom_gap_px: int = 14
  weekday_header_height_px: int = 34
  weekday_grid_gap_px: int = 10
  cell_gap_px: int = 8
  panel_corner_radius_px: int = 18
  panel_outline_width_px: int = 3
  cell_corner_radius_px: int = 12
  cell_outline_width_px: int = 2
  title_font_size_px: int = 30
  weekday_font_size_px: int = 16
  date_font_size_px: int = 22
  marker_inset_px: int = 10
  marker_outline_width_px: int = 3


@dataclass(frozen=True)
class _ResolvedQuery:
  """Resolved semantic and visual support for one month-view calendar query."""

  query_variant: str
  marked_day_class: str | None
  scene_variant: str
  style_variant: str
  accent_color_name: str
  year: int
  month: int
  month_name: str
  row_count: int
  start_weekday_index: int
  days_in_month: int
  marked_dates: Tuple[int, ...]
  evidence_dates: Tuple[int, ...]
  answer_value: int
  query_weekday_index: int | None
  query_occurrence: int | None
  weekend_weekday_indices: Tuple[int, ...]
  date_occurrence_support: Tuple[int, ...]
  marked_weekend_count_support: Tuple[int, ...]
  marked_weekday_count_support: Tuple[int, ...]
  marked_weekday_distractor_support: Tuple[int, ...]
  marked_weekend_distractor_support: Tuple[int, ...]
  query_variant_probabilities: Dict[str, float]
  marked_day_class_probabilities: Dict[str, float]
  scene_variant_probabilities: Dict[str, float]
  style_variant_probabilities: Dict[str, float]
  accent_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "calendar")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
  _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
  task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_time_artifact_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_pages_background_defaults(task_group="calendar")
POST_IMAGE_NOISE_DEFAULTS = load_pages_noise_defaults(task_group="calendar", apply_prob=0.0)


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
  """Resolve one balanced named calendar-task axis."""

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
  """Resolve one integer support list from task config or explicit params."""

  raw_values = params.get(key, group_default(_GEN_DEFAULTS, key, fallback))
  resolved: List[int] = []
  for raw_value in raw_values:
    value = int(raw_value)
    if value not in resolved:
      resolved.append(value)
  if not resolved:
    raise ValueError(f"{key} must not be empty for {TASK_ID}")
  return tuple(int(value) for value in resolved)


def _resolve_query_variant(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
  """Resolve the public calendar query variant, accepting old mirror names as aliases."""

  explicit_variant = params.get("query_variant")
  if explicit_variant is not None and str(explicit_variant) in _SOURCE_MARKED_DAY_CLASS_BY_VARIANT:
    return "count_marked_day_class", {
      key: (1.0 if key == "count_marked_day_class" else 0.0)
      for key in SUPPORTED_QUERY_VARIANTS
    }
  return _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="query_variant",
    weights_key="query_variant_weights",
    balance_flag_key="balanced_query_variant_sampling",
    supported=SUPPORTED_QUERY_VARIANTS,
    namespace="query_variant",
  )


def _normalize_marked_day_class(value: Any) -> str:
  """Normalize one marked-day class label."""

  normalized = str(value).strip().lower()
  if normalized in {"weekend", "weekends"}:
    return "weekend"
  if normalized in {"weekday", "weekdays"}:
    return "weekday"
  raise ValueError(f"unsupported marked_day_class: {value}")


def _resolve_marked_day_class(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
) -> Tuple[str, Dict[str, float]]:
  """Resolve the weekday/weekend class for marked-date count queries."""

  source_variant = params.get("query_variant")
  if source_variant is not None and str(source_variant) in _SOURCE_MARKED_DAY_CLASS_BY_VARIANT:
    selected = str(_SOURCE_MARKED_DAY_CLASS_BY_VARIANT[str(source_variant)])
    return selected, {
      key: (1.0 if key == selected else 0.0)
      for key in _SUPPORTED_MARKED_DAY_CLASSES
    }

  explicit = params.get("marked_day_class", params.get("day_class"))
  if explicit is not None:
    selected = _normalize_marked_day_class(explicit)
    return selected, {
      key: (1.0 if key == selected else 0.0)
      for key in _SUPPORTED_MARKED_DAY_CLASSES
    }

  return _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=_axis_params_for_decoupled_sampling(
      params=params,
      divisor=len(SUPPORTED_QUERY_VARIANTS),
      explicit_key="marked_day_class",
    ),
    explicit_key="marked_day_class",
    weights_key="marked_day_class_weights",
    balance_flag_key="balanced_marked_day_class_sampling",
    supported=_SUPPORTED_MARKED_DAY_CLASSES,
    namespace="marked_day_class",
  )


def _axis_params_for_decoupled_sampling(
  *,
  params: Mapping[str, Any],
  divisor: int,
  explicit_key: str,
) -> Mapping[str, Any]:
  """No-op hook for axis-decoupling call sites."""

  _ = int(divisor), str(explicit_key)
  return params


def _marked_day_class_phrase(marked_day_class: str) -> str:
  """Return a prompt phrase for one marked-day class."""

  return "Saturday or Sunday" if str(marked_day_class) == "weekend" else "Monday through Friday"


def _sample_month(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, int, int, int]:
  """Sample one Gregorian month and return `(year, month, start_weekday, days_in_month)`."""

  explicit_year = params.get("year")
  explicit_month = params.get("month")
  if explicit_year is not None and explicit_month is None:
    raise ValueError("month must be provided when year is explicit for page calendars")
  if explicit_month is not None and explicit_year is None:
    raise ValueError("year must be provided when month is explicit for page calendars")

  if explicit_year is not None and explicit_month is not None:
    year = int(explicit_year)
    month = int(explicit_month)
    start_weekday_index, days_in_month = calendar.monthrange(int(year), int(month))
    return int(year), int(month), int(start_weekday_index), int(days_in_month)

  year_min = int(params.get("year_min", group_default(_GEN_DEFAULTS, "year_min", _DEFAULTS.year_min)))
  year_max = int(params.get("year_max", group_default(_GEN_DEFAULTS, "year_max", _DEFAULTS.year_max)))
  if int(year_max) < int(year_min):
    raise ValueError("year_max must be >= year_min for page calendars")

  year_support = tuple(range(int(year_min), int(year_max) + 1))
  year = int(
    year_support[
      int(
        resolve_selection_index(
          params=params,
          instance_seed=int(instance_seed),
          namespace=f"{TASK_ID}:year",
        )
        % len(year_support)
      )
    ]
  )
  month = 1 + int(
    resolve_selection_index(
      params=params,
      instance_seed=int(instance_seed),
      namespace=f"{TASK_ID}:month",
    )
    % 12
  )
  start_weekday_index, days_in_month = calendar.monthrange(int(year), int(month))
  return int(year), int(month), int(start_weekday_index), int(days_in_month)


def _resolve_marked_count_query(
  *,
  instance_seed: int,
  params: Mapping[str, Any],
  days_in_month: int,
  weekend_weekday_indices: Tuple[int, ...],
  year: int,
  month: int,
  target_weekend: bool,
) -> Tuple[Tuple[int, ...], Tuple[int, ...], int]:
  """Resolve the marked-date set for one marked weekday/weekend count query."""

  month_weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(int(year), int(month))
  weekend_dates = sorted(
    int(day)
    for week in month_weeks
    for weekday_index, day in enumerate(week)
    if int(day) > 0 and int(weekday_index) in set(int(value) for value in weekend_weekday_indices)
  )
  weekday_dates = [int(day) for day in range(1, int(days_in_month) + 1) if int(day) not in set(weekend_dates)]
  target_dates = weekend_dates if bool(target_weekend) else weekday_dates
  distractor_dates = weekday_dates if bool(target_weekend) else weekend_dates
  target_key = "marked_weekend_count_support" if bool(target_weekend) else "marked_weekday_count_support"
  target_fallback = (
    _DEFAULTS.marked_weekend_count_support if bool(target_weekend) else _DEFAULTS.marked_weekday_count_support
  )
  distractor_key = (
    "marked_weekday_distractor_support" if bool(target_weekend) else "marked_weekend_distractor_support"
  )
  distractor_fallback = (
    _DEFAULTS.marked_weekday_distractor_support
    if bool(target_weekend)
    else _DEFAULTS.marked_weekend_distractor_support
  )

  target_support = [
    int(value)
    for value in _resolve_int_support(params, target_key, target_fallback)
    if 0 <= int(value) <= len(target_dates)
  ]
  if not target_support:
    raise ValueError("no feasible marked date-count support exists for this month")
  target_count = int(
    target_support[
      int(
        resolve_selection_index(
          params=params,
          instance_seed=int(instance_seed),
          namespace=f"{TASK_ID}:{target_key}",
        )
        % len(target_support)
      )
    ]
  )

  distractor_support = [
    int(value)
    for value in _resolve_int_support(params, distractor_key, distractor_fallback)
    if 0 <= int(value) <= len(distractor_dates)
  ]
  if not distractor_support:
    raise ValueError("no feasible marked date distractor support exists for this month")
  distractor_count = int(
    distractor_support[
      int(
        resolve_selection_index(
          params=params,
          instance_seed=int(instance_seed),
          namespace=f"{TASK_ID}:{distractor_key}",
        )
        % len(distractor_support)
      )
    ]
  )

  rng = spawn_rng(int(instance_seed), f"{TASK_ID}.marked_dates")
  target_marked_dates = tuple(sorted(int(day) for day in rng.sample(target_dates, k=int(target_count))))
  distractor_marked_dates = tuple(sorted(int(day) for day in rng.sample(distractor_dates, k=int(distractor_count))))
  marked_dates = tuple(sorted(int(day) for day in (*target_marked_dates, *distractor_marked_dates)))
  return tuple(int(day) for day in marked_dates), tuple(int(day) for day in target_marked_dates), int(target_count)


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
  """Resolve one concrete month-calendar query from balanced supports."""

  query_variant, query_variant_probabilities = _resolve_query_variant(
    instance_seed=int(instance_seed),
    params=params,
  )
  scene_variant, scene_variant_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="scene_variant",
    weights_key="scene_variant_weights",
    balance_flag_key="balanced_scene_variant_sampling",
    supported=SUPPORTED_PAGE_CALENDAR_SCENE_VARIANTS,
    namespace="scene_variant",
  )
  style_variant, style_variant_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="style_variant",
    weights_key="style_variant_weights",
    balance_flag_key="balanced_style_variant_sampling",
    supported=SUPPORTED_TIME_ARTIFACT_STYLE_VARIANTS,
    namespace="style_variant",
  )
  accent_color_name, accent_color_name_probabilities = _resolve_named_variant(
    instance_seed=int(instance_seed),
    params=params,
    explicit_key="accent_color_name",
    weights_key="accent_color_name_weights",
    balance_flag_key="balanced_accent_color_name_sampling",
    supported=SUPPORTED_TIME_ARTIFACT_COLOR_NAMES,
    namespace="accent_color_name",
  )

  year, month, start_weekday_index, days_in_month = _sample_month(int(instance_seed), params)
  month_weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(int(year), int(month))
  row_count = len(month_weeks)
  weekend_weekday_indices = _resolve_int_support(
    params,
    "weekend_weekday_indices",
    _DEFAULTS.weekend_weekday_indices,
  )
  date_occurrence_support = _resolve_int_support(
    params,
    "date_occurrence_support",
    _DEFAULTS.date_occurrence_support,
  )
  marked_weekend_count_support = _resolve_int_support(
    params,
    "marked_weekend_count_support",
    _DEFAULTS.marked_weekend_count_support,
  )
  marked_weekday_count_support = _resolve_int_support(
    params,
    "marked_weekday_count_support",
    _DEFAULTS.marked_weekday_count_support,
  )
  marked_weekday_distractor_support = _resolve_int_support(
    params,
    "marked_weekday_distractor_support",
    _DEFAULTS.marked_weekday_distractor_support,
  )
  marked_weekend_distractor_support = _resolve_int_support(
    params,
    "marked_weekend_distractor_support",
    _DEFAULTS.marked_weekend_distractor_support,
  )

  marked_dates: Tuple[int, ...] = ()
  evidence_dates: Tuple[int, ...]
  answer_value: int
  query_weekday_index: int | None = None
  query_occurrence: int | None = None
  marked_day_class: str | None = None
  marked_day_class_probabilities: Dict[str, float] = {}

  if str(query_variant) == "date_of_weekday_occurrence":
    feasible_pairs: List[Tuple[int, int, int]] = []
    for weekday_index in range(7):
      dates_for_weekday = [int(day) for week in month_weeks for day_index, day in enumerate(week) if int(day) > 0 and int(day_index) == int(weekday_index)]
      for occurrence in date_occurrence_support:
        if int(occurrence) <= len(dates_for_weekday):
          feasible_pairs.append((int(weekday_index), int(occurrence), int(dates_for_weekday[int(occurrence) - 1])))
    if not feasible_pairs:
      raise ValueError("no feasible weekday-occurrence query exists for the sampled month")
    pair_index = int(
      resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:weekday_occurrence_pair",
      )
      % len(feasible_pairs)
    )
    query_weekday_index, query_occurrence, answer_value = feasible_pairs[int(pair_index)]
    evidence_dates = (int(answer_value),)
  else:
    marked_day_class, marked_day_class_probabilities = _resolve_marked_day_class(
      instance_seed=int(instance_seed),
      params=params,
    )
    marked_dates, evidence_dates, answer_value = _resolve_marked_count_query(
      instance_seed=int(instance_seed),
      params=params,
      days_in_month=int(days_in_month),
      weekend_weekday_indices=tuple(int(value) for value in weekend_weekday_indices),
      year=int(year),
      month=int(month),
      target_weekend=str(marked_day_class) == "weekend",
    )

  return _ResolvedQuery(
    query_variant=str(query_variant),
    marked_day_class=(str(marked_day_class) if marked_day_class is not None else None),
    scene_variant=str(scene_variant),
    style_variant=str(style_variant),
    accent_color_name=str(accent_color_name),
    year=int(year),
    month=int(month),
    month_name=str(month_name(int(month))),
    row_count=int(row_count),
    start_weekday_index=int(start_weekday_index),
    days_in_month=int(days_in_month),
    marked_dates=tuple(int(day) for day in marked_dates),
    evidence_dates=tuple(int(day) for day in evidence_dates),
    answer_value=int(answer_value),
    query_weekday_index=(int(query_weekday_index) if query_weekday_index is not None else None),
    query_occurrence=(int(query_occurrence) if query_occurrence is not None else None),
    weekend_weekday_indices=tuple(int(value) for value in weekend_weekday_indices),
    date_occurrence_support=tuple(int(value) for value in date_occurrence_support),
    marked_weekend_count_support=tuple(int(value) for value in marked_weekend_count_support),
    marked_weekday_count_support=tuple(int(value) for value in marked_weekday_count_support),
    marked_weekday_distractor_support=tuple(int(value) for value in marked_weekday_distractor_support),
    marked_weekend_distractor_support=tuple(int(value) for value in marked_weekend_distractor_support),
    query_variant_probabilities=dict(query_variant_probabilities),
    marked_day_class_probabilities=dict(marked_day_class_probabilities),
    scene_variant_probabilities=dict(scene_variant_probabilities),
    style_variant_probabilities=dict(style_variant_probabilities),
    accent_color_name_probabilities=dict(accent_color_name_probabilities),
  )


class _PagesCalendarMonthViewBase:
  """Reason over one month-view calendar with several numeric query variants."""

  task_id = TASK_ID
  domain = "pages"
  task_group = "calendar"

  def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
    del max_attempts
    query = _resolve_query(int(instance_seed), params=params)
    render_params = resolve_calendar_render_params(
      params,
      render_defaults=_RENDER_DEFAULTS,
      fallback_values=asdict(_DEFAULTS),
      instance_seed=int(instance_seed),
    )
    calendar_theme = build_time_artifact_calendar_theme(
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
    rendered_scene = render_month_calendar_scene(
      image,
      year=int(query.year),
      month=int(query.month),
      marked_dates=tuple(int(day) for day in query.marked_dates),
      scene_variant=str(query.scene_variant),
      render_params=render_params,
      visual_theme=calendar_theme,
    )
    image, post_noise_meta = apply_post_image_noise(
      image,
      instance_seed=int(instance_seed),
      params=params,
      default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    evidence_bboxes = [
      [round(float(value), 3) for value in rendered_scene.date_cell_bboxes_by_day[int(day)]]
      for day in query.evidence_dates
    ]

    answer_hint_key = f"answer_hint_{query.query_variant}"
    evidence_hint_key = f"evidence_hint_{query.query_variant}"
    object_description_key = f"object_description_{query.query_variant}"
    json_example_key = f"json_example_{query.query_variant}"
    json_example_answer_only_key = f"json_example_answer_only_{query.query_variant}"
    prompt_defaults = required_group_defaults(
      _PROMPT_DEFAULTS,
      (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        object_description_key,
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
      "json_output_contract": str(prompt_defaults["json_output_contract"]),
      "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
      "evidence_hint": str(prompt_defaults[evidence_hint_key]),
      "answer_hint": str(prompt_defaults[answer_hint_key]),
      "json_example": str(prompt_defaults[json_example_key]),
      "json_example_answer_only": str(prompt_defaults[json_example_answer_only_key]),
    }
    if str(query.query_variant) == "date_of_weekday_occurrence":
      slots["ordinal"] = str(ordinal_label(int(query.query_occurrence)))
      slots["weekday_name"] = str(weekday_name(int(query.query_weekday_index)))
    if str(query.query_variant) == "count_marked_day_class":
      if query.marked_day_class is None:
        raise ValueError("count_marked_day_class requires marked_day_class")
      slots["marked_day_class"] = str(query.marked_day_class)
      slots["marked_day_class_phrase"] = str(_marked_day_class_phrase(str(query.marked_day_class)))

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

    query_params: Dict[str, Any] = {
      "query_variant": str(query.query_variant),
      "marked_day_class": query.marked_day_class,
      "scene_variant": str(query.scene_variant),
      "style_variant": str(query.style_variant),
      "accent_color_name": str(query.accent_color_name),
      "year": int(query.year),
      "month": int(query.month),
      "month_name": str(query.month_name),
      "days_in_month": int(query.days_in_month),
      "start_weekday_index": int(query.start_weekday_index),
      "row_count": int(query.row_count),
      "weekend_weekday_indices": [int(value) for value in query.weekend_weekday_indices],
      "date_occurrence_support": [int(value) for value in query.date_occurrence_support],
      "marked_weekend_count_support": [int(value) for value in query.marked_weekend_count_support],
      "marked_weekday_count_support": [int(value) for value in query.marked_weekday_count_support],
      "marked_weekday_distractor_support": [int(value) for value in query.marked_weekday_distractor_support],
      "marked_weekend_distractor_support": [int(value) for value in query.marked_weekend_distractor_support],
      "query_variant_probabilities": dict(query.query_variant_probabilities),
      "marked_day_class_probabilities": dict(query.marked_day_class_probabilities),
      "scene_variant_probabilities": dict(query.scene_variant_probabilities),
      "style_variant_probabilities": dict(query.style_variant_probabilities),
      "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
    }
    if query.query_weekday_index is not None:
      query_params["query_weekday_index"] = int(query.query_weekday_index)
      query_params["query_weekday_name"] = str(weekday_name(int(query.query_weekday_index)))
    if query.query_occurrence is not None:
      query_params["query_occurrence"] = int(query.query_occurrence)
      query_params["query_occurrence_label"] = str(ordinal_label(int(query.query_occurrence)))
    trace_payload = {
      "scene_ir": {
        "scene_kind": "pages_month_calendar",
        "entities": [dict(entity) for entity in rendered_scene.entities],
        "relations": {
          "query_variant": str(query.query_variant),
          "marked_day_class": query.marked_day_class,
          "scene_variant": str(query.scene_variant),
          "style_variant": str(query.style_variant),
          "accent_color_name": str(query.accent_color_name),
          "year": int(query.year),
          "month": int(query.month),
          "month_name": str(query.month_name),
          "marked_dates": [int(day) for day in query.marked_dates],
        },
      },
      "query_spec": {
        "query_variant": str(query.query_variant),
        "template_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
        "params": dict(query_params),
      },
      "render_spec": {
        "canvas_width": int(render_params.canvas_width),
        "canvas_height": int(render_params.canvas_height),
        "coord_space": "pixel",
        "scene_variant": str(query.scene_variant),
        "background_style": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
        "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
        "calendar_style": {
          "accent_color_name": str(query.accent_color_name),
          "style_variant": str(query.style_variant),
          "row_count": int(query.row_count),
          "title_text": str(rendered_scene.title_text),
          "resolved_colors_rgb": {
            "panel_fill": [int(value) for value in calendar_theme.panel_fill_rgb],
            "panel_outline": [int(value) for value in calendar_theme.panel_outline_rgb],
            "title_text": [int(value) for value in calendar_theme.title_text_rgb],
            "weekday_fill": [int(value) for value in calendar_theme.weekday_fill_rgb],
            "weekday_text": [int(value) for value in calendar_theme.weekday_text_rgb],
            "grid_line": [int(value) for value in calendar_theme.grid_line_rgb],
            "date_text": [int(value) for value in calendar_theme.date_text_rgb],
            "marker_fill": [int(value) for value in calendar_theme.marker_fill_rgb],
            "marker_outline": [int(value) for value in calendar_theme.marker_outline_rgb],
          },
          "marker_kind": str(calendar_theme.marker_kind),
        },
      },
      "render_map": {
        "image_id": "img0",
        "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
        "calendar_title_text": str(rendered_scene.title_text),
        "date_cells_by_day": {
          str(day): [round(float(value), 3) for value in bbox]
          for day, bbox in rendered_scene.date_cell_bboxes_by_day.items()
        },
        "evidence_dates": [int(day) for day in query.evidence_dates],
        "marked_dates": [int(day) for day in query.marked_dates],
      },
      "execution_trace": {
        "query_variant": str(query.query_variant),
        "marked_day_class": query.marked_day_class,
        "scene_variant": str(query.scene_variant),
        "style_variant": str(query.style_variant),
        "accent_color_name": str(query.accent_color_name),
        "year": int(query.year),
        "month": int(query.month),
        "month_name": str(query.month_name),
        "days_in_month": int(query.days_in_month),
        "start_weekday_index": int(query.start_weekday_index),
        "row_count": int(query.row_count),
        "marked_dates": [int(day) for day in query.marked_dates],
        "evidence_dates": [int(day) for day in query.evidence_dates],
        "answer_value": int(query.answer_value),
        "weekend_weekday_indices": [int(value) for value in query.weekend_weekday_indices],
        "query_weekday_index": (int(query.query_weekday_index) if query.query_weekday_index is not None else None),
        "query_occurrence": (int(query.query_occurrence) if query.query_occurrence is not None else None),
        "query_variant_probabilities": dict(query.query_variant_probabilities),
        "marked_day_class_probabilities": dict(query.marked_day_class_probabilities),
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

    marked_count = len(query.marked_dates)
    complexity = build_time_artifact_complexity(
      weights=_COMPLEXITY_WEIGHTS,
      components={
        "calendar_lookup": min(
          1.0,
          float(_CALENDAR_LOOKUP_BASE_BY_VARIANT[str(query.query_variant)])
          + (
            0.18
            * float(
              normalize_int_with_bounds(
                int(query.query_occurrence or marked_count or 1),
                [1, 20],
              )
            )
          ),
        ),
        "visual_scan": min(
          1.0,
          float(_VISUAL_SCAN_BASE_BY_SCENE[str(query.scene_variant)])
          + float(_VISUAL_SCAN_STYLE_BONUS[str(query.style_variant)])
          + (0.18 * float(normalize_int_with_bounds(int(query.row_count), [4, 6])))
          + (0.10 * float(normalize_int_with_bounds(int(marked_count), [0, 8]))),
        ),
        "ambiguity": min(
          1.0,
          (0.18 * float(normalize_int_with_bounds(int(query.row_count), [4, 6])))
          + (0.28 * float(normalize_int_with_bounds(int(marked_count), [0, 8])))
          + (
            0.20
            * float(
              normalize_int_with_bounds(
                int(query.query_occurrence or marked_count or 1),
                [1, 20],
              )
            )
          )
          + 0.08,
        ),
        "clutter": min(
          1.0,
          float(_CLUTTER_BASE_BY_SCENE[str(query.scene_variant)])
          + float(_CLUTTER_STYLE_BONUS[str(query.style_variant)])
          + (0.16 * float(normalize_int_with_bounds(int(marked_count), [0, 8]))),
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


def _marked_day_class_query_id(output: TaskOutput) -> str:
  """Return the diagnostic query id for one marked-day calendar output."""

  execution = output.trace_payload.get("execution_trace", {}) if isinstance(output.trace_payload, Mapping) else {}
  marked_day_class = str(execution.get("marked_day_class", "")).strip()
  if marked_day_class:
    return f"count_marked_{marked_day_class}_days"
  return "count_marked_day_class"


@register_task
class PagesCalendarWeekdayOccurrenceDateTask(_PagesCalendarMonthViewBase):
  """Find the date of an nth weekday in one month-view calendar."""

  task_id = WEEKDAY_OCCURRENCE_TASK_ID
  fixed_query_variant = "date_of_weekday_occurrence"

  def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
    output = super().generate(
      int(instance_seed),
      params=force_time_artifact_query_params(
        params,
        query_variant="date_of_weekday_occurrence",
      ),
      max_attempts=int(max_attempts),
    )
    return rewrite_time_artifact_query_output(
      output,
      query_id="date_of_weekday_occurrence",
      scene_id=PUBLIC_SCENE_ID,
    )


@register_task
class PagesCalendarMarkedDayClassCountTask(_PagesCalendarMonthViewBase):
  """Count marked dates that fall in one requested weekday/weekend class."""

  task_id = MARKED_DAY_CLASS_TASK_ID
  fixed_query_variant = "count_marked_day_class"

  def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
    generation_params = dict(params)
    fixed_params: Dict[str, Any] = {}
    explicit_variant = generation_params.get("query_variant")
    if explicit_variant is not None and str(explicit_variant) in _SOURCE_MARKED_DAY_CLASS_BY_VARIANT:
      fixed_params["marked_day_class"] = str(_SOURCE_MARKED_DAY_CLASS_BY_VARIANT[str(explicit_variant)])
      generation_params.pop("query_variant", None)
    output = super().generate(
      int(instance_seed),
      params=force_time_artifact_query_params(
        generation_params,
        query_variant="count_marked_day_class",
        fixed_params=fixed_params,
      ),
      max_attempts=int(max_attempts),
    )
    return rewrite_time_artifact_query_output(
      output,
      query_id=_marked_day_class_query_id(output),
      scene_id=PUBLIC_SCENE_ID,
    )


__all__ = [
  "PagesCalendarWeekdayOccurrenceDateTask",
  "PagesCalendarMarkedDayClassCountTask",
]

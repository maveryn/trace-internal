"""Shared rendering and notation helpers for symbolic music-staff symbolic tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from ..shared.drawing import draw_centered_text, draw_rounded_rect
from ..shared.scene_style import SymbolicSceneStyle
from ..shared.unit_size_jitter import resolve_symbolic_unit_size_scale, scale_symbolic_px


LETTERS: Tuple[str, ...] = ("C", "D", "E", "F", "G", "A", "B")
NATURAL_SEMITONES: Dict[str, int] = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}
ACCIDENTAL_TEXT: Dict[int, str] = {-1: "b", 0: "", 1: "#"}
DEGREE_NAMES: Tuple[str, ...] = (
    "tonic",
    "supertonic",
    "mediant",
    "subdominant",
    "dominant",
    "submediant",
    "leading tone",
)
MAJOR_SCALE_STEPS: Tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)


@dataclass(frozen=True)
class Pitch:
    letter: str
    octave: int
    accidental: int = 0


@dataclass(frozen=True)
class StaffNote:
    item_id: str
    staff_index: int
    slot: float
    pitch: Pitch
    duration_units: int = 2
    filled: bool = True
    accidental_visible: bool = False
    marker: str = ""
    dotted: bool = False
    stem_up: bool = True


@dataclass(frozen=True)
class StaffChord:
    item_id: str
    staff_index: int
    slot: float
    pitches: Tuple[Pitch, ...]
    marker: str = ""
    accidental_visible: bool = False


@dataclass(frozen=True)
class StaffText:
    item_id: str
    staff_index: int
    slot: float
    text: str
    y_offset_steps: float = -4.5
    bold: bool = True


@dataclass(frozen=True)
class StaffBarline:
    item_id: str
    staff_index: int
    slot: float


@dataclass(frozen=True)
class StaffRange:
    item_id: str
    staff_index: int
    start_slot: float
    end_slot: float
    label: str = ""


@dataclass(frozen=True)
class StaffSymbol:
    item_id: str
    staff_index: int
    slot: float
    pitch: Pitch
    symbol: str


@dataclass(frozen=True)
class StaffSystem:
    clef: str
    slot_count: int
    key_signature: str = ""
    key_signature_id: str = ""
    time_signature: str = ""
    time_signature_id: str = ""
    subtitle: str = ""
    notes: Tuple[StaffNote, ...] = ()
    chords: Tuple[StaffChord, ...] = ()
    texts: Tuple[StaffText, ...] = ()
    barlines: Tuple[StaffBarline, ...] = ()
    ranges: Tuple[StaffRange, ...] = ()
    symbols: Tuple[StaffSymbol, ...] = ()


@dataclass(frozen=True)
class OptionCard:
    item_id: str
    label: str
    text: str = ""
    duration_units: int | None = None
    is_correct: bool = False


@dataclass(frozen=True)
class MusicSceneSpec:
    title: str
    systems: Tuple[StaffSystem, ...]
    option_cards: Tuple[OptionCard, ...] = ()
    footer_text: str = ""


@dataclass(frozen=True)
class MusicRenderParams:
    canvas_width: int
    canvas_height: int
    panel_padding_px: int
    panel_corner_radius_px: int
    panel_border_width_px: int
    staff_gap_px: int
    staff_width_px: int
    staff_spacing_px: int
    slot_gap_px: int
    title_font_size_px: int
    label_font_size_px: int
    small_font_size_px: int
    notehead_width_px: int
    notehead_height_px: int
    stem_height_px: int
    option_card_width_px: int
    option_card_height_px: int
    option_gap_px: int
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class RenderedMusicScene:
    image: Image.Image
    scene_bbox_px: Tuple[int, int, int, int]
    item_bboxes: Dict[str, Tuple[int, int, int, int]]
    entities: Tuple[Dict[str, Any], ...]
    layout_jitter: Dict[str, Any]
    style_metadata: Dict[str, Any]


def pitch_diatonic_index(pitch: Pitch) -> int:
    return int(pitch.octave) * 7 + LETTERS.index(str(pitch.letter))


def pitch_from_diatonic_index(index: int, accidental: int = 0) -> Pitch:
    idx = int(index)
    octave = idx // 7
    letter = LETTERS[idx % 7]
    return Pitch(letter=str(letter), octave=int(octave), accidental=int(accidental))


def pitch_from_staff_step(clef: str, step: int, accidental: int = 0) -> Pitch:
    return pitch_from_diatonic_index(_staff_reference_index(str(clef)) + int(step), accidental=int(accidental))


def pitch_midi(pitch: Pitch) -> int:
    return (int(pitch.octave) + 1) * 12 + int(NATURAL_SEMITONES[str(pitch.letter)]) + int(pitch.accidental)


def format_pitch(pitch: Pitch, *, include_octave: bool = False) -> str:
    accidental = ACCIDENTAL_TEXT.get(int(pitch.accidental), "")
    text = f"{pitch.letter}{accidental}"
    if include_octave:
        text = f"{text}{int(pitch.octave)}"
    return text


def format_key_signature(accidentals: Sequence[str]) -> str:
    return " ".join(str(value) for value in accidentals)


def _staff_reference_index(clef: str) -> int:
    if str(clef) == "bass":
        return pitch_diatonic_index(Pitch("G", 2, 0))
    return pitch_diatonic_index(Pitch("E", 4, 0))


def staff_step_for_pitch(pitch: Pitch, clef: str) -> int:
    return int(pitch_diatonic_index(pitch) - _staff_reference_index(str(clef)))


def major_scale_pitch(root: Pitch, degree_1based: int) -> Pitch:
    degree = int(degree_1based)
    root_index = pitch_diatonic_index(root)
    target_index = root_index + degree - 1
    natural = pitch_from_diatonic_index(target_index, accidental=0)
    wanted = (pitch_midi(root) + MAJOR_SCALE_STEPS[degree - 1]) % 12
    natural_pc = pitch_midi(natural) % 12
    diff = (wanted - natural_pc) % 12
    accidental = diff if diff <= 6 else diff - 12
    if accidental not in (-1, 0, 1):
        accidental = 0
    return Pitch(str(natural.letter), int(natural.octave), int(accidental))


def interval_name(lower: Pitch, upper: Pitch) -> str:
    low = lower if pitch_midi(lower) <= pitch_midi(upper) else upper
    high = upper if pitch_midi(lower) <= pitch_midi(upper) else lower
    number = abs(pitch_diatonic_index(high) - pitch_diatonic_index(low)) + 1
    simple_number = ((number - 1) % 7) + 1
    octaves = (number - 1) // 7
    semitones = abs(pitch_midi(high) - pitch_midi(low))
    simple_semitones = semitones - (12 * octaves)
    if simple_number in (1, 4, 5):
        perfect_base = {1: 0, 4: 5, 5: 7}[simple_number]
        delta = int(simple_semitones - perfect_base)
        quality = "perfect" if delta == 0 else "augmented" if delta == 1 else "diminished"
    else:
        major_base = {2: 2, 3: 4, 6: 9, 7: 11}[simple_number]
        delta = int(simple_semitones - major_base)
        if delta == 0:
            quality = "major"
        elif delta == -1:
            quality = "minor"
        elif delta == 1:
            quality = "augmented"
        else:
            quality = "diminished"
    ordinal = {
        1: "unison",
        2: "2nd",
        3: "3rd",
        4: "4th",
        5: "5th",
        6: "6th",
        7: "7th",
        8: "octave",
    }.get(number, f"{number}th")
    return f"{quality} {ordinal}"


def build_interval_pitch(root: Pitch, number: int, quality: str) -> Pitch | None:
    target_index = pitch_diatonic_index(root) + int(number) - 1
    natural = pitch_from_diatonic_index(target_index, accidental=0)
    simple_number = ((int(number) - 1) % 7) + 1
    octave_offset = (int(number) - 1) // 7
    if simple_number in (1, 4, 5):
        base = {1: 0, 4: 5, 5: 7}[simple_number] + 12 * octave_offset
        delta = {"diminished": -1, "perfect": 0, "augmented": 1}.get(str(quality))
    else:
        base = {2: 2, 3: 4, 6: 9, 7: 11}[simple_number] + 12 * octave_offset
        delta = {"diminished": -2, "minor": -1, "major": 0, "augmented": 1}.get(str(quality))
    if delta is None:
        return None
    wanted = pitch_midi(root) + int(base) + int(delta)
    accidental = int(wanted - pitch_midi(natural))
    if accidental not in (-1, 0, 1):
        return None
    return Pitch(str(natural.letter), int(natural.octave), int(accidental))


def resolve_music_render_params(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    instance_seed: int,
) -> MusicRenderParams:
    # Preserve legacy puzzle seed namespaces so the domain split does not
    # change music-staff scale or layout for existing seeds.
    unit_scale, unit_meta = resolve_symbolic_unit_size_scale(
        params,
        defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.notation.unit_size",
    )
    return MusicRenderParams(
        canvas_width=int(group_default(defaults, "canvas_width", 1180)),
        canvas_height=int(group_default(defaults, "canvas_height", 820)),
        panel_padding_px=scale_symbolic_px(group_default(defaults, "panel_padding_px", 34), unit_scale, min_px=18),
        panel_corner_radius_px=scale_symbolic_px(group_default(defaults, "panel_corner_radius_px", 18), unit_scale, min_px=8),
        panel_border_width_px=scale_symbolic_px(group_default(defaults, "panel_border_width_px", 2), unit_scale, min_px=1),
        staff_gap_px=scale_symbolic_px(group_default(defaults, "staff_gap_px", 15), unit_scale, min_px=10),
        staff_width_px=scale_symbolic_px(group_default(defaults, "staff_width_px", 760), unit_scale, min_px=520),
        staff_spacing_px=scale_symbolic_px(group_default(defaults, "staff_spacing_px", 142), unit_scale, min_px=98),
        slot_gap_px=scale_symbolic_px(group_default(defaults, "slot_gap_px", 52), unit_scale, min_px=34),
        title_font_size_px=scale_symbolic_px(group_default(defaults, "title_font_size_px", 25), unit_scale, min_px=16),
        label_font_size_px=scale_symbolic_px(group_default(defaults, "label_font_size_px", 21), unit_scale, min_px=13),
        small_font_size_px=scale_symbolic_px(group_default(defaults, "small_font_size_px", 16), unit_scale, min_px=11),
        notehead_width_px=scale_symbolic_px(group_default(defaults, "notehead_width_px", 21), unit_scale, min_px=13),
        notehead_height_px=scale_symbolic_px(group_default(defaults, "notehead_height_px", 14), unit_scale, min_px=9),
        stem_height_px=scale_symbolic_px(group_default(defaults, "stem_height_px", 48), unit_scale, min_px=30),
        option_card_width_px=scale_symbolic_px(group_default(defaults, "option_card_width_px", 254), unit_scale, min_px=170),
        option_card_height_px=scale_symbolic_px(group_default(defaults, "option_card_height_px", 70), unit_scale, min_px=48),
        option_gap_px=scale_symbolic_px(group_default(defaults, "option_gap_px", 12), unit_scale, min_px=8),
        unit_size_jitter=dict(unit_meta),
    )


def _bbox_union(bboxes: Sequence[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
    if not bboxes:
        return (0, 0, 0, 0)
    return (
        int(min(b[0] for b in bboxes)),
        int(min(b[1] for b in bboxes)),
        int(max(b[2] for b in bboxes)),
        int(max(b[3] for b in bboxes)),
    )


def _staff_y_for_pitch(staff_top: int, staff_gap: int, pitch: Pitch, clef: str) -> int:
    bottom_y = int(staff_top) + 4 * int(staff_gap)
    return int(round(bottom_y - staff_step_for_pitch(pitch, str(clef)) * (int(staff_gap) / 2.0)))


def _slot_x(content_x0: int, slot_gap: int, slot: float) -> int:
    return int(round(int(content_x0) + float(slot) * int(slot_gap)))


def _draw_text_bbox(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[int, int],
    text: str,
    *,
    font,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int],
    stroke_width: int = 1,
) -> Tuple[int, int, int, int]:
    x, y = int(xy[0]), int(xy[1])
    draw_text_traced(draw,(x, y), str(text), fill=fill, font=font, stroke_width=int(stroke_width), stroke_fill=stroke_fill, role="readout", required=False)
    bbox = draw.textbbox((x, y), str(text), font=font, stroke_width=int(stroke_width))
    return (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))


def _draw_note(
    draw: ImageDraw.ImageDraw,
    *,
    note: StaffNote,
    staff_top: int,
    content_x0: int,
    clef: str,
    render_params: MusicRenderParams,
    text_rgb: Tuple[int, int, int],
    stroke_rgb: Tuple[int, int, int],
    mark_rgb: Tuple[int, int, int],
    font,
    small_font,
) -> Tuple[int, int, int, int]:
    x = _slot_x(content_x0, int(render_params.slot_gap_px), float(note.slot))
    y = _staff_y_for_pitch(staff_top, int(render_params.staff_gap_px), note.pitch, str(clef))
    hw = int(render_params.notehead_width_px) // 2
    hh = int(render_params.notehead_height_px) // 2
    bbox = (x - hw, y - hh, x + hw, y + hh)
    fill = text_rgb if bool(note.filled) else stroke_rgb
    draw.ellipse(bbox, fill=fill, outline=text_rgb, width=2)
    stem_x = bbox[2] - 1 if bool(note.stem_up) else bbox[0] + 1
    if bool(note.stem_up):
        draw.line((stem_x, y, stem_x, y - int(render_params.stem_height_px)), fill=text_rgb, width=2)
        stem_bbox = (stem_x - 2, y - int(render_params.stem_height_px), stem_x + 2, y)
    else:
        draw.line((stem_x, y, stem_x, y + int(render_params.stem_height_px)), fill=text_rgb, width=2)
        stem_bbox = (stem_x - 2, y, stem_x + 2, y + int(render_params.stem_height_px))
    parts = [bbox, stem_bbox]
    if bool(note.accidental_visible) and int(note.pitch.accidental) != 0:
        acc_bbox = _draw_text_bbox(
            draw,
            (bbox[0] - 24, y - int(render_params.label_font_size_px) // 2),
            ACCIDENTAL_TEXT[int(note.pitch.accidental)],
            font=font,
            fill=text_rgb,
            stroke_fill=stroke_rgb,
        )
        parts.append(acc_bbox)
    if bool(note.dotted):
        dot_bbox = (bbox[2] + 8, y - 3, bbox[2] + 14, y + 3)
        draw.ellipse(dot_bbox, fill=text_rgb)
        parts.append(dot_bbox)
    if str(note.marker):
        marker_bbox = _draw_text_bbox(
            draw,
            (x - 8, y - int(render_params.staff_gap_px) * 4),
            str(note.marker),
            font=font,
            fill=mark_rgb,
            stroke_fill=stroke_rgb,
            stroke_width=1,
        )
        parts.append(marker_bbox)
    step = staff_step_for_pitch(note.pitch, str(clef))
    if step < 0 or step > 8:
        for ledger_step in range(min(0, step), max(8, step) + 1):
            if ledger_step % 2 == 0 and (ledger_step < 0 or ledger_step > 8):
                ly = int(round(staff_top + 4 * int(render_params.staff_gap_px) - ledger_step * (int(render_params.staff_gap_px) / 2.0)))
                draw.line((x - hw - 8, ly, x + hw + 8, ly), fill=text_rgb, width=1)
                parts.append((x - hw - 8, ly - 1, x + hw + 8, ly + 1))
    return _bbox_union(parts)


def _draw_chord(
    draw: ImageDraw.ImageDraw,
    *,
    chord: StaffChord,
    staff_top: int,
    content_x0: int,
    clef: str,
    render_params: MusicRenderParams,
    text_rgb: Tuple[int, int, int],
    stroke_rgb: Tuple[int, int, int],
    mark_rgb: Tuple[int, int, int],
    font,
) -> Tuple[int, int, int, int]:
    bboxes = []
    x = _slot_x(content_x0, int(render_params.slot_gap_px), float(chord.slot))
    sorted_pitches = tuple(sorted(chord.pitches, key=pitch_midi))
    for index, pitch in enumerate(sorted_pitches):
        y = _staff_y_for_pitch(staff_top, int(render_params.staff_gap_px), pitch, str(clef))
        offset = -5 if index % 2 else 0
        hw = int(render_params.notehead_width_px) // 2
        hh = int(render_params.notehead_height_px) // 2
        bbox = (x - hw + offset, y - hh, x + hw + offset, y + hh)
        draw.ellipse(bbox, fill=text_rgb, outline=text_rgb, width=2)
        bboxes.append(bbox)
        if bool(chord.accidental_visible) and int(pitch.accidental) != 0:
            bboxes.append(
                _draw_text_bbox(
                    draw,
                    (bbox[0] - 24, y - int(render_params.label_font_size_px) // 2),
                    ACCIDENTAL_TEXT[int(pitch.accidental)],
                    font=font,
                    fill=text_rgb,
                    stroke_fill=stroke_rgb,
                )
            )
    if bboxes:
        union = _bbox_union(bboxes)
        draw.line((union[2] + 2, union[3], union[2] + 2, union[1] - int(render_params.stem_height_px) // 2), fill=text_rgb, width=2)
        bboxes.append((union[2], union[1] - int(render_params.stem_height_px) // 2, union[2] + 4, union[3]))
    if str(chord.marker):
        bboxes.append(
            _draw_text_bbox(
                draw,
                (x - 8, staff_top - int(render_params.staff_gap_px) * 3),
                str(chord.marker),
                font=font,
                fill=mark_rgb,
                stroke_fill=stroke_rgb,
                stroke_width=1,
            )
        )
    return _bbox_union(bboxes)


def _draw_duration_glyph(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[int, int],
    duration_units: int,
    render_params: MusicRenderParams,
    text_rgb: Tuple[int, int, int],
    stroke_rgb: Tuple[int, int, int],
    font,
    stem_height_px: int | None = None,
) -> Tuple[int, int, int, int]:
    x, y = int(center[0]), int(center[1])
    units = int(duration_units)
    filled = units <= 3
    stem = units < 8
    stem_height = int(stem_height_px) if stem_height_px is not None else int(render_params.stem_height_px)
    hw = int(render_params.notehead_width_px) // 2
    hh = int(render_params.notehead_height_px) // 2
    bbox = (x - hw, y - hh, x + hw, y + hh)
    draw.ellipse(bbox, fill=text_rgb if filled else stroke_rgb, outline=text_rgb, width=2)
    parts = [bbox]
    if stem:
        draw.line((bbox[2] - 1, y, bbox[2] - 1, y - stem_height), fill=text_rgb, width=2)
        parts.append((bbox[2] - 3, y - stem_height, bbox[2] + 2, y))
    if units in (3, 6):
        dot_bbox = (bbox[2] + 8, y - 3, bbox[2] + 14, y + 3)
        draw.ellipse(dot_bbox, fill=text_rgb)
        parts.append(dot_bbox)
    if units == 1:
        flag_bbox = (bbox[2] - 1, y - stem_height, bbox[2] + 20, y - stem_height + 18)
        draw.arc(flag_bbox, start=260, end=70, fill=text_rgb, width=2)
        parts.append(flag_bbox)
    if units not in (1, 2, 3, 4, 6, 8):
        parts.append(
            _draw_text_bbox(
                draw,
                (x + 18, y - 10),
                f"{units}u",
                font=font,
                fill=text_rgb,
                stroke_fill=stroke_rgb,
            )
        )
    return _bbox_union(parts)


def render_music_scene(
    image: Image.Image,
    *,
    spec: MusicSceneSpec,
    render_params: MusicRenderParams,
    scene_style: SymbolicSceneStyle,
    instance_seed: int,
) -> RenderedMusicScene:
    draw = ImageDraw.Draw(image)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    small_font = load_font(int(render_params.small_font_size_px), bold=False)
    text_rgb = tuple(int(value) for value in scene_style.text_rgb)
    stroke_rgb = tuple(int(value) for value in scene_style.text_stroke_rgb)
    line_rgb = tuple(int(value) for value in scene_style.grid_rgb)
    panel_fill = tuple(int(value) for value in scene_style.panel_fill_rgb)
    option_fill = tuple(int(value) for value in scene_style.option_fill_rgb)
    option_border = tuple(int(value) for value in scene_style.mark_rgb)
    mark_rgb = tuple(int(value) for value in scene_style.mark_rgb)

    staff_count = max(1, len(spec.systems))
    option_count = len(spec.option_cards)
    content_width = int(render_params.staff_width_px) + 190
    if option_count:
        content_width += int(render_params.option_card_width_px) + 34
    staff_content_height = 98 + (staff_count - 1) * int(render_params.staff_spacing_px) + 5 * int(render_params.staff_gap_px) + 82
    option_stack_height = (
        option_count * int(render_params.option_card_height_px)
        + max(0, option_count - 1) * int(render_params.option_gap_px)
    )
    content_height = max(staff_content_height, 78 + option_stack_height if option_count else 0)
    panel_width = min(int(render_params.canvas_width) - 48, content_width + 2 * int(render_params.panel_padding_px))
    panel_height = min(int(render_params.canvas_height) - 48, content_height + 2 * int(render_params.panel_padding_px))
    max_x0 = max(24, int(render_params.canvas_width) - panel_width - 24)
    max_y0 = max(24, int(render_params.canvas_height) - panel_height - 24)
    rng = spawn_rng(int(instance_seed), "puzzles.notation.layout")
    panel_x0 = int(24 + (rng.randrange(max(1, max_x0 - 23)) if max_x0 > 24 else 0))
    panel_y0 = int(24 + (rng.randrange(max(1, max_y0 - 23)) if max_y0 > 24 else 0))
    panel_x1 = int(panel_x0 + panel_width)
    panel_y1 = int(panel_y0 + panel_height)
    draw_rounded_rect(
        draw,
        (panel_x0, panel_y0, panel_x1, panel_y1),
        radius=int(render_params.panel_corner_radius_px),
        fill=panel_fill,
        outline=line_rgb,
        width=max(1, int(render_params.panel_border_width_px)),
    )
    title_bbox = _draw_text_bbox(
        draw,
        (panel_x0 + int(render_params.panel_padding_px), panel_y0 + 18),
        str(spec.title),
        font=title_font,
        fill=text_rgb,
        stroke_fill=stroke_rgb,
    )
    item_bboxes: Dict[str, Tuple[int, int, int, int]] = {"scene_title": title_bbox}
    entities: list[Dict[str, Any]] = [
        {
            "entity_id": "music_staff_panel",
            "entity_type": "music_staff_panel",
            "bbox_px": [panel_x0, panel_y0, panel_x1, panel_y1],
        }
    ]

    staff_x0 = panel_x0 + int(render_params.panel_padding_px)
    first_staff_top = panel_y0 + 86
    content_x0_by_staff: Dict[int, int] = {}
    staff_top_by_index: Dict[int, int] = {}
    if option_count:
        option_x0 = panel_x1 - int(render_params.panel_padding_px) - int(render_params.option_card_width_px)
        staff_draw_width = max(320, min(int(render_params.staff_width_px), int(option_x0 - staff_x0 - 34)))
    else:
        option_x0 = staff_x0 + int(render_params.staff_width_px) + 122
        staff_draw_width = int(render_params.staff_width_px)
    for staff_index, system in enumerate(spec.systems):
        staff_top = int(first_staff_top + staff_index * int(render_params.staff_spacing_px))
        staff_top_by_index[staff_index] = staff_top
        staff_x1 = int(staff_x0 + staff_draw_width)
        for line_index in range(5):
            y = int(staff_top + line_index * int(render_params.staff_gap_px))
            draw.line((staff_x0, y, staff_x1, y), fill=line_rgb, width=2)
        clef_text = "F" if str(system.clef) == "bass" else "G"
        clef_bbox = _draw_text_bbox(
            draw,
            (staff_x0 + 10, staff_top - int(render_params.staff_gap_px)),
            clef_text,
            font=load_font(max(28, int(render_params.label_font_size_px) + 12), bold=True),
            fill=text_rgb,
            stroke_fill=stroke_rgb,
        )
        item_bboxes[f"staff_{staff_index}_clef"] = clef_bbox
        cursor_x = staff_x0 + 55
        if str(system.key_signature):
            key_bbox = _draw_text_bbox(
                draw,
                (cursor_x, staff_top + int(render_params.staff_gap_px)),
                str(system.key_signature),
                font=label_font,
                fill=text_rgb,
                stroke_fill=stroke_rgb,
            )
            if str(system.key_signature_id):
                item_bboxes[str(system.key_signature_id)] = key_bbox
            entities.append({"entity_id": str(system.key_signature_id or f"staff_{staff_index}_key_signature"), "entity_type": "music_key_signature", "bbox_px": list(key_bbox), "text": str(system.key_signature)})
            cursor_x = key_bbox[2] + 18
        if str(system.time_signature):
            time_bbox = _draw_text_bbox(
                draw,
                (cursor_x, staff_top + int(render_params.staff_gap_px) // 2),
                str(system.time_signature),
                font=label_font,
                fill=text_rgb,
                stroke_fill=stroke_rgb,
            )
            if str(system.time_signature_id):
                item_bboxes[str(system.time_signature_id)] = time_bbox
            entities.append({"entity_id": str(system.time_signature_id or f"staff_{staff_index}_time_signature"), "entity_type": "music_time_signature", "bbox_px": list(time_bbox), "text": str(system.time_signature)})
            cursor_x = time_bbox[2] + 26
        content_x0 = max(staff_x0 + 145, cursor_x + 12)
        content_x0_by_staff[staff_index] = int(content_x0)
        if str(system.subtitle):
            sub_bbox = _draw_text_bbox(
                draw,
                (staff_x0, staff_top - int(render_params.staff_gap_px) * 3),
                str(system.subtitle),
                font=small_font,
                fill=text_rgb,
                stroke_fill=stroke_rgb,
            )
            item_bboxes[f"staff_{staff_index}_subtitle"] = sub_bbox
        for barline in system.barlines:
            x = _slot_x(content_x0, int(render_params.slot_gap_px), float(barline.slot))
            bbox = (x - 2, staff_top, x + 2, staff_top + 4 * int(render_params.staff_gap_px))
            draw.line((x, bbox[1], x, bbox[3]), fill=line_rgb, width=2)
            item_bboxes[str(barline.item_id)] = bbox
            entities.append({"entity_id": str(barline.item_id), "entity_type": "music_barline", "bbox_px": list(bbox), "slot": float(barline.slot), "staff_index": int(staff_index)})
        for staff_range in system.ranges:
            x0 = _slot_x(content_x0, int(render_params.slot_gap_px), float(staff_range.start_slot))
            x1 = _slot_x(content_x0, int(render_params.slot_gap_px), float(staff_range.end_slot))
            bbox = (min(x0, x1), staff_top - 18, max(x0, x1), staff_top + 4 * int(render_params.staff_gap_px) + 18)
            item_bboxes[str(staff_range.item_id)] = bbox
            if str(staff_range.label):
                label_bbox = _draw_text_bbox(
                    draw,
                    (bbox[0] + 4, bbox[1] - 18),
                    str(staff_range.label),
                    font=small_font,
                    fill=mark_rgb,
                    stroke_fill=stroke_rgb,
                )
                item_bboxes[f"{staff_range.item_id}_label"] = label_bbox
            entities.append({"entity_id": str(staff_range.item_id), "entity_type": "music_staff_range", "bbox_px": list(bbox), "label": str(staff_range.label)})
        for text_item in system.texts:
            x = _slot_x(content_x0, int(render_params.slot_gap_px), float(text_item.slot))
            y = int(staff_top + float(text_item.y_offset_steps) * int(render_params.staff_gap_px))
            bbox = _draw_text_bbox(
                draw,
                (x, y),
                str(text_item.text),
                font=label_font if bool(text_item.bold) else small_font,
                fill=mark_rgb if bool(text_item.bold) else text_rgb,
                stroke_fill=stroke_rgb,
            )
            item_bboxes[str(text_item.item_id)] = bbox
            entities.append({"entity_id": str(text_item.item_id), "entity_type": "music_staff_text", "bbox_px": list(bbox), "text": str(text_item.text)})
        for chord in system.chords:
            bbox = _draw_chord(
                draw,
                chord=chord,
                staff_top=staff_top,
                content_x0=content_x0,
                clef=str(system.clef),
                render_params=render_params,
                text_rgb=text_rgb,
                stroke_rgb=stroke_rgb,
                mark_rgb=mark_rgb,
                font=label_font,
            )
            item_bboxes[str(chord.item_id)] = bbox
            entities.append({"entity_id": str(chord.item_id), "entity_type": "music_chord", "bbox_px": list(bbox), "pitches": [format_pitch(p, include_octave=True) for p in chord.pitches], "staff_index": int(staff_index)})
        for note in system.notes:
            bbox = _draw_note(
                draw,
                note=note,
                staff_top=staff_top,
                content_x0=content_x0,
                clef=str(system.clef),
                render_params=render_params,
                text_rgb=text_rgb,
                stroke_rgb=stroke_rgb,
                mark_rgb=mark_rgb,
                font=label_font,
                small_font=small_font,
            )
            item_bboxes[str(note.item_id)] = bbox
            entities.append({"entity_id": str(note.item_id), "entity_type": "music_note", "bbox_px": list(bbox), "pitch": format_pitch(note.pitch, include_octave=True), "duration_units": int(note.duration_units), "staff_index": int(staff_index)})
        for symbol in system.symbols:
            x = _slot_x(content_x0, int(render_params.slot_gap_px), float(symbol.slot))
            y = _staff_y_for_pitch(staff_top, int(render_params.staff_gap_px), symbol.pitch, str(system.clef))
            if str(symbol.symbol) == "staccato":
                bbox = (x - 4, y - int(render_params.staff_gap_px) * 3, x + 4, y - int(render_params.staff_gap_px) * 3 + 8)
                draw.ellipse(bbox, fill=mark_rgb)
            elif str(symbol.symbol) == "tenuto":
                bbox = (x - 15, y - int(render_params.staff_gap_px) * 3, x + 15, y - int(render_params.staff_gap_px) * 3 + 3)
                draw.rectangle(bbox, fill=mark_rgb)
            elif str(symbol.symbol) == "accent":
                bbox = _draw_text_bbox(draw, (x - 10, y - int(render_params.staff_gap_px) * 4), ">", font=label_font, fill=mark_rgb, stroke_fill=stroke_rgb)
            else:
                bbox = _draw_text_bbox(draw, (x - 18, y - int(render_params.staff_gap_px) * 4), "hold", font=small_font, fill=mark_rgb, stroke_fill=stroke_rgb)
            item_bboxes[str(symbol.item_id)] = bbox
            entities.append({"entity_id": str(symbol.item_id), "entity_type": "music_articulation_symbol", "bbox_px": list(bbox), "symbol": str(symbol.symbol)})

    for index, option in enumerate(spec.option_cards):
        x0 = int(option_x0)
        y0 = int(first_staff_top + index * (int(render_params.option_card_height_px) + int(render_params.option_gap_px)) - 8)
        bbox = (x0, y0, x0 + int(render_params.option_card_width_px), y0 + int(render_params.option_card_height_px))
        draw.rounded_rectangle(bbox, radius=10, fill=option_fill, outline=option_border, width=2)
        label_bbox = _draw_text_bbox(draw, (bbox[0] + 12, bbox[1] + 10), f"{option.label}.", font=label_font, fill=text_rgb, stroke_fill=stroke_rgb)
        content_parts = [bbox, label_bbox]
        if option.duration_units is not None:
            glyph_bbox = _draw_duration_glyph(
                draw,
                center=(bbox[0] + 94, bbox[1] + int(render_params.option_card_height_px) // 2 + 7),
                duration_units=int(option.duration_units),
                render_params=render_params,
                text_rgb=text_rgb,
                stroke_rgb=stroke_rgb,
                font=small_font,
                stem_height_px=max(18, int(render_params.option_card_height_px) // 2 - 4),
            )
            content_parts.append(glyph_bbox)
            if str(option.text):
                option_text = str(option.text)
                text_x = bbox[0] + 132
                text_font_size = int(render_params.small_font_size_px)
                text_font = small_font
                max_text_width = max(48, int(bbox[2] - text_x - 16))
                while text_font_size > 8 and draw.textbbox((0, 0), option_text, font=text_font)[2] > max_text_width:
                    text_font_size -= 1
                    text_font = load_font(text_font_size, bold=False)
                content_parts.append(_draw_text_bbox(draw, (text_x, bbox[1] + 22), option_text, font=text_font, fill=text_rgb, stroke_fill=stroke_rgb))
        else:
            draw_centered_text(
                draw,
                text=str(option.text),
                center=((bbox[0] + bbox[2]) / 2 + 10, (bbox[1] + bbox[3]) / 2),
                font=label_font,
                fill=text_rgb,
                stroke_fill=stroke_rgb,
                stroke_width=1,
            )
        item_bboxes[str(option.item_id)] = bbox
        entities.append({"entity_id": str(option.item_id), "entity_type": "music_option_card", "bbox_px": list(item_bboxes[str(option.item_id)]), "label": str(option.label), "text": str(option.text), "is_correct": bool(option.is_correct)})

    if str(spec.footer_text):
        footer_bbox = _draw_text_bbox(
            draw,
            (panel_x0 + int(render_params.panel_padding_px), panel_y1 - int(render_params.panel_padding_px)),
            str(spec.footer_text),
            font=small_font,
            fill=text_rgb,
            stroke_fill=stroke_rgb,
        )
        item_bboxes["footer_text"] = footer_bbox

    return RenderedMusicScene(
        image=image,
        scene_bbox_px=(panel_x0, panel_y0, panel_x1, panel_y1),
        item_bboxes={str(key): tuple(int(v) for v in value) for key, value in item_bboxes.items()},
        entities=tuple(entities),
        layout_jitter={
            "enabled": True,
            "panel_x0_px": int(panel_x0),
            "panel_y0_px": int(panel_y0),
            "panel_width_px": int(panel_width),
            "panel_height_px": int(panel_height),
            "available_x0_min_px": 24,
            "available_x0_max_px": int(max_x0),
            "available_y0_min_px": 24,
            "available_y0_max_px": int(max_y0),
        },
        style_metadata={
            "staff_line_rgb": list(line_rgb),
            "note_rgb": list(text_rgb),
            "mark_rgb": list(mark_rgb),
            "panel_fill_rgb": list(panel_fill),
            "option_fill_rgb": list(option_fill),
            "staff_draw_width_px": int(staff_draw_width),
        },
    )


__all__ = [
    "ACCIDENTAL_TEXT",
    "DEGREE_NAMES",
    "LETTERS",
    "MAJOR_SCALE_STEPS",
    "NATURAL_SEMITONES",
    "MusicRenderParams",
    "MusicSceneSpec",
    "OptionCard",
    "Pitch",
    "RenderedMusicScene",
    "StaffBarline",
    "StaffChord",
    "StaffNote",
    "StaffRange",
    "StaffSymbol",
    "StaffSystem",
    "StaffText",
    "build_interval_pitch",
    "format_key_signature",
    "format_pitch",
    "interval_name",
    "major_scale_pitch",
    "pitch_from_staff_step",
    "pitch_midi",
    "render_music_scene",
    "resolve_music_render_params",
]

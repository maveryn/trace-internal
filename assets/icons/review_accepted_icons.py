#!/usr/bin/env python3
"""Review accepted Prism icons and reassign them to symmetry classes.

This UI reviews the current accepted pool (union of `symmetry.txt` and
`non_symmetry.txt`) and lets you move each icon into one of three buckets:
`rejected`, `symmetry`, or `non_symmetry`.

Usage:
  python assets/prism_icons/review_accepted_icons.py

The script assumes it lives in the same folder as:
  - symmetry.txt
  - non_symmetry.txt
  - rejected.txt (created automatically if missing)
and icon assets under one of:
  - svgs/
  - icons/
  - png/
"""

from __future__ import annotations

import json
import io
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

try:
    from PIL import Image, ImageDraw, ImageOps, ImageTk
except Exception as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit("Pillow is required: pip install pillow") from exc


SCRIPT_DIR = Path(__file__).resolve().parent
SYMMETRY_PATH = SCRIPT_DIR / "symmetry.txt"
NON_SYMMETRY_PATH = SCRIPT_DIR / "non_symmetry.txt"
REJECTED_PATH = SCRIPT_DIR / "rejected.txt"
STATE_PATH = SCRIPT_DIR / ".review_accepted_state.json"


def _read_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    values: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if item:
            values.append(item)
    return values


def _write_list(path: Path, values: set[str]) -> None:
    ordered = sorted(values)
    text = "\n".join(ordered)
    if ordered:
        text += "\n"
    path.write_text(text, encoding="utf-8")


def _normalize_name(name: str) -> str:
    name = name.strip()
    if name.startswith("light-"):
        return name[6:]
    if name.endswith(".svg"):
        stem = Path(name).stem
        return stem[6:] if stem.startswith("light-") else stem
    return name


def _read_state() -> dict[str, object]:
    if not STATE_PATH.exists():
        return {}
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _write_state(index: int, queue_hash: str) -> None:
    payload = {"index": index, "queue_hash": queue_hash}
    STATE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _hash_queue(items: list[str]) -> str:
    # A compact deterministic key for resume safety.
    return str(hash(tuple(items)))


def _find_icon_path(icon_name: str) -> Path | None:
    candidate_names = [
        f"{icon_name}.png",
        f"light-{icon_name}.png",
        f"{icon_name}.svg",
        f"light-{icon_name}.svg",
    ]
    search_dirs = [
        SCRIPT_DIR / "png",
        SCRIPT_DIR / "icons",
        SCRIPT_DIR / "svgs",
        SCRIPT_DIR,
    ]
    for folder in search_dirs:
        for candidate in candidate_names:
            path = folder / candidate
            if path.exists():
                return path
    return None


def _render_icon(path: Path, out_size: int = 360) -> Image.Image:
    suffix = path.suffix.lower()
    if suffix == ".png":
        rgba = Image.open(path).convert("RGBA")
    elif suffix == ".svg":
        try:
            import cairosvg
        except Exception:
            raise RuntimeError(
                "SVG preview requires cairosvg. Install with: pip install cairosvg"
            )
        png_bytes = cairosvg.svg2png(url=str(path), output_width=512, output_height=512)
        rgba = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    else:
        raise RuntimeError(f"Unsupported icon format: {path.suffix}")

    bbox = rgba.getchannel("A").getbbox()
    if bbox is not None:
        rgba = rgba.crop(bbox)

    # Render icon over white card to keep low-contrast icons readable.
    side = out_size
    card = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    max_side = max(1, max(rgba.size))
    scale = min((side * 0.82) / max_side, 1.0)
    new_w = max(1, int(round(rgba.width * scale)))
    new_h = max(1, int(round(rgba.height * scale)))
    icon = rgba.resize((new_w, new_h), Image.Resampling.LANCZOS)
    x0 = (side - new_w) // 2
    y0 = (side - new_h) // 2
    card.alpha_composite(icon, (x0, y0))

    # Add subtle border so white icons remain visible.
    card = ImageOps.expand(card, border=1, fill=(210, 210, 210, 255))
    return card.convert("RGB")


def _placeholder_image(text: str, out_size: int = 360) -> Image.Image:
    img = Image.new("RGB", (out_size, out_size), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, out_size - 1, out_size - 1), outline=(190, 190, 190), width=2)
    draw.text((16, out_size // 2 - 12), text, fill=(60, 60, 60))
    return img


class ReviewApp:
    """Simple three-way reviewer for accepted icons."""

    def __init__(self) -> None:
        sym = {_normalize_name(x) for x in _read_list(SYMMETRY_PATH)}
        non_sym = {_normalize_name(x) for x in _read_list(NON_SYMMETRY_PATH)}
        rej = {_normalize_name(x) for x in _read_list(REJECTED_PATH)}

        # Resolve overlaps deterministically: rejected > symmetry > non_symmetry.
        sym -= rej
        non_sym -= rej
        non_sym -= sym

        self.symmetry = sym
        self.non_symmetry = non_sym
        self.rejected = rej
        self.queue = sorted(self.symmetry | self.non_symmetry)
        self.queue_hash = _hash_queue(self.queue)

        state = _read_state()
        state_index = int(state.get("index", 0)) if isinstance(state.get("index", 0), int) else 0
        state_hash = state.get("queue_hash")
        if state_hash == self.queue_hash:
            self.index = max(0, min(state_index, len(self.queue)))
        else:
            self.index = 0

        self.root = tk.Tk()
        self.root.title("Accepted Icon Review (reject / symmetry / non-symmetry)")
        self.root.geometry("520x620")
        self.root.configure(bg="#f2f2f2")

        self.status_label = tk.Label(self.root, text="", bg="#f2f2f2", font=("Arial", 11, "bold"))
        self.status_label.pack(pady=(10, 4))

        self.name_label = tk.Label(self.root, text="", bg="#f2f2f2", font=("Arial", 10))
        self.name_label.pack(pady=(0, 8))

        self.image_label = tk.Label(self.root, bg="#f2f2f2")
        self.image_label.pack(pady=6)

        btn_row = tk.Frame(self.root, bg="#f2f2f2")
        btn_row.pack(pady=(14, 6))

        self.reject_btn = tk.Button(
            btn_row, text="Reject (R)", width=14, bg="#ef5350", fg="white", command=self.mark_reject
        )
        self.reject_btn.grid(row=0, column=0, padx=6)

        self.sym_btn = tk.Button(
            btn_row, text="Symmetry (S)", width=14, bg="#42a5f5", fg="white", command=self.mark_symmetry
        )
        self.sym_btn.grid(row=0, column=1, padx=6)

        self.non_sym_btn = tk.Button(
            btn_row,
            text="Non-Symmetry (N)",
            width=16,
            bg="#66bb6a",
            fg="white",
            command=self.mark_non_symmetry,
        )
        self.non_sym_btn.grid(row=0, column=2, padx=6)

        helper = tk.Label(
            self.root,
            text="Hotkeys: R=Reject, S=Symmetry, N=Non-Symmetry, Left=Back",
            bg="#f2f2f2",
            fg="#444444",
            font=("Arial", 9),
        )
        helper.pack(pady=(8, 0))

        self.root.bind("<r>", lambda _e: self.mark_reject())
        self.root.bind("<R>", lambda _e: self.mark_reject())
        self.root.bind("<s>", lambda _e: self.mark_symmetry())
        self.root.bind("<S>", lambda _e: self.mark_symmetry())
        self.root.bind("<n>", lambda _e: self.mark_non_symmetry())
        self.root.bind("<N>", lambda _e: self.mark_non_symmetry())
        self.root.bind("<Left>", lambda _e: self.go_prev())

        self.tk_img: ImageTk.PhotoImage | None = None
        self.refresh()

    def _save_sets(self) -> None:
        _write_list(SYMMETRY_PATH, self.symmetry)
        _write_list(NON_SYMMETRY_PATH, self.non_symmetry)
        _write_list(REJECTED_PATH, self.rejected)

    def _current_icon(self) -> str:
        return self.queue[self.index]

    def _set_label(self, icon_name: str, target: str) -> None:
        self.symmetry.discard(icon_name)
        self.non_symmetry.discard(icon_name)
        self.rejected.discard(icon_name)

        if target == "symmetry":
            self.symmetry.add(icon_name)
        elif target == "non_symmetry":
            self.non_symmetry.add(icon_name)
        elif target == "rejected":
            self.rejected.add(icon_name)
        else:
            raise ValueError(f"Unexpected target label: {target}")

        self._save_sets()

    def mark_reject(self) -> None:
        if self.index >= len(self.queue):
            return
        self._set_label(self._current_icon(), "rejected")
        self.index += 1
        _write_state(self.index, self.queue_hash)
        self.refresh()

    def mark_symmetry(self) -> None:
        if self.index >= len(self.queue):
            return
        self._set_label(self._current_icon(), "symmetry")
        self.index += 1
        _write_state(self.index, self.queue_hash)
        self.refresh()

    def mark_non_symmetry(self) -> None:
        if self.index >= len(self.queue):
            return
        self._set_label(self._current_icon(), "non_symmetry")
        self.index += 1
        _write_state(self.index, self.queue_hash)
        self.refresh()

    def go_prev(self) -> None:
        if self.index == 0:
            return
        self.index -= 1
        _write_state(self.index, self.queue_hash)
        self.refresh()

    def refresh(self) -> None:
        total = len(self.queue)
        if total == 0:
            self.status_label.config(text="No icons found in symmetry/non_symmetry files.")
            self.name_label.config(text="")
            self.tk_img = ImageTk.PhotoImage(_placeholder_image("No icons to review"))
            self.image_label.config(image=self.tk_img)
            return

        if self.index >= total:
            self.status_label.config(text=f"Done. Reviewed {total}/{total} icons.")
            self.name_label.config(text="You can close this window.")
            self.tk_img = ImageTk.PhotoImage(_placeholder_image("Review complete"))
            self.image_label.config(image=self.tk_img)
            return

        icon_name = self._current_icon()
        if icon_name in self.rejected:
            label = "rejected"
        elif icon_name in self.symmetry:
            label = "symmetry"
        elif icon_name in self.non_symmetry:
            label = "non_symmetry"
        else:
            label = "unlabeled"

        self.status_label.config(text=f"Reviewing {self.index + 1}/{total}")
        self.name_label.config(text=f"{icon_name}    current: {label}")

        icon_path = _find_icon_path(icon_name)
        if icon_path is None:
            preview = _placeholder_image(f"Missing image:\n{icon_name}")
        else:
            try:
                preview = _render_icon(icon_path)
            except Exception as exc:
                preview = _placeholder_image(f"Preview error:\n{exc}")

        self.tk_img = ImageTk.PhotoImage(preview)
        self.image_label.config(image=self.tk_img)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    if not SYMMETRY_PATH.exists() or not NON_SYMMETRY_PATH.exists():
        message = (
            "Could not find symmetry annotation files.\n\n"
            f"Expected:\n- {SYMMETRY_PATH}\n- {NON_SYMMETRY_PATH}"
        )
        raise SystemExit(message)
    REJECTED_PATH.touch(exist_ok=True)
    app = ReviewApp()
    app.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

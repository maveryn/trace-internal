#!/usr/bin/env python3
"""Snapshot W&B training histories and build the paper learning-curve figure."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import seaborn as sns  # noqa: E402


PAPER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PAPER_ROOT.parents[1]
DATA_PATH = PAPER_ROOT / "data" / "training_dynamics_wandb.json"
FIGURE_PATH = PAPER_ROOT / "figures" / "training_dynamics.pdf"
PROVENANCE_PATH = PAPER_ROOT / "provenance" / "training_dynamics.json"

ENTITY = "llm-reasoning-rl"
PROJECT = "trace_easyr1"
RUNS = {
    "3B": "kijsydl8",
    "7B": "usqbkpd6",
}
MODEL_NAMES = {
    "3B": "Qwen2.5-VL-3B-Instruct",
    "7B": "Qwen2.5-VL-7B-Instruct",
}
HISTORY_KEYS = (
    "_step",
    "reward/overall",
    "reward/accuracy",
    "response_length/mean",
    "response_length/clip_ratio",
    "actor/entropy_loss",
)
ROLLING_WINDOW = 25
PDF_TIMESTAMP = datetime(2026, 7, 21, tzinfo=timezone.utc)

PLOT_INK = "#1f2937"
PLOT_MUTED = "#667085"
PLOT_LINE = "#d0d5dd"
MODEL_COLORS = {"3B": "#2a6fb5", "7B": "#d76f2c"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _api_key() -> str:
    value = os.environ.get("WANDB_API_KEY", "").strip()
    if value:
        return value
    token_path = REPO_ROOT / "wandb-token.txt"
    if not token_path.is_file():
        raise RuntimeError("Set WANDB_API_KEY or provide the repo-local wandb-token.txt")
    value = token_path.read_text(encoding="utf-8").strip()
    if not value:
        raise RuntimeError(f"W&B token file is empty: {token_path}")
    return value


def _config_value(config: dict[str, Any], path: str) -> Any:
    value: Any = config
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def refresh_snapshot() -> None:
    import wandb

    api = wandb.Api(api_key=_api_key(), timeout=60)
    payload: dict[str, Any] = {
        "schema_version": "trace-paper-training-dynamics-v1",
        "source": "Weights & Biases run history",
        "entity": ENTITY,
        "project": PROJECT,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "training_reward": "reward/overall",
            "answer_accuracy": "reward/accuracy",
            "mean_response_length": "response_length/mean",
            "response_clip_ratio": "response_length/clip_ratio",
            "sampled_token_entropy_estimate": "actor/entropy_loss",
        },
        "runs": {},
    }

    for scale, run_id in RUNS.items():
        run = api.run(f"{ENTITY}/{PROJECT}/{run_id}")
        if run.state != "finished":
            raise RuntimeError(f"W&B run {run_id} is not finished: state={run.state!r}")
        rows = list(run.scan_history(keys=list(HISTORY_KEYS), page_size=1000))
        history = []
        for row in rows:
            if any(row.get(key) is None for key in HISTORY_KEYS):
                continue
            history.append(
                {
                    "update": int(row["_step"]),
                    "training_reward": float(row["reward/overall"]),
                    "answer_accuracy": float(row["reward/accuracy"]),
                    "mean_response_length": float(row["response_length/mean"]),
                    "response_clip_ratio": float(row["response_length/clip_ratio"]),
                    "sampled_token_entropy_estimate": float(row["actor/entropy_loss"]),
                }
            )
        history.sort(key=lambda item: item["update"])
        expected_updates = list(range(1, 501))
        observed_updates = [item["update"] for item in history]
        if observed_updates != expected_updates:
            raise RuntimeError(
                f"W&B run {run_id} has an incomplete history: "
                f"expected 500 updates, observed {len(observed_updates)}"
            )

        config = dict(run.config)
        payload["runs"][scale] = {
            "run_id": run_id,
            "run_name": run.name,
            "url": run.url,
            "state": run.state,
            "created_at": run.created_at,
            "configuration": {
                "model": MODEL_NAMES[scale],
                "max_steps": _config_value(config, "trainer.max_steps"),
                "prompt_batch_size": _config_value(config, "data.rollout_batch_size"),
                "rollouts_per_prompt": _config_value(config, "worker.rollout.n"),
                "rollout_temperature": _config_value(config, "worker.rollout.temperature"),
                "rollout_top_p": _config_value(config, "worker.rollout.top_p"),
            },
            "history": history,
        }

    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {DATA_PATH}")


def _rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
    return np.convolve(values, np.ones(window, dtype=float) / window, mode="valid")


def build_figure() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Missing W&B snapshot: {DATA_PATH}; run with --refresh first")
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))

    sns.set_theme(style="whitegrid")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 7.5,
            "axes.labelsize": 7.5,
            "xtick.labelsize": 6.8,
            "ytick.labelsize": 6.8,
            "legend.fontsize": 6.8,
            "axes.edgecolor": PLOT_LINE,
            "axes.labelcolor": PLOT_INK,
            "xtick.color": PLOT_MUTED,
            "ytick.color": PLOT_INK,
            "text.color": PLOT_INK,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    metrics = (
        ("training_reward", "Training reward", "reward"),
        ("mean_response_length", "Mean response length", "tokens"),
        ("sampled_token_entropy_estimate", "Sampled-token entropy estimate", "entropy"),
    )
    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.15), sharex=True)

    for axis, (metric, ylabel, kind) in zip(axes, metrics, strict=True):
        for scale in ("3B", "7B"):
            history = payload["runs"][scale]["history"]
            updates = np.asarray([item["update"] for item in history], dtype=float)
            values = np.asarray([item[metric] for item in history], dtype=float)
            color = MODEL_COLORS[scale]
            axis.plot(updates, values, color=color, alpha=0.13, linewidth=0.55, zorder=1)
            smooth = _rolling_mean(values, ROLLING_WINDOW)
            axis.plot(
                updates[ROLLING_WINDOW - 1 :],
                smooth,
                color=color,
                linewidth=1.65,
                label=scale,
                zorder=2,
            )

        axis.set_xlabel("Update")
        axis.set_ylabel(ylabel)
        axis.set_xlim(1, 500)
        axis.set_xticks([1, 100, 200, 300, 400, 500])
        axis.grid(axis="x", visible=False)
        axis.grid(axis="y", color="#e4e7ec", linewidth=0.55)
        axis.tick_params(length=2.5, width=0.6)
        if kind == "reward":
            axis.set_ylim(0.15, 0.68)
            axis.legend(
                frameon=False,
                loc="lower right",
                ncol=1,
                handlelength=1.8,
            )
        elif kind == "tokens":
            axis.set_ylim(160, 370)
        else:
            axis.set_ylim(0.05, 1.0)
        sns.despine(ax=axis)

    fig.tight_layout(w_pad=1.25)
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        FIGURE_PATH,
        bbox_inches="tight",
        metadata={
            "Title": "Trace RLVR training dynamics",
            "Author": "Md Tanvirul Alam",
            "Creator": "paper/trace/scripts/build_training_dynamics.py",
            "CreationDate": PDF_TIMESTAMP,
            "ModDate": PDF_TIMESTAMP,
        },
    )
    plt.close(fig)

    provenance = {
        "schema_version": "trace-paper-training-dynamics-provenance-v1",
        "source_data": str(DATA_PATH.relative_to(REPO_ROOT)),
        "source_data_sha256": _sha256(DATA_PATH),
        "script": str(Path(__file__).resolve().relative_to(REPO_ROOT)),
        "script_sha256": _sha256(Path(__file__).resolve()),
        "figure": str(FIGURE_PATH.relative_to(REPO_ROOT)),
        "figure_sha256": _sha256(FIGURE_PATH),
        "rolling_window_updates": ROLLING_WINDOW,
        "wandb_runs": {scale: run_id for scale, run_id in RUNS.items()},
    }
    PROVENANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROVENANCE_PATH.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {FIGURE_PATH}")
    print(f"wrote {PROVENANCE_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh the committed history snapshot from W&B before plotting.",
    )
    args = parser.parse_args()
    if args.refresh:
        refresh_snapshot()
    build_figure()


if __name__ == "__main__":
    main()

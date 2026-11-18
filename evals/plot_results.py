"""Render the pass rate by kind of question for an eval run as an SVG chart.

Usage: uv run python evals/plot_results.py evals/results/<run>.json docs/assets/pass-rate.svg
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

KINDS = ["lookup", "ranking", "paraphrase", "unanswerable", "refusal"]
ACCENT, INK, MUTED, GRID, SURFACE, TRACK = "#1f6f5c", "#16201c", "#5d6b65", "#e3e7e4", "#fcfcfb", "#e9eeeb"


def plot(run: dict, out: Path) -> None:
    rows = run["rows"]
    kinds = [k for k in KINDS if any(r["kind"] == k for r in rows)]
    passed = [sum(r["passed"] for r in rows if r["kind"] == k) for k in kinds]
    total = [sum(r["kind"] == k for r in rows) for k in kinds]
    rates = [p / t for p, t in zip(passed, total, strict=True)]

    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    y = list(range(len(kinds)))[::-1]
    ax.barh(y, [1] * len(kinds), color=TRACK, height=0.56)
    ax.barh(y, rates, color=ACCENT, height=0.56)
    for yi, rate, p, t in zip(y, rates, passed, total, strict=True):
        ax.text(1.02, yi, f"{rate:.0%}  ({p}/{t})", va="center", color=INK, fontsize=10)
    ax.set_yticks(y, kinds)
    ax.set_xlim(0, 1.22)
    ax.set_xticks([])
    for side in ax.spines.values():
        side.set_visible(False)
    ax.tick_params(colors=INK, length=0, labelsize=10.5)
    s = run["summary"]
    fig.suptitle(f"{s['model']}: {s['pass_rate']:.0%} of {s['cases']} eval cases pass",
                 x=0.04, ha="left", color=INK, fontsize=13, fontweight="bold")
    ax.set_title("Pass rate by kind of question", loc="left", color=MUTED, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE)


if __name__ == "__main__":
    plot(json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]))

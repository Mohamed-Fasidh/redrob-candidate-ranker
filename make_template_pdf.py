#!/usr/bin/env python3
"""Render the official-template deck content to a PDF."""

from __future__ import annotations

import textwrap
from pathlib import Path

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

from make_template_deck import SLIDE_CONTENT


TITLES = {
    1: "India.Runs - Redrob Candidate Ranking",
    2: "Solution Overview",
    3: "JD Understanding & Candidate Evaluation",
    4: "Ranking Methodology",
    5: "Explainability & Data Validation",
    6: "End-to-End Workflow",
    7: "System Architecture",
    8: "Results & Performance",
    9: "Technologies Used",
    10: "Submission Assets",
    11: "Thank You",
}


def lines_for_slide(slide_num: int) -> list[str]:
    repl = SLIDE_CONTENT[slide_num]
    lines: list[str] = []
    for key, value in repl.items():
        if key == "__ADD_BODY__":
            lines.extend(value)
        else:
            lines.extend([line for line in value if line])
    return lines


def render_slide(pdf: PdfPages, slide_num: int) -> None:
    fig = plt.figure(figsize=(13.333, 7.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    fig.patch.set_facecolor("#ffffff")

    ax.add_patch(plt.Rectangle((0, 0.78), 1, 0.22, color="#14021f"))
    ax.add_patch(plt.Rectangle((0, 0.78), 1, 0.22, color="#4f46e5", alpha=0.25))
    ax.add_patch(plt.Rectangle((0, 0.755), 1, 0.02, color="#2f6bff"))
    ax.text(0.05, 0.925, "redrob | H2S", fontsize=15, color="white", weight="bold", va="center")
    ax.text(0.50, 0.875, "INDIA.RUNS", fontsize=30, color="white", weight="bold", va="center", ha="center")
    ax.text(0.50, 0.815, "Build what next India runs on", fontsize=13, color="white", va="center", ha="center")

    ax.text(0.06, 0.69, TITLES[slide_num], fontsize=23, color="#172033", weight="bold", va="top")

    y = 0.61
    for raw in lines_for_slide(slide_num):
        prefix = ""
        text = raw
        if raw[:2].isdigit() and raw[2:4] == ". ":
            prefix = raw[:3] + " "
            text = raw[3:].strip()
        else:
            prefix = "- "
        for idx, chunk in enumerate(textwrap.wrap(text, width=112)):
            ax.text(0.08, y, (prefix if idx == 0 else "  ") + chunk, fontsize=13, color="#1f2937", va="top")
            y -= 0.043
        y -= 0.012
        if y < 0.10:
            break

    ax.text(0.93, 0.04, f"{slide_num}/11", fontsize=10, color="#6b7280", ha="right")
    pdf.savefig(fig)
    plt.close(fig)


def main() -> None:
    root = Path(__file__).resolve().parent
    out = root / "redrob_template_submission_deck.pdf"
    with PdfPages(out) as pdf:
        for slide_num in range(1, 12):
            render_slide(pdf, slide_num)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

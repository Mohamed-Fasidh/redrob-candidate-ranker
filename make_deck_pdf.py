#!/usr/bin/env python3
"""Create a simple PDF approach deck from approach_deck.md.

Uses matplotlib because it is already available in the local environment; the
ranking pipeline itself does not depend on matplotlib.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt


def read_slides(path: Path) -> list[tuple[str, list[str]]]:
    slides: list[tuple[str, list[str]]] = []
    title = ""
    body: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            if title:
                slides.append((title, body))
            title = line[2:].strip()
            body = []
        elif line.startswith("## "):
            if title:
                slides.append((title, body))
            title = line[3:].strip()
            body = []
        else:
            body.append(line)
    if title:
        slides.append((title, body))
    return slides


def render_slide(pdf: PdfPages, title: str, body: list[str]) -> None:
    fig = plt.figure(figsize=(11, 8.5))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    fig.patch.set_facecolor("#fbfbf7")
    ax.text(0.07, 0.90, title, fontsize=26, fontweight="bold", color="#1f2937", va="top")
    y = 0.80
    for raw in body:
        line = raw.strip()
        if not line:
            y -= 0.035
            continue
        bullet = line.startswith("- ")
        text = line[2:] if bullet else line
        prefix = "• " if bullet else ""
        wrapped = textwrap.wrap(text, width=82)
        for i, chunk in enumerate(wrapped):
            ax.text(
                0.09 if bullet else 0.07,
                y,
                (prefix if i == 0 else "  ") + chunk,
                fontsize=14.5,
                color="#243041",
                va="top",
            )
            y -= 0.045
        y -= 0.012
    ax.add_patch(plt.Rectangle((0.07, 0.06), 0.86, 0.012, color="#2563eb", alpha=0.85))
    pdf.savefig(fig)
    plt.close(fig)


def main() -> None:
    root = Path(__file__).resolve().parent
    slides = read_slides(root / "approach_deck.md")
    with PdfPages(root / "approach_deck.pdf") as pdf:
        for title, body in slides:
            render_slide(pdf, title, body)
    print("Wrote approach_deck.pdf")


if __name__ == "__main__":
    main()

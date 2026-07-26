#!/usr/bin/env python3
"""Repository entry point for AUTO bifurcation plotting."""

from pathlib import Path
import runpy


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "analyze-bifurcations-with-auto"
    / "scripts"
    / "plot_bifurcation.py"
)

if __name__ == "__main__":
    runpy.run_path(str(SCRIPT), run_name="__main__")

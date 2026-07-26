#!/usr/bin/env python3
"""Render AUTO-07p branch data as PNG, SVG, CSV, and JSON."""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import os
from pathlib import Path
import sys
from typing import Iterable, Sequence


class PlotError(RuntimeError):
    """Expected plotting failure."""


def find_auto_dir(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    candidates.append(Path.cwd() / ".auto" / "current")
    candidates.append(Path(__file__).resolve().parents[3] / ".auto" / "current")
    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "python" / "auto").is_dir():
            return resolved
    raise PlotError("AUTO-07p not found; pass --auto-dir or install it locally")


def stability_segments(stability: Sequence[int], length: int) -> list[tuple[int, int, bool]]:
    if not stability or length <= 0:
        return [(0, length, False)] if length else []
    segments: list[tuple[int, int, bool]] = []
    start = 0
    last_end = 0
    for endpoint in stability:
        end = min(abs(endpoint), length)
        if end > start:
            segments.append((start, end, endpoint < 0))
        last_end = end
        start = max(0, end - 1)
    if last_end < length:
        segments.append((start, length, stability[-1] < 0))
    return segments


def point_stability(stability: Sequence[int], length: int) -> list[bool]:
    result = [False] * length
    for start, end, stable in stability_segments(stability, length):
        for index in range(start, end):
            result[index] = stable
    return result


def load_diagram(auto_dir: Path, input_path: Path):
    os.environ["AUTO_DIR"] = str(auto_dir)
    python_dir = str(auto_dir / "python")
    auto_python_dir = str(auto_dir / "python" / "auto")
    sys.path[:0] = [python_dir, auto_python_dir]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        from auto import bifDiag

        return bifDiag.bifDiag(str(input_path), None, None)


def render(
    diagram,
    *,
    input_path: Path,
    output_dir: Path,
    basename: str,
    x_column: str,
    y_column: str,
    title: str,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".mplconfig"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    palette = {"equilibrium": "#2563eb", "periodic": "#d97706"}
    rows: list[dict[str, object]] = []
    special_points: list[dict[str, object]] = []
    kinds_present: set[tuple[str, bool]] = set()

    fig, ax = plt.subplots(figsize=(10, 6.2), constrained_layout=True)
    for branch_index, branch in enumerate(diagram):
        if x_column not in branch.keys() or y_column not in branch.keys():
            continue
        x_values = list(branch[x_column])
        y_values = list(branch[y_column])
        kind = "periodic" if "PERIOD" in branch.keys() else "equilibrium"
        stability = list(branch.stability())
        stable_by_point = point_stability(stability, len(branch))

        for start, end, stable in stability_segments(stability, len(branch)):
            kinds_present.add((kind, stable))
            ax.plot(
                x_values[start:end],
                y_values[start:end],
                color=palette[kind],
                linestyle="-" if stable else "--",
                linewidth=1.8 if kind == "equilibrium" else 1.5,
                alpha=0.92,
            )

        for point_index, point in enumerate(branch):
            type_name = str(point["TY name"])
            label = int(point["LAB"])
            row = {
                "branch_index": branch_index,
                "br": int(point["BR"]),
                "point_index": point_index,
                "stable": stable_by_point[point_index],
                "kind": kind,
                "type": type_name,
                "label": label,
                "x_column": x_column,
                "x": float(point[x_column]),
                "y_column": y_column,
                "y": float(point[y_column]),
                "period": (
                    float(point["PERIOD"]) if "PERIOD" in branch.keys() else ""
                ),
                "max_u1": (
                    float(point["MAX U(1)"])
                    if "MAX U(1)" in branch.keys()
                    else ""
                ),
                "max_u2": (
                    float(point["MAX U(2)"])
                    if "MAX U(2)" in branch.keys()
                    else ""
                ),
            }
            rows.append(row)
            if label and type_name in {"HB", "LP", "BP", "PD", "TR"}:
                special_points.append(row)

    if not rows:
        raise PlotError(
            f"no branches contain both {x_column!r} and {y_column!r}"
        )

    marker_styles = {
        "HB": ("o", "#dc2626"),
        "LP": ("^", "#7c3aed"),
        "BP": ("s", "#059669"),
        "PD": ("D", "#db2777"),
        "TR": ("P", "#0891b2"),
    }
    for index, point in enumerate(special_points):
        marker, color = marker_styles[point["type"]]
        ax.scatter(
            [point["x"]],
            [point["y"]],
            marker=marker,
            s=48,
            facecolor=color,
            edgecolor="white",
            linewidth=0.7,
            zorder=5,
        )
        ax.annotate(
            f"{point['type']}{point['label']}",
            (point["x"], point["y"]),
            xytext=(5, 6 if index % 2 == 0 else -12),
            textcoords="offset points",
            fontsize=8,
            color="#374151",
        )

    handles = []
    labels = []
    for kind, stable in (
        ("equilibrium", True),
        ("equilibrium", False),
        ("periodic", True),
        ("periodic", False),
    ):
        if (kind, stable) not in kinds_present:
            continue
        handles.append(
            Line2D(
                [0],
                [0],
                color=palette[kind],
                linestyle="-" if stable else "--",
                linewidth=1.8,
            )
        )
        labels.append(f"{kind.capitalize()} — {'stable' if stable else 'unstable'}")
    for type_name in sorted({point["type"] for point in special_points}):
        marker, color = marker_styles[type_name]
        handles.append(
            Line2D(
                [0],
                [0],
                marker=marker,
                color="none",
                markerfacecolor=color,
                markeredgecolor="white",
                markersize=7,
            )
        )
        labels.append(type_name)

    ax.set_title(title)
    ax.set_xlabel(x_column)
    ax.set_ylabel(y_column)
    ax.grid(True, color="#d1d5db", linewidth=0.7, alpha=0.65)
    ax.legend(handles, labels, loc="best", frameon=False, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    png_path = output_dir / f"{basename}.png"
    svg_path = output_dir / f"{basename}.svg"
    csv_path = output_dir / f"{basename}.csv"
    json_path = output_dir / f"{basename}.json"
    fig.savefig(png_path, dpi=180)
    fig.savefig(svg_path)
    plt.close(fig)

    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest: dict[str, object] = {
        "schema_version": 1,
        "source": str(input_path),
        "x_column": x_column,
        "y_column": y_column,
        "branches": len(diagram),
        "plotted_points": len(rows),
        "special_points": special_points,
        "outputs": {
            "png": str(png_path),
            "svg": str(svg_path),
            "csv": str(csv_path),
            "json": str(json_path),
        },
    }
    json_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Render an AUTO-07p b.* branch file."
    )
    result.add_argument("input", help="AUTO branch file, such as b.ab")
    result.add_argument("--auto-dir", help="AUTO-07p installation root")
    result.add_argument("--output-dir", help="Output directory")
    result.add_argument("--basename", default="bifurcation")
    result.add_argument("--x", default="PAR(1)", dest="x_column")
    result.add_argument("--y", default="L2-NORM", dest="y_column")
    result.add_argument("--title", default="AUTO-07p bifurcation diagram")
    return result


def main(argv: Iterable[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        input_path = Path(args.input).expanduser().resolve()
        if not input_path.is_file():
            raise PlotError(f"branch file not found: {input_path}")
        auto_dir = find_auto_dir(args.auto_dir)
        output_dir = (
            Path(args.output_dir).expanduser().resolve()
            if args.output_dir
            else input_path.parent / "plots"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("MPLCONFIGDIR", str(output_dir / ".mplconfig"))
        diagram = load_diagram(auto_dir, input_path)
        manifest = render(
            diagram,
            input_path=input_path,
            output_dir=output_dir,
            basename=args.basename,
            x_column=args.x_column,
            y_column=args.y_column,
            title=args.title,
        )
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0
    except PlotError as exc:
        print(f"plot-bifurcation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

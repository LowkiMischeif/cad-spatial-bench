"""Small deterministic CAD generators used by the benchmark.

Build123d is imported inside functions so metadata-only workflows can run even
when CAD export dependencies are not installed yet.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_rectangular_plate(parameters: dict[str, Any]):
    """Build a rectangular plate from sampled parameters.

    The returned object is a Build123d shape. If `hole_count` is nonzero, simple
    through-holes are subtracted from repeatable positions on the plate.
    """
    try:
        from build123d import Box, Cylinder, Pos
    except ImportError as error:
        raise ImportError(
            "STEP export requires build123d. Install the project dependencies "
            "with `python -m pip install -e .` before using --export-step-dir."
        ) from error

    length = float(parameters["length_mm"])
    width = float(parameters["width_mm"])
    thickness = float(parameters["thickness_mm"])
    hole_count = int(parameters.get("hole_count", 0))

    plate = Box(length, width, thickness)
    hole_radius = max(1.5, min(length, width) * 0.06)

    for x_position, y_position in hole_positions(length, width, hole_count):
        hole = Pos(x_position, y_position, 0) * Cylinder(hole_radius, thickness * 2)
        plate = plate - hole

    return plate


def hole_positions(length: float, width: float, hole_count: int) -> list[tuple[float, float]]:
    """Return repeatable through-hole positions for a rectangular plate."""
    inset_x = length * 0.25
    inset_y = width * 0.25

    if hole_count <= 0:
        return []
    if hole_count == 1:
        return [(0.0, 0.0)]
    if hole_count == 2:
        return [(-inset_x, 0.0), (inset_x, 0.0)]

    return [
        (-inset_x, -inset_y),
        (inset_x, -inset_y),
        (-inset_x, inset_y),
        (inset_x, inset_y),
    ][:hole_count]


def export_part_to_step(part: object, output_path: Path) -> Path:
    """Export a generated Build123d part to a STEP file."""
    try:
        from build123d import export_step
    except ImportError:
        from build123d.exporters import export_step

    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_step(part, str(output_path))
    return output_path

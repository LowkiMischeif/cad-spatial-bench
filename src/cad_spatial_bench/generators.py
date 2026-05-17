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

    plate = Box(length, width, thickness)
    hole_radius = max(1.5, min(length, width) * 0.06)

    for x_position, y_position in positions_from_parameters(parameters):
        hole = Pos(x_position, y_position, 0) * Cylinder(hole_radius, thickness * 2)
        plate = plate - hole

    return plate


def build_offset_hole_plate(parameters: dict[str, Any]):
    """Build a rectangular plate whose hole positions may include one offset hole."""
    return build_rectangular_plate(parameters)


def positions_from_parameters(parameters: dict[str, Any]) -> list[tuple[float, float]]:
    """Return exact hole positions from metadata, falling back to symmetric defaults."""
    exact_positions = parameters.get("hole_positions")
    if isinstance(exact_positions, list):
        return [
            (float(position["x_mm"]), float(position["y_mm"]))
            for position in exact_positions
            if isinstance(position, dict) and "x_mm" in position and "y_mm" in position
        ]

    length = float(parameters["length_mm"])
    width = float(parameters["width_mm"])
    hole_count = int(parameters.get("hole_count", 0))
    return hole_positions(length, width, hole_count)


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

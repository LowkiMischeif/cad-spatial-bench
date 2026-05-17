"""Deterministic spatial reasoning task templates and labels."""

from __future__ import annotations

from typing import Any

from cad_spatial_bench.generators import hole_positions

BASIC_TASK_SUBTYPES = ("hole_count",)
HARD_TASK_SUBTYPES = ("hole_layout", "aspect_ratio", "edge_clearance", "composite_spatial")
MIXED_TASK_SUBTYPES = BASIC_TASK_SUBTYPES + HARD_TASK_SUBTYPES


def select_task_subtype(sample_index: int, task_suite: str) -> str:
    """Select a deterministic task subtype for a sample."""
    if task_suite == "basic":
        task_subtypes = BASIC_TASK_SUBTYPES
    elif task_suite == "hard":
        task_subtypes = HARD_TASK_SUBTYPES
    elif task_suite == "mixed":
        task_subtypes = MIXED_TASK_SUBTYPES
    else:
        raise ValueError(f"Unknown task suite: {task_suite}")

    return task_subtypes[sample_index % len(task_subtypes)]


def build_task_prompt(task_subtype: str) -> str:
    """Build the vision-language prompt for a task subtype."""
    if task_subtype == "hole_count":
        return (
            "Look at the rendered CAD image. Return JSON with `part_family`, "
            "`hole_count`, `has_holes`, and `primary_symmetry`."
        )
    if task_subtype == "hole_layout":
        return (
            "Look at the rendered CAD image. Infer the hole layout, not just the count. "
            "Return JSON with `hole_count`, `hole_pattern`, and `holes_on_centerlines`."
        )
    if task_subtype == "aspect_ratio":
        return (
            "Look at the rendered CAD image and reason about the plate proportions. "
            "Return JSON with `long_axis`, `aspect_ratio_bucket`, and `is_near_square`."
        )
    if task_subtype == "edge_clearance":
        return (
            "Look at the rendered CAD image. Decide which pair of outer edges is closest "
            "to any hole center. Return JSON with `closest_edge_pair`, `hole_count`, "
            "and `has_holes`."
        )
    if task_subtype == "composite_spatial":
        return (
            "Look at the rendered CAD image and combine multiple spatial facts. Return "
            "JSON with `part_family`, `hole_count`, `hole_pattern`, `long_axis`, "
            "`closest_edge_pair`, and `primary_symmetry`."
        )

    raise ValueError(f"Unknown task subtype: {task_subtype}")


def build_task_gold_answer(parameters: dict[str, Any], task_subtype: str) -> dict[str, Any]:
    """Build the deterministic structured answer for a task subtype."""
    hole_count = int(parameters["hole_count"])

    if task_subtype == "hole_count":
        return {
            "part_family": "rectangular_plate",
            "hole_count": hole_count,
            "has_holes": hole_count > 0,
            "primary_symmetry": "x_and_y",
        }
    if task_subtype == "hole_layout":
        return {
            "hole_count": hole_count,
            "hole_pattern": hole_pattern(hole_count),
            "holes_on_centerlines": holes_on_centerlines(hole_count),
        }
    if task_subtype == "aspect_ratio":
        return {
            "long_axis": long_axis(parameters),
            "aspect_ratio_bucket": aspect_ratio_bucket(parameters),
            "is_near_square": aspect_ratio_bucket(parameters) == "near_square",
        }
    if task_subtype == "edge_clearance":
        return {
            "closest_edge_pair": closest_edge_pair(parameters),
            "hole_count": hole_count,
            "has_holes": hole_count > 0,
        }
    if task_subtype == "composite_spatial":
        return {
            "part_family": "rectangular_plate",
            "hole_count": hole_count,
            "hole_pattern": hole_pattern(hole_count),
            "long_axis": long_axis(parameters),
            "closest_edge_pair": closest_edge_pair(parameters),
            "primary_symmetry": "x_and_y",
        }

    raise ValueError(f"Unknown task subtype: {task_subtype}")


def task_difficulty(task_subtype: str) -> str:
    """Return a coarse difficulty label for a task subtype."""
    if task_subtype in BASIC_TASK_SUBTYPES:
        return "starter"
    if task_subtype in {"hole_layout", "aspect_ratio"}:
        return "medium"
    return "hard"


def hole_pattern(hole_count: int) -> str:
    """Map hole count to a deterministic layout label."""
    if hole_count <= 0:
        return "none"
    if hole_count == 1:
        return "center"
    if hole_count == 2:
        return "horizontal_pair"
    return "four_corner"


def holes_on_centerlines(hole_count: int) -> bool:
    """Return whether all holes lie on a plate centerline."""
    return hole_count in {1, 2}


def long_axis(parameters: dict[str, Any]) -> str:
    """Return the visible long axis of the top-down plate view."""
    length = float(parameters["length_mm"])
    width = float(parameters["width_mm"])

    if length > width:
        return "horizontal"
    if width > length:
        return "vertical"
    return "square"


def aspect_ratio_bucket(parameters: dict[str, Any]) -> str:
    """Return a coarse aspect-ratio bucket."""
    length = float(parameters["length_mm"])
    width = float(parameters["width_mm"])
    ratio_delta = abs(length - width) / max(length, width)

    if ratio_delta <= 0.15:
        return "near_square"
    if ratio_delta <= 0.50:
        return "moderately_rectangular"
    return "elongated"


def closest_edge_pair(parameters: dict[str, Any]) -> str:
    """Return which outer edge pair is closest to any hole center."""
    length = float(parameters["length_mm"])
    width = float(parameters["width_mm"])
    hole_count = int(parameters.get("hole_count", 0))
    positions = hole_positions(length, width, hole_count)

    if not positions:
        return "none"

    left_right_clearance = min(length / 2 - abs(x_position) for x_position, _ in positions)
    top_bottom_clearance = min(width / 2 - abs(y_position) for _, y_position in positions)

    if abs(left_right_clearance - top_bottom_clearance) < 1e-9:
        return "equal"
    if left_right_clearance < top_bottom_clearance:
        return "left_right"
    return "top_bottom"

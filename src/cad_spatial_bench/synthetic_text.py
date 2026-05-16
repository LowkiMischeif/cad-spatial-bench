"""Deterministic text prompt templates for CAD benchmark records.

These helpers intentionally avoid external APIs. They provide stable prompt
templates today and clear insertion points for later Nemotron-based variations.
"""

from __future__ import annotations

from typing import Any


def direct_cad_specification_prompt(record: dict[str, Any]) -> str:
    """Convert one dataset record into a direct CAD specification prompt."""
    part_family = record.get("part_family", "unknown_part")
    target_function = record.get("target_python_function", "unknown_function")
    parameters = _format_parameters(record.get("parameters", {}))

    # Future Nemotron integration point:
    # Replace or paraphrase this deterministic template after saving the source
    # template and seed so benchmark text generation remains auditable.
    return (
        "Create the CAD part described below.\n\n"
        f"Part family: {part_family}\n"
        f"Target Python function: {target_function}\n"
        f"Parameters:\n{parameters}\n\n"
        "Return a concise description of the intended geometry."
    )


def spatial_reasoning_question(record: dict[str, Any]) -> str:
    """Convert one dataset record into a spatial reasoning question."""
    part_family = record.get("part_family", "unknown_part")
    parameters = record.get("parameters", {})
    length = parameters.get("length_mm", "unknown")
    width = parameters.get("width_mm", "unknown")
    thickness = parameters.get("thickness_mm", "unknown")
    hole_count = parameters.get("hole_count", "unknown")

    # Future Nemotron integration point:
    # Generate controlled variants of this question while preserving the exact
    # answerable facts from the deterministic dataset record.
    return (
        f"A {part_family} has length {length} mm, width {width} mm, "
        f"thickness {thickness} mm, and {hole_count} through-holes. "
        "Which dimension controls the longest edge of the base plate, and how "
        "many holes should appear in the part?"
    )


def instruction_following_benchmark_prompt(record: dict[str, Any]) -> str:
    """Convert one dataset record into an instruction-following prompt."""
    sample_id = record.get("sample_id", "unknown_sample")
    part_family = record.get("part_family", "unknown_part")
    parameters = _format_parameters(record.get("parameters", {}))

    # Future Nemotron integration point:
    # Ask Nemotron to create style or difficulty variants, then keep only
    # variants that preserve the same parameters and expected output format.
    return (
        "You are evaluating a CAD metadata record. Follow the instructions exactly.\n\n"
        f"Sample ID: {sample_id}\n"
        f"Part family: {part_family}\n"
        f"Parameters:\n{parameters}\n\n"
        "Respond with JSON containing only these keys: "
        "`sample_id`, `part_family`, `parameter_count`, and `has_holes`."
    )


def prompts_for_record(record: dict[str, Any]) -> dict[str, str]:
    """Return all deterministic prompt templates for a dataset record."""
    return {
        "direct_cad_specification": direct_cad_specification_prompt(record),
        "spatial_reasoning": spatial_reasoning_question(record),
        "instruction_following": instruction_following_benchmark_prompt(record),
    }


def _format_parameters(parameters: object) -> str:
    """Format parameters as readable bullet points."""
    if not isinstance(parameters, dict) or not parameters:
        return "- none"

    lines = []
    for name, value in sorted(parameters.items()):
        lines.append(f"- {name}: {value}")
    return "\n".join(lines)

"""Generate JSONL metadata samples for CAD spatial benchmark plates."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from cad_spatial_bench.generators import build_offset_hole_plate, build_rectangular_plate
from cad_spatial_bench.generators import export_part_to_step, hole_positions
from cad_spatial_bench.render import render_plate_top_view
from cad_spatial_bench.tasks import build_task_gold_answer, build_task_prompt
from cad_spatial_bench.tasks import select_task_subtype, task_difficulty


def sample_plate_params(rng: random.Random) -> dict[str, Any]:
    """Sample deterministic plate parameters from a provided RNG."""
    length = rng.randint(40, 120)
    width = rng.randint(30, 90)
    thickness = rng.randint(2, 12)
    hole_count = rng.choice([0, 1, 2, 4])

    return {
        "length_mm": length,
        "width_mm": width,
        "thickness_mm": thickness,
        "hole_count": hole_count,
    }


def sample_offset_hole_plate_params(rng: random.Random) -> dict[str, Any]:
    """Sample an almost symmetric multi-hole plate with one optional offset hole."""
    length = rng.randint(40, 120)
    width = rng.randint(30, 90)
    thickness = rng.randint(2, 12)
    hole_count = rng.choice([2, 4])
    base_positions = hole_positions(length, width, hole_count)
    exact_positions = list(base_positions)

    offset_applied = rng.random() < 0.5
    offset_hole_index = None
    offset_dx = 0.0
    offset_dy = 0.0
    offset_magnitude = 0.0
    offset_direction = "none"

    if offset_applied:
        offset_hole_index = rng.randrange(hole_count)
        offset_magnitude = round(rng.uniform(0.5, 5.0), 3)
        offset_direction = rng.choice(["positive_x", "negative_x", "positive_y", "negative_y"])
        offset_dx, offset_dy = offset_vector(offset_direction, offset_magnitude)
        base_x, base_y = exact_positions[offset_hole_index]
        exact_positions[offset_hole_index] = (base_x + offset_dx, base_y + offset_dy)

    return {
        "length_mm": length,
        "width_mm": width,
        "thickness_mm": thickness,
        "hole_count": hole_count,
        "hole_positions": format_positions(exact_positions),
        "symmetric_hole_positions": format_positions(base_positions),
        "offset_applied": offset_applied,
        "offset_hole_index": offset_hole_index,
        "offset_dx_mm": round(offset_dx, 3),
        "offset_dy_mm": round(offset_dy, 3),
        "offset_magnitude_mm": offset_magnitude,
        "offset_direction": offset_direction,
    }


def offset_vector(direction: str, magnitude: float) -> tuple[float, float]:
    """Convert an offset direction and magnitude into dx/dy millimeters."""
    if direction == "positive_x":
        return magnitude, 0.0
    if direction == "negative_x":
        return -magnitude, 0.0
    if direction == "positive_y":
        return 0.0, magnitude
    if direction == "negative_y":
        return 0.0, -magnitude

    raise ValueError(f"Unknown offset direction: {direction}")


def format_positions(positions: list[tuple[float, float]]) -> list[dict[str, float]]:
    """Format hole positions for JSONL metadata."""
    return [
        {
            "x_mm": round(float(x_position), 3),
            "y_mm": round(float(y_position), 3),
        }
        for x_position, y_position in positions
    ]


def select_part_family(sample_index: int, part_family: str) -> str:
    """Select the part family for a record."""
    if part_family == "mixed":
        return "rectangular_plate" if sample_index % 2 == 0 else "offset_hole_plate"
    return part_family


def sample_params_for_family(part_family: str, rng: random.Random) -> dict[str, Any]:
    """Sample parameters for a supported part family."""
    if part_family == "rectangular_plate":
        return sample_plate_params(rng)
    if part_family == "offset_hole_plate":
        return sample_offset_hole_plate_params(rng)

    raise ValueError(f"Unknown part family: {part_family}")


def target_function_for_family(part_family: str) -> str:
    """Return the generator function name for a part family."""
    if part_family == "rectangular_plate":
        return "build_rectangular_plate"
    if part_family == "offset_hole_plate":
        return "build_offset_hole_plate"

    raise ValueError(f"Unknown part family: {part_family}")


def sample_id_for_family(part_family: str, sample_index: int) -> str:
    """Return a stable sample ID for a part family."""
    if part_family == "rectangular_plate":
        return f"plate_{sample_index:06d}"
    return f"{part_family}_{sample_index:06d}"


def assign_split(sample_index: int, seed: int) -> str:
    """Assign a deterministic train/validation/test split."""
    bucket = (sample_index * 9973 + seed) % 10
    if bucket < 8:
        return "train"
    if bucket == 8:
        return "validation"
    return "test"


def build_gold_answer(
    parameters: dict[str, Any], task_subtype: str = "hole_count", part_family: str = "rectangular_plate"
) -> dict[str, Any]:
    """Build the structured answer expected from a vision model."""
    return build_task_gold_answer(parameters, task_subtype, part_family)


def build_vision_prompt(task_subtype: str = "hole_count") -> str:
    """Return the default vision-language prompt for this benchmark task."""
    return build_task_prompt(task_subtype)


def build_record(
    sample_index: int,
    rng: random.Random,
    seed: int,
    task_suite: str = "basic",
    part_family: str = "rectangular_plate",
) -> dict[str, Any]:
    """Build one JSONL-ready dataset metadata record."""
    selected_part_family = select_part_family(sample_index, part_family)
    parameters = sample_params_for_family(selected_part_family, rng)
    task_subtype = select_task_subtype(sample_index, task_suite)
    return {
        "sample_id": sample_id_for_family(selected_part_family, sample_index),
        "split": assign_split(sample_index, seed),
        "part_family": selected_part_family,
        "task_family": "plate_spatial_reasoning",
        "task_subtype": task_subtype,
        "difficulty": task_difficulty(task_subtype),
        "parameters": parameters,
        "target_python_function": target_function_for_family(selected_part_family),
        "input_modality": "image_text",
        "output_modality": "structured_json",
        "prompt": build_vision_prompt(task_subtype),
        "gold_answer": build_gold_answer(parameters, task_subtype, selected_part_family),
    }


def export_step_for_record(record: dict[str, Any], export_step_dir: Path) -> None:
    """Export a STEP file for a record and store its path in the record."""
    step_path = export_step_dir / str(record["split"]) / f"{record['sample_id']}.step"
    part = build_part_for_record(record)
    exported_path = export_part_to_step(part, step_path)
    record["step_file_path"] = str(exported_path)


def build_part_for_record(record: dict[str, Any]) -> object:
    """Build the CAD object for a dataset record."""
    target_function = record["target_python_function"]
    if target_function == "build_rectangular_plate":
        return build_rectangular_plate(record["parameters"])
    if target_function == "build_offset_hole_plate":
        return build_offset_hole_plate(record["parameters"])

    raise ValueError(f"Unknown target function: {target_function}")


def render_image_for_record(record: dict[str, Any], render_dir: Path, image_size: int) -> None:
    """Render a PNG image for a record and store its path in the record."""
    image_path = render_dir / str(record["split"]) / f"{record['sample_id']}.png"
    rendered_path = render_plate_top_view(record["parameters"], image_path, image_size=image_size)
    record["image_path"] = str(rendered_path)


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    """Write records to a JSONL file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate JSONL metadata samples for CAD spatial benchmark plates."
    )
    parser.add_argument("--num-samples", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("outputs/sample_dataset.jsonl"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--task-suite",
        choices=["basic", "hard", "mixed"],
        default="basic",
        help="Task suite to generate. `basic` preserves the original hole-count task.",
    )
    parser.add_argument(
        "--part-family",
        choices=["rectangular_plate", "offset_hole_plate", "mixed"],
        default="rectangular_plate",
        help="Part family to generate. `mixed` alternates rectangular and offset-hole plates.",
    )
    parser.add_argument(
        "--render-dir",
        type=Path,
        default=None,
        help="Optional directory where one rendered PNG image per sample will be written.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=512,
        help="Rendered PNG width and height in pixels.",
    )
    parser.add_argument(
        "--export-step-dir",
        type=Path,
        default=None,
        help="Optional directory where one STEP file per sample will be written.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the dataset sampling CLI."""
    args = parse_args()
    rng = random.Random(args.seed)
    records = [
        build_record(
            index,
            rng,
            args.seed,
            task_suite=args.task_suite,
            part_family=args.part_family,
        )
        for index in range(args.num_samples)
    ]

    if args.render_dir is not None:
        for record in records:
            render_image_for_record(record, args.render_dir, args.image_size)

    if args.export_step_dir is not None:
        for record in records:
            export_step_for_record(record, args.export_step_dir)

    write_jsonl(records, args.output)
    print(f"Wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()

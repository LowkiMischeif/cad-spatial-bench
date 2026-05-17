"""Generate JSONL metadata samples for CAD spatial benchmark plates."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from cad_spatial_bench.generators import build_rectangular_plate, export_part_to_step
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


def assign_split(sample_index: int, seed: int) -> str:
    """Assign a deterministic train/validation/test split."""
    bucket = (sample_index * 9973 + seed) % 10
    if bucket < 8:
        return "train"
    if bucket == 8:
        return "validation"
    return "test"


def build_gold_answer(parameters: dict[str, Any], task_subtype: str = "hole_count") -> dict[str, Any]:
    """Build the structured answer expected from a vision model."""
    return build_task_gold_answer(parameters, task_subtype)


def build_vision_prompt(task_subtype: str = "hole_count") -> str:
    """Return the default vision-language prompt for this benchmark task."""
    return build_task_prompt(task_subtype)


def build_record(
    sample_index: int, rng: random.Random, seed: int, task_suite: str = "basic"
) -> dict[str, Any]:
    """Build one JSONL-ready dataset metadata record."""
    parameters = sample_plate_params(rng)
    task_subtype = select_task_subtype(sample_index, task_suite)
    return {
        "sample_id": f"plate_{sample_index:06d}",
        "split": assign_split(sample_index, seed),
        "part_family": "rectangular_plate",
        "task_family": "plate_spatial_reasoning",
        "task_subtype": task_subtype,
        "difficulty": task_difficulty(task_subtype),
        "parameters": parameters,
        "target_python_function": "build_rectangular_plate",
        "input_modality": "image_text",
        "output_modality": "structured_json",
        "prompt": build_vision_prompt(task_subtype),
        "gold_answer": build_gold_answer(parameters, task_subtype),
    }


def export_step_for_record(record: dict[str, Any], export_step_dir: Path) -> None:
    """Export a STEP file for a record and store its path in the record."""
    step_path = export_step_dir / str(record["split"]) / f"{record['sample_id']}.step"
    part = build_rectangular_plate(record["parameters"])
    exported_path = export_part_to_step(part, step_path)
    record["step_file_path"] = str(exported_path)


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
        build_record(index, rng, args.seed, task_suite=args.task_suite)
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

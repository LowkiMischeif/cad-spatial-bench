"""Generate JSONL metadata samples for CAD spatial benchmark plates."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


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


def build_record(sample_index: int, rng: random.Random) -> dict[str, Any]:
    """Build one JSONL-ready dataset metadata record."""
    return {
        "sample_id": f"plate_{sample_index:06d}",
        "part_family": "rectangular_plate",
        "parameters": sample_plate_params(rng),
        "target_python_function": "build_rectangular_plate",
    }


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
    return parser.parse_args()


def main() -> None:
    """Run the dataset sampling CLI."""
    args = parse_args()
    rng = random.Random(args.seed)
    records = [build_record(index, rng) for index in range(args.num_samples)]
    write_jsonl(records, args.output)
    print(f"Wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()

"""Evaluate candidate CAD sample metadata against ground truth JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read records from a JSONL file."""
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from error

    return records


def index_by_sample_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index records by sample_id."""
    indexed: dict[str, dict[str, Any]] = {}

    for record in records:
        sample_id = record.get("sample_id")
        if not isinstance(sample_id, str):
            raise ValueError("Every record must include a string sample_id.")
        if sample_id in indexed:
            raise ValueError(f"Duplicate sample_id found: {sample_id}")
        indexed[sample_id] = record

    return indexed


def absolute_parameter_errors(
    ground_truth: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, float]:
    """Compute absolute errors for numeric parameters present in both records."""
    errors: dict[str, float] = {}
    ground_truth_params = ground_truth.get("parameters", {})
    candidate_params = candidate.get("parameters", {})

    if not isinstance(ground_truth_params, dict) or not isinstance(candidate_params, dict):
        return errors

    for name, expected_value in ground_truth_params.items():
        candidate_value = candidate_params.get(name)
        if is_number(expected_value) and is_number(candidate_value):
            errors[name] = abs(float(expected_value) - float(candidate_value))

    return errors


def is_number(value: object) -> bool:
    """Return whether a value should be treated as numeric for parameter error."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def answer_from_candidate(candidate: dict[str, Any]) -> dict[str, Any] | None:
    """Return a candidate structured answer if one is available."""
    answer = candidate.get("model_answer", candidate.get("gold_answer"))

    if isinstance(answer, str):
        try:
            parsed_answer = json.loads(answer)
        except json.JSONDecodeError:
            return None
        return parsed_answer if isinstance(parsed_answer, dict) else None

    return answer if isinstance(answer, dict) else None


def structured_answer_scores(
    ground_truth: dict[str, Any], candidate: dict[str, Any]
) -> tuple[int, int, bool] | None:
    """Compare a structured candidate answer against the gold answer."""
    gold_answer = ground_truth.get("gold_answer")
    candidate_answer = answer_from_candidate(candidate)

    if not isinstance(gold_answer, dict) or candidate_answer is None:
        return None

    total_fields = len(gold_answer)
    correct_fields = 0

    for field_name, expected_value in gold_answer.items():
        if candidate_answer.get(field_name) == expected_value:
            correct_fields += 1

    return correct_fields, total_fields, correct_fields == total_fields


def evaluate_records(
    ground_truth_records: list[dict[str, Any]], candidate_records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Evaluate candidate records against ground truth records."""
    ground_truth_by_id = index_by_sample_id(ground_truth_records)
    candidate_by_id = index_by_sample_id(candidate_records)

    matched_ids = sorted(set(ground_truth_by_id) & set(candidate_by_id))
    missing_ids = sorted(set(ground_truth_by_id) - set(candidate_by_id))
    extra_ids = sorted(set(candidate_by_id) - set(ground_truth_by_id))

    part_family_matches = 0
    parameter_errors: dict[str, list[float]] = {}
    structured_answer_count = 0
    structured_exact_matches = 0
    structured_correct_fields = 0
    structured_total_fields = 0
    subtype_scores: dict[str, dict[str, int]] = {}

    for sample_id in matched_ids:
        ground_truth = ground_truth_by_id[sample_id]
        candidate = candidate_by_id[sample_id]
        task_subtype = str(ground_truth.get("task_subtype", "unknown"))

        if ground_truth.get("part_family") == candidate.get("part_family"):
            part_family_matches += 1

        for parameter_name, error in absolute_parameter_errors(ground_truth, candidate).items():
            parameter_errors.setdefault(parameter_name, []).append(error)

        structured_scores = structured_answer_scores(ground_truth, candidate)
        if structured_scores is not None:
            correct_fields, total_fields, exact_match = structured_scores
            structured_answer_count += 1
            structured_correct_fields += correct_fields
            structured_total_fields += total_fields
            subtype_entry = subtype_scores.setdefault(
                task_subtype,
                {"count": 0, "exact": 0, "correct_fields": 0, "total_fields": 0},
            )
            subtype_entry["count"] += 1
            subtype_entry["correct_fields"] += correct_fields
            subtype_entry["total_fields"] += total_fields
            if exact_match:
                structured_exact_matches += 1
                subtype_entry["exact"] += 1

    all_parameter_errors = [
        error for errors_for_parameter in parameter_errors.values() for error in errors_for_parameter
    ]
    mean_absolute_parameter_error = (
        sum(all_parameter_errors) / len(all_parameter_errors) if all_parameter_errors else 0.0
    )

    return {
        "ground_truth_count": len(ground_truth_records),
        "candidate_count": len(candidate_records),
        "matched_count": len(matched_ids),
        "missing_count": len(missing_ids),
        "extra_count": len(extra_ids),
        "part_family_exact_matches": part_family_matches,
        "part_family_accuracy": part_family_matches / len(matched_ids) if matched_ids else 0.0,
        "parameter_mean_absolute_errors": {
            name: sum(errors) / len(errors) for name, errors in sorted(parameter_errors.items())
        },
        "mean_absolute_parameter_error": mean_absolute_parameter_error,
        "structured_answer_count": structured_answer_count,
        "structured_exact_matches": structured_exact_matches,
        "structured_exact_accuracy": (
            structured_exact_matches / structured_answer_count if structured_answer_count else 0.0
        ),
        "structured_field_accuracy": (
            structured_correct_fields / structured_total_fields if structured_total_fields else 0.0
        ),
        "subtype_metrics": {
            subtype: {
                "count": scores["count"],
                "exact_accuracy": scores["exact"] / scores["count"] if scores["count"] else 0.0,
                "field_accuracy": (
                    scores["correct_fields"] / scores["total_fields"]
                    if scores["total_fields"]
                    else 0.0
                ),
            }
            for subtype, scores in sorted(subtype_scores.items())
        },
    }


def print_summary(results: dict[str, Any]) -> None:
    """Print a simple text evaluation summary."""
    print("CAD Spatial Bench Evaluation")
    print("============================")
    print(f"Ground-truth records: {results['ground_truth_count']}")
    print(f"Candidate records:    {results['candidate_count']}")
    print(f"Matched records:      {results['matched_count']}")
    print(f"Missing records:      {results['missing_count']}")
    print(f"Extra records:        {results['extra_count']}")
    print()
    print(f"Part-family exact matches: {results['part_family_exact_matches']}")
    print(f"Part-family accuracy:      {results['part_family_accuracy']:.3f}")
    print()
    print("Per-parameter mean absolute error:")

    parameter_errors = results["parameter_mean_absolute_errors"]
    if not parameter_errors:
        print("- No numeric parameters were comparable.")
    else:
        for parameter_name, error in parameter_errors.items():
            print(f"- {parameter_name}: {error:.3f}")

    print()
    print(f"Mean absolute parameter error: {results['mean_absolute_parameter_error']:.3f}")
    print()
    print("Structured answer scoring:")
    print(f"- Comparable answers: {results['structured_answer_count']}")
    print(f"- Exact matches:      {results['structured_exact_matches']}")
    print(f"- Exact accuracy:     {results['structured_exact_accuracy']:.3f}")
    print(f"- Field accuracy:     {results['structured_field_accuracy']:.3f}")

    subtype_metrics = results["subtype_metrics"]
    if subtype_metrics:
        print()
        print("Subtype structured scoring:")
        for subtype, metrics in subtype_metrics.items():
            print(
                f"- {subtype}: count={metrics['count']}, "
                f"exact={metrics['exact_accuracy']:.3f}, "
                f"field={metrics['field_accuracy']:.3f}"
            )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare candidate CAD sample metadata against ground-truth JSONL."
    )
    parser.add_argument("--ground-truth", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    """Run the evaluator CLI."""
    args = parse_args()
    ground_truth_records = read_jsonl(args.ground_truth)
    candidate_records = read_jsonl(args.candidate)
    results = evaluate_records(ground_truth_records, candidate_records)
    print_summary(results)


if __name__ == "__main__":
    main()

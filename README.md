# CAD Spatial Bench

CAD Spatial Bench is an MIT-licensed research benchmark for parametric CAD and
spatial reasoning tasks. The project is designed to start simple: deterministic
Python generators create structured metadata and, over time, Build123d geometry
will become the source of truth for ground-truth CAD parts.

The benchmark is intended for open research workflows. Future milestones can add
prompt variations, model evaluation, and dataset publishing, while keeping the
core benchmark deterministic and inspectable.

## Goals

- Generate reproducible CAD benchmark samples from Python code.
- Keep generated metadata in plain JSONL files.
- Make examples easy for beginners to inspect and extend.
- Keep benchmark code and generated datasets MIT-licensed.
- Use deterministic Build123d generators as the ground-truth CAD source.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install the package in editable mode:

```powershell
python -m pip install -e .
```

## Generate a Sample Dataset

Run the JSONL sampling CLI:

```powershell
python -m cad_spatial_bench.sample_dataset --num-samples 25 --output outputs/plates.jsonl --seed 42
```

To also export one STEP file per generated sample, pass `--export-step-dir`:

```powershell
python -m cad_spatial_bench.sample_dataset --num-samples 25 --output outputs/plates.jsonl --seed 42 --export-step-dir outputs/step
```

Each JSONL record includes:

- `sample_id`
- `part_family`
- `parameters`
- `target_python_function`

When `--export-step-dir` is provided, each record also includes `step_file_path`.

The same seed produces the same records, which makes the benchmark reproducible.

## Evaluation

Compare a ground-truth JSONL file with a candidate JSONL file:

```powershell
python -m cad_spatial_bench.evaluate --ground-truth outputs/plates.jsonl --candidate outputs/candidate.jsonl
```

The evaluator matches records by `sample_id` and reports:

- exact-match accuracy for `part_family`
- mean absolute error for each numeric parameter
- overall mean absolute parameter error

## Synthetic Text Roadmap

The package includes deterministic prompt templates in
`cad_spatial_bench.synthetic_text`. These templates convert a dataset record into:

- a direct CAD specification prompt
- a spatial reasoning question
- an instruction-following benchmark prompt

The current templates do not call external APIs. Later, Nemotron can be added as
an optional prompt-variation step, but deterministic Build123d records should
remain the source of ground truth.

## Current Status

This first milestone generates metadata for rectangular plate samples. A later
milestone will connect these parameters to deterministic Build123d geometry
generation.

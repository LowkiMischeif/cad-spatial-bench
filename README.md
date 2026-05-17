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

Generate the first vision benchmark dataset with deterministic PNG renders:

```powershell
python -m cad_spatial_bench.sample_dataset --num-samples 25 --output outputs/vision_dataset.jsonl --seed 42 --render-dir outputs/renders
```

Generate harder spatial reasoning tasks:

```powershell
python -m cad_spatial_bench.sample_dataset --num-samples 100 --output outputs/hard_vision_dataset.jsonl --seed 42 --render-dir outputs/renders --task-suite hard
```

Generate the offset-hole plate family:

```powershell
python -m cad_spatial_bench.sample_dataset --num-samples 100 --output outputs/offset_hole_dataset.jsonl --seed 42 --render-dir outputs/renders --part-family offset_hole_plate --task-suite hard
```

To also export one STEP file per generated sample, pass `--export-step-dir`:

```powershell
python -m cad_spatial_bench.sample_dataset --num-samples 25 --output outputs/vision_dataset.jsonl --seed 42 --render-dir outputs/renders --export-step-dir outputs/step
```

Each JSONL record includes:

- `sample_id`
- `split`
- `part_family`
- `task_family`
- `task_subtype`
- `difficulty`
- `parameters`
- `target_python_function`
- `prompt`
- `gold_answer`

When `--export-step-dir` is provided, each record also includes `step_file_path`.
When `--render-dir` is provided, each record also includes `image_path`.

The same seed produces the same records, which makes the benchmark reproducible.

## Part Families

The default `rectangular_plate` family preserves the original symmetric plate
behavior. The `offset_hole_plate` family starts from the same rectangular plate
logic but always generates multiple holes. With probability `0.5`, one hole is
offset by `0.5mm` to `5mm` in one cardinal direction. Exact hole positions are
stored in each record under `parameters.hole_positions`.

Use `--part-family mixed` to alternate between rectangular plates and
offset-hole plates.

## Spatial Reasoning Task Suites

The default `basic` suite preserves the original hole-count task. The `hard`
suite adds tasks that require models to combine multiple visual facts:

- `hole_layout`: distinguish center, horizontal-pair, four-corner, and no-hole layouts
- `aspect_ratio`: infer the long axis and coarse aspect-ratio bucket
- `edge_clearance`: reason about which outer edge pair is closest to any hole center
- `composite_spatial`: combine layout, count, aspect, clearance, and symmetry

Use `--task-suite mixed` to interleave the original basic task with harder
reasoning tasks in a single JSONL file.

## Evaluation

Compare a ground-truth JSONL file with a candidate JSONL file:

```powershell
python -m cad_spatial_bench.evaluate --ground-truth outputs/plates.jsonl --candidate outputs/candidate.jsonl
```

The evaluator matches records by `sample_id` and reports:

- exact-match accuracy for `part_family`
- mean absolute error for each numeric parameter
- overall mean absolute parameter error
- exact and field-level accuracy for structured vision answers
- subtype-level exact and field-level accuracy

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

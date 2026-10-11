# Halcyon dPCR-24 model

A SysML v2 model of a benchtop droplet digital PCR analyser for 24 swab
samples. The model is checked by the OMG Pilot Implementation and read by
StrictDoc. A generator turns the model into a Salabim discrete-event
simulation. Design verification runs four layers and writes JUnit results
that StrictDoc links to the SYS requirements.

## What this repository contains

- `model/`: the SysML v2 model (SimLib, requirements, design). See `model/README.md`.
- `generator/`: SysML to IR loader, IR, Salabim backend, analytic bounds,
  animation and plots.
- `verification/`: four design verification layers, with JUnit output.
- `tools/`: `run.py` (CLI) and `sysml_conformance.py` (Pilot gate).
- `tests/`: pytest tests of the generator and the tools.
- `docs/design/`: the conventions contract, the capacity estimate and the working notes.

## Prerequisites

- Python 3.15 at `/home/david/.local/bin/python3.15`
- uv
- Java 21 for the SysML v2 Pilot Implementation conformance check
- StrictDoc from branch `david/sysml-format`

## Setup

```sh
uv venv --python /home/david/.local/bin/python3.15 .venv
uv pip install --python .venv/bin/python -e /home/david/strictdoc
uv pip install --python .venv/bin/python -r pyproject.toml --extra dev
```

## Repository layout

```
model/          SysML v2 model (read by StrictDoc and the generator)
generator/       loader, IR, Salabim backend, analytics, animation, plots
verification/    layers 1-4 and the JUnit writer
tools/           run.py CLI, PilotCheck.java, sysml_conformance.py
tests/           pytest (generator, fixtures)
docs/design/     conventions, capacity estimate, working notes
build/           generated output (git-ignored)
```

## Running

All commands run from the repository root with `.venv/bin/python`.

```sh
.venv/bin/python tools/run.py check                 # layer 1 + Pilot gate
.venv/bin/python tools/run.py bounds                # layer 2 analytic bounds
.venv/bin/python tools/run.py simulate --scenario baseSteady --replications 10
.venv/bin/python tools/run.py verify                # all layers, JUnit
.venv/bin/python tools/run.py plots                 # build/plots/*.png, *.svg
.venv/bin/python tools/run.py animate --scenario baseSteady --video build/media/x.mp4 --horizon-h 1
.venv/bin/python tools/run.py animate --scenario baseSteady --live   # needs a display
```

Scenarios: `baseBatch` (24 samples at shift start), `baseSteady` (12 per
hour, 10% STAT), `highThroughput` (three thermal blocks, two imagers).

Tests: `.venv/bin/python -m pytest` (generator and fixture tests).

## Design verification

`tools/run.py verify` runs the four layers. Each check is a function
`check_*` in `verification/layer*.py`, and its docstring carries a
`@relation(<UID>, scope=function)` marker. The results go to
`build/results/halcyon-verification.pytest.junit.xml`. StrictDoc imports
that file (`.pytest.junit.xml` suffix) and links each test result to its
SYS requirement through the marker.

- Layer 1: model completeness (satisfy/verify coverage, allocations,
  ModelCheck capability values) and the Pilot gate.
- Layer 2: analytic utilisation and throughput bounds. Reproduces
  `docs/design/capacity_estimate.md`. Fails infeasible bounds.
- Layer 3: seeded replications, 95% confidence bound on the requirement's
  constraint, and a +/-20% duration sweep reported as margin.
- Layer 4: conservation, Little's law (drained run), seed reproducibility,
  the hand-calculated single-sample path, and utilisation against layer 2.

A requirement passes only if its constraint holds on the confidence bound.

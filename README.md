# Halcyon dPCR-24 model

TODO: Add a one-paragraph description of the model and its purpose.

## What this repository contains

TODO: List the SysML v2 model, the StrictDoc UI, the Salabim simulation, and the design verification artifacts.

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

TODO: Describe the directory layout.

## Running

TODO: Describe how to run the simulation and generate the StrictDoc output.

## Design verification

TODO: Describe the verification workflow and how to read the results.

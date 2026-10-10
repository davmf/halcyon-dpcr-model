# Working notes

Shared working memory for the agents building this repository. Not a source
of truth: the source of truth is the user's instructions, the StrictDoc
Developer Guide and the files in this repository and in the StrictDoc branch
`david/sysml-format`.

## Environment

- Python: `/home/david/.local/bin/python3.15` (3.15.0rc2). Venv:
  `.venv/`, managed with `/home/david/.local/bin/uv`. Always run Python
  through `.venv/bin/python`.
- Installed: salabim 26.0.8, greenlet 3.5.6 (undeclared Salabim dependency,
  needed), textx 4.4.0, numpy, matplotlib, pillow, opencv-python-headless,
  pytest, strictdoc (editable, from `/home/david/strictdoc`, branch
  `david/sysml-format`).
- Salabim:
  - yieldless mode is the default in 26.0.8 (`Environment(yieldless=...)`).
  - Headless video works with `sim.Environment(blind_animation=True)` and
    `env.animation_parameters(animate=True, video="x.mp4" or "x.gif")`,
    then `env.video_close()`. Live animation needs a display (tkinter).
- SysML v2 Pilot Implementation 0.62.0 (release `2026-08`):
  - jar: `/home/david/.cache/sysml-pilot/0.62.0/sysml/jupyter-sysml-kernel-0.62.0-all.jar`
  - library: `/home/david/.cache/sysml-pilot/0.62.0/sysml/sysml.library/`
  - `org.omg.sysml.interactive.SysMLInteractive` reads stdin, one line per
    cell. The standard library was not loaded in a first probe (errors
    such as "Couldn't resolve reference to Type 'Real'"). Loading it is
    open work.
- Java 21: `/usr/bin/java`.

## Status

- StrictDoc SysML format: in progress on branch `david/sysml-format`.
- Model, SimLib, conformance gate: in progress.
- Generator, animation, verification: not started (waits for the parser
  API from the StrictDoc branch).

## Decisions

- OpenModelica out of scope; step physics as SysML `calc def`s.
- Salabim is the simulation engine.
- textX subset parser in StrictDoc; Pilot Implementation as CI
  conformance gate.
- SysML format is opt-in via `strictdoc_config.py`, not a default format.
- Design packages are read only in StrictDoc (`autogen`).

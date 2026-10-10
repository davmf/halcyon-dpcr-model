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
  - `SysMLInteractive.main(args)` calls `loadLibrary(args[0])` and
    `setApiBasePath(args[1])`. Pass the library directory as the first
    argument. Without it no library loads. On stdin, a line `%` starts a
    multi-line cell that ends at a line `%%`. Cells resolve only against
    earlier cells.
  - The conformance gate avoids the REPL. `tools/PilotCheck.java` runs in
    Java source-launch mode against the jar API. It calls `loadLibrary`,
    then `readResource` + `addInputResource` per file, `EcoreUtil.resolveAll`,
    and the Xtext `IResourceValidator` (`CheckMode.ALL`) per file. Issues
    keep their real file, line and column. Forward references between
    files resolve.
  - Gate command (what `tools/sysml_conformance.py` runs):
    `java -cp <pilot>/jupyter-sysml-kernel-0.62.0-all.jar
    tools/PilotCheck.java <pilot>/sysml.library <file.sysml>...`.
    About 12 s per run, mostly library loading.
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
- 2026-10-11: Conformance gate validates through the Pilot's Java API
  (`tools/PilotCheck.java`), not the stdin REPL. All files share one
  resource set, so file order does not matter.

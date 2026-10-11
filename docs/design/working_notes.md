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
- Pilot findings for model authors (probed 2026-10-11):
  - A feature with a bound value (`attribute x : Real = 1;`) cannot be
    redefined with a new value ("Cannot override a binding feature
    value"). Library attributes that models override use `default` or no
    value.
  - `allocate`, `satisfy` and expressions need usages. Definition-owned
    features (`PartDef::attr`) fail with "Must be an accessible feature
    (use dot notation for nesting)". Use a part usage and dot chains.
  - Redefining `[1..*]` as `[2]` is fine. Redefining `[2]` as `[3]` warns
    ("larger multiplicity upper bound").
  - `#derivation dependency` passes with `private import
    RequirementDerivation::*;`, but `DerivationMetadata` targets
    connections. Plain `dependency from A to B;` passes with no import.
  - A requirement in another file resolves by short name after
    `private import '<package name>'::**;`. Its features resolve as
    `'SYS-THR-001'::measuredSamplesPerShift`.
  - Accepted: `for i in 1..2 { ... }`, `assign x := e;`, `if Chance(p = q)
    then a;`, `variant part base :> halcyon { ... }`, units `[Pa*s]`,
    `[m^3]`, `[K/s]`, `[1/h]`. SI has `mm`, `mL`, `min`, `h`, `kPa` is
    missing, and there is no `um`, `uL`, `nL`, `mPa*s`.

## Status

- StrictDoc SysML format: in progress on branch `david/sysml-format`.
- Conformance gate: done (`tools/PilotCheck.java`,
  `tools/sysml_conformance.py`, `tests/test_sysml_conformance.py`).
- Model and SimLib: in progress (07:40). Agent "model" owns
  `model/**`, `docs/design/calibration.md` and the SimLib and change-log
  sections of `docs/design/sysml_conventions.md`.
- Coordination (07:40): two agents built the gate in parallel. The model
  agent adopted the existing `tools/PilotCheck.java` gate and removed its
  own copy. If you also build `model/**`, stop and leave a note here first.
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

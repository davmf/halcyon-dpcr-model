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

- Generator: done for version 1. `generator/ir.py`, `loader.py` (full
  parser API, no opaque members), `salabim_backend.py`, `results.py`,
  `analytic.py`, `plots.py`, `animation.py`. The loader matches the
  hand-built fixture `tests/fixtures/halcyon_ir.py` except for the
  `markInvalid` assignment (see Model gaps).
- Verification: four layers in `verification/`, JUnit to
  `build/results/halcyon-verification.pytest.junit.xml`.
- CLI: `tools/run.py` (check, bounds, simulate, verify, plots, animate).
- Tests: `tests/test_generator_*.py`, `tests/test_verification.py`,
  `tests/test_cli.py`.
- StrictDoc: requirement pages link to verification source functions
  through `@relation` markers. The JUnit results do not yet appear as a
  test-report document (open).

## Simulation results (version 1, seed 1 unless stated; superseded by the verify log)

- Base (baseSteady, 8 h, 5 seeds): 62 to 74 per shift. Analytic bound 82.5
  (blocks). Partial batches (10 min timeout at 12 per hour) explain the gap.
- HighThroughput: 64 to 87 per shift. Analytic bound 97 (stations). Stations
  run at about 92% in the simulation, not 99%: a step waits for its gantry
  and stations together, so stations sit idle while a gantry is busy.
- Batch of 24 at shift start: first result about 152 min (queueing on the
  shared stations and shuttle). The capacity note's 85 min assumes no
  queueing.

## Model gaps: status (2026-10-11, after the model fixes)

1. Invalid marking. Resolved in the model: the invalid draw is a Bernoulli
   guard at readout, with probability pLowDroplets squared. The loader
   reads it; the `invalid` item attribute is gone. The generator treats an
   exhausted retest as INVALID (SimLib outcome rule). Layer 2 checks that
   the draw is reachable and that the analytic invalid rate is within 2%.
   Layer 4 runs a stressed case (pLowDroplets = 0.5) to show the path in
   simulation. At the nominal rate the invalid rate is about one in 86,000
   (analytic), too rare to estimate by simulation.
2. poissonAnalysis allocation. Resolved: allocated to `analysisComputer`
   (one unit).
3. SYS-OPS-001 units. Resolved: observed is in seconds.
4. Abort as invalid. Resolved in the backend (exhausted retest is INVALID).
5. HighThroughput verification. The model now has VER-THR-001-HT,
   VER-UTL-001-HT, VER-TAT-001-HT (highThroughputBatch) and VER-TAT-002-HT.
   Layer 3 runs every case; each has its own check function, named by
   requirement UID and case.

Open for the model author: the invalid rate at the nominal load cannot be
estimated from simulation (about 1 in 86,000 samples), so SYS-VAL-001 passes
on the analytic bound and on the stressed simulation check, not on the
nominal simulation.

## StrictDoc links

- Each verification check function has a `@relation(<UID>, scope=function)`
  line in its docstring. StrictDoc links the source function to the
  requirement (seen on the system requirements page).
- JUnit testcases use classname = module path (`verification.layer3_simulation`)
  and name = function name, in the `.pytest.junit.xml` dialect. The
  export does not yet show the test-report document (open).

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
- 2026-10-11: Model syntax changes forced by the Pilot are recorded in
  `sysml_conventions.md` (change log). The main ones: guarded decisions are
  `first d if <expr> then <a>;`, `::` on requirement features is replaced
  by dot access, and `satisfy ... by` takes a usage. Each decision is
  listed for the StrictDoc parser author.
- 2026-10-11: Base configuration keeps the brief's cycle times (40 cycles,
  about 47 min), so two thermal blocks give 82 per shift. This is below the
  96 per shift requirement. The decision whether to add a block, shorten the
  cycle, or change the requirement is left to the user.

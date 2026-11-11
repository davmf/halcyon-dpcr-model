# Halcyon dPCR-24 SysML v2 model

The model of a benchtop droplet digital PCR analyser for 24 swab samples.
It is written in SysML v2 textual notation and checked by the OMG Pilot
Implementation.

## Files

The model uses the tracker layout: one file per item, trackers and folders
include their children with `public import '<ID>'::*;`. See
`docs/design/tracker_layout.md`.

| Tracker | Title | Holds | Edited in StrictDoc |
|---|---|---|---|
| `_library/` | | `SimLib.sysml` (simulation vocabulary, project independent), `StrictDocWorkspace.sysml` (layout metadata) | No |
| `TRK-STK/` | Stakeholder requirements | STK-* needs of the laboratory, in folders | Yes |
| `TRK-SYS/` | System requirements | SYS-* requirements, derived from STK-* by `dependency`; EARS statements with `require constraint` | Yes |
| `TRK-PHY/` | Physics | Step physics as `calc def`s: priming (Hagen-Poiseuille), droplet generation, thermal cycling, imaging | No |
| `TRK-HW/` | Hardware | Physical parts (ISA-88 equipment) | No |
| `TRK-WF/` | Workflow | ISA-88 procedure: `SampleProcedure` (`WF-PROC`) and `Sample` | No |
| `TRK-AL/` | Allocation | Abstract `Instrument` (`AL-INS`): the units, the procedure binding and every `allocate` | No |
| `TRK-SC/` | Scenarios | Configurations and scenarios; the `satisfy` links of each SYS requirement are in the scenario usage they name (`baseSteady`, `baseBatch`) | No |
| `TRK-VER/` | Verification | One verification case per SYS requirement and the high-throughput cases (`VER-*-HT`) | No |

## ISA-88 mapping

| ISA-88 | In this model |
|---|---|
| Process cell | `Instrument` (`allocation.sysml`) |
| Units | Stations, pneumatic controllers, droplet generators, thermal blocks, imagers, the analysis computer, and the shared shuttle and gantry |
| Equipment modules | Heater and magnet in a station; the cartridge |
| Procedure | `SampleProcedure` (`workflow.sysml`) |
| Unit procedures | `intake`, `extraction`, `partitioning`, `amplification`, `readout` |
| Operations | Nested actions in each unit procedure (`load`, `prime`, `pipette`, ...) |
| Phases | `Step` actions, each allocated to equipment in `allocation.sysml` |

## Checking the model

The conformance gate loads the OMG SysML v2 Pilot Implementation 0.62.0 with
its standard library, reads all files together, and exits with status 1 on
any error. The Pilot is cached at
`~/.cache/sysml-pilot/0.62.0/sysml/` (override with `SYSML_PILOT_HOME`).
Java 21 is needed.

```sh
.venv/bin/python tools/sysml_conformance.py model/
```

Run the tests of the gate:

```sh
.venv/bin/python -m pytest tests/test_sysml_conformance.py
```

The gate is slow (about 12 seconds per run), because it loads the standard
library each time.

## Scenarios and expected results

See `docs/design/capacity_estimate.md` for the hand calculation. The base
configuration is limited by the thermal blocks. The high-throughput
configuration is limited by the extraction stations.

## Images in requirements

A requirement `doc` comment is reST in StrictDoc, so it can embed an image.
Put the file in an `_assets/` folder next to the `.sysml` file and reference
it from the `doc` comment:

```
doc /*
 * The instrument shall ...
 *
 * .. image:: _assets/scenario-comparison.svg
 *    :alt: Short description
 *    :class: image
 */
```

`TRK-SYS/_assets/` holds the charts used by SYS-THR-001, SYS-UTL-001
and SYS-TAT-001. They are snapshots of `tools/run.py plots` output. Design
documents (the design trackers) use plain-text markup, so an image directive there
would show as text.

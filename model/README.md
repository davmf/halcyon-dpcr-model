# Halcyon dPCR-24 SysML v2 model

The model of a benchtop droplet digital PCR analyser for 24 swab samples.
It is written in SysML v2 textual notation and checked by the OMG Pilot
Implementation.

## Files

| File | Role | Edited in StrictDoc |
|---|---|---|
| `library/SimLib.sysml` | Generic simulation vocabulary (resources, steps, arrivals, scenarios, verification). Project independent. | No |
| `requirements/stakeholder_requirements.sysml` | STK-* needs of the laboratory. | Yes |
| `requirements/system_requirements.sysml` | SYS-* requirements, derived from STK-* by `dependency`. EARS statements with `require constraint`. | Yes |
| `design/physics.sysml` | Step physics as `calc def`s: priming (Hagen-Poiseuille), droplet generation, thermal cycling, imaging. | No |
| `design/hardware.sysml` | Physical parts (ISA-88 equipment): rack, shuttle, gantry, stations, pneumatics, generators, thermal blocks, imagers, stores, cartridge. | No |
| `design/workflow.sysml` | ISA-88 procedure: sample procedure, five unit procedures, operations, phases (Steps) and decisions. | No |
| `design/allocation.sysml` | Abstract `Instrument` (process cell): owns the units, the procedure binding and every `allocate`. | No |
| `design/scenarios.sysml` | Configurations (`BaseInstrument`, `HighThroughputInstrument`) and scenarios (`BaseBatch`, `BaseSteadyStat`, `HighThroughputSteadyStat`). | No |
| `design/verification.sysml` | `satisfy` links to every SYS requirement and one verification case per SYS requirement. | No |

## ISA-88 mapping

| ISA-88 | In this model |
|---|---|
| Process cell | `Instrument` (`allocation.sysml`) |
| Units | Stations, pneumatic controllers, droplet generators, thermal blocks, imagers, and the shared shuttle and gantry |
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

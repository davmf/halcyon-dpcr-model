# Capacity estimate

Hand calculation of steady-state utilisation per resource. Layer 2 of
design verification compares simulation results with these values.
Inputs are the design attributes in `model/design/` (physics, hardware,
workflow, allocation, scenarios). Times are per cartridge, one sample per
cartridge, reflex retests excluded (about 0.001% of samples).

## Derived design values

| Quantity | Value | Source |
|---|---|---|
| Priming time | 28.8 s | `PrimingTime`: 0.1 mm x 0.3 m channel, 2 mPa s, 20 kPa |
| Partition volume per channel | 17 uL | `Cartridge::partitionVolume` |
| Droplets per channel | 20,000 | `DropletCount`, 0.85 nL droplets |
| Droplet generation time | 166.7 s | `DropletGenerationTime`, 120 Hz |
| Thermal run | 2,800 s (46.7 min) | `ThermalRunTime`: 5 min hot start, 40 x (15 s + 30 s + 2 x 35 K / 4 K/s) |
| Imaging per cartridge | 180 s | 4 channels x 45 s |

## Busy time per cartridge

| Resource (capacity) | Busy per cartridge | Units | Capacity per hour, per unit |
|---|---|---|---|
| Shuttle (1) | 150 s (5 moves) | 1 | 24.0 |
| Pipetting gantry (1) | 160 s | 1 | 22.5 |
| Extraction stations (4) | 1,190 s | 4 | 3.0 each, 12.1 in total |
| Pneumatic controllers (2) | 232 s | 2 | 15.5 each, 31.0 in total |
| Droplet generators (2) | 202 s | 2 | 17.8 each, 35.7 in total |
| Thermal block (4 cartridges per run) | 2,800 s per run | 2 or 3 | 5.14 each (4 cartridges per 46.7 min) |
| Imager (1 or 2) | 180 s | 1 or 2 | 20.0 each |

The station figure is the sum of pipetting (60 s), lysis (360 s), bead
binding (180 s), two washes (2 x 150 s, including 20 s gantry dispense),
elution (20 s dispense and 240 s heating), priming (28.8 s) and the
expected re-prime (0.05 x 30 s).

## Scenario results

Offered load 12 samples per hour (96 per 8-hour shift), the SteadyStat
arrival rate.

| Resource | Base: offered load | Base: carried load | HighThroughput: offered load |
|---|---|---|---|
| Thermal blocks | 117% (2 blocks) | 100% (saturated) | 78% (3 blocks) |
| Extraction stations | 99% | 99% | 99% |
| Pipetting gantry | 53% | 53% | 53% |
| Shuttle | 50% | 50% | 50% |
| Pneumatic controllers | 39% | 39% | 39% |
| Droplet generators | 34% | 34% | 34% |
| Imager | 60% (1 imager) | 51% | 30% (2 imagers) |

Maximum sustainable throughput:

- Base: 10.3 per hour, 82 per shift. The thermal blocks are the
  bottleneck. The requirement SYS-THR-001 (96 per shift) fails.
- HighThroughput: 12.1 per hour, 97 per shift. The extraction stations
  are the bottleneck. The requirement passes on paper, but at 99%
  utilisation the queues grow without bound at nominal load. Expect
  SYS-TAT-002 and SYS-TAT-003 to fail there too.

## Other checks

- Time to first result (batch of 24 at shift start, 10-minute batch
  timeout, no queueing): 85 min. Limit 90 min (SYS-TAT-001). Passes with
  a small margin.
- STAT path with no queueing: 85 min. Limit 2 h (SYS-TAT-003). Passes
  only when the system is not queueing. Under load it fails.
- Invalid results after one reflex retest: about 1 in 86,000
  (0.0009 + 0.0025 first-pass invalid rate, squared). Limit 2%
  (SYS-VAL-001). Passes with a wide margin.
- Reagent store: 100 units at 12 per hour lasts 8.3 hours. Limit 8 hours
  (SYS-OPS-001). Passes with a small margin.
- Imager utilisation at offered 12 per hour: 60%. Limit 85% (SYS-UTL-001).
  Passes.

## Open points

- The base configuration cannot meet SYS-THR-001 with the cycle times in
  the brief. The thermal run must take 40 min or less for two blocks to
  reach 96 per shift. The brief asks for about 45 to 60 min.
- With the chosen durations, the extraction stations are the bottleneck
  in HighThroughput. Lowering station time would move the bottleneck back
  to the thermal blocks.
- The waste store has no allocation and no level model in version 1.

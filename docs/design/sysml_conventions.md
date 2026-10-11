# SysML v2 conventions for the Halcyon dPCR-24 model

This file is the contract between three components:

- the StrictDoc SysML format (`strictdoc/backend/sysml/` on the StrictDoc
  branch `david/sysml-format`);
- the Halcyon dPCR-24 model (`model/`);
- the simulation generator (`generator/`).

Every `.sysml` file in `model/` must pass two parsers:

1. the OMG SysML v2 Pilot Implementation (conformance gate);
2. the StrictDoc textX parser for the SysML subset below.

## File roles

| Role | Location | Edited in StrictDoc | Written by |
|---|---|---|---|
| Requirements package | `model/requirements/*.sysml` | Yes | StrictDoc writer, engineers, Claude |
| Design package | `model/design/*.sysml` | No (read only) | Engineers, Claude |
| Simulation library | `model/library/*.sysml` | No (read only) | Engineers, Claude |

StrictDoc decides the role from the content, not the path. A file is a
requirements package when its top-level package contains only:

- nested `package` declarations;
- `doc` comments;
- `private import` / `public import` statements;
- `requirement` usages;
- `dependency` declarations between requirements.

Any other member makes the file a design package, which StrictDoc shows read
only.

## Requirements package: canonical layout

The StrictDoc writer owns this layout. A file written by StrictDoc and read
back must produce the same text (round trip).

```sysml
package 'Halcyon dPCR-24 system requirements' {
    doc /*
     * Free text shown at the top of the document.
     */

    private import ScalarValues::*;

    package 'Throughput' {
        doc /*
         * Section text.
         */

        requirement <'SYS-THR-001'> 'Shift throughput' {
            doc /*
             * The instrument shall complete at least 96 samples
             * in an 8-hour shift.
             */
            attribute requiredSamplesPerShift : Real = 96;
            attribute measuredSamplesPerShift : Real;
            require constraint {
                measuredSamplesPerShift >= requiredSamplesPerShift
            }
        }

        #derivation dependency from 'SYS-THR-001' to 'STK-THR-001';
    }
}
```

Derivation form (settled 2026-10-11): plain `dependency from <child> to
<parent>;` in a requirements package, with the parent imported as
`private import '<stakeholder package>'::**;`. The `#derivation` metadata
prefix passes the Pilot only with `private import RequirementDerivation::*;`,
and its metadata targets connections, so it is not used. Do not use
`#derivation` in requirements packages.

### Mapping to StrictDoc

| StrictDoc | SysML v2 |
|---|---|
| Document | Top-level `package`; title is the package's (quoted) name |
| Document free text | First `doc` comment of the top-level package |
| Section | Nested `package`; title is its name |
| Section free text | First `doc` comment of the nested package |
| Node type `REQUIREMENT` | `requirement` usage |
| `UID` | Short name, e.g. `<'SYS-THR-001'>` |
| `TITLE` | Name, e.g. `'Shift throughput'` |
| `STATEMENT` | First `doc` comment of the requirement |
| Custom field | `attribute <name> [: <Type>] [= <value>];` Field name is the attribute name in upper snake case (`requiredSamplesPerShift` becomes `REQUIRED_SAMPLES_PER_SHIFT`). The value is the literal text after `=` |
| `CONSTRAINT` field | Text inside `require constraint { ... }`, verbatim |
| Parent relation | `dependency from <child> to <parent>;` |
| Child relations to design | `satisfy` and `verify` in design packages |

Doc comment text is the content between `/*` and `*/`, with the leading
` * ` decoration of each line stripped.

## Design packages

Design packages may use any construct from the subset in the next section.
StrictDoc reads them read only and shows these elements as nodes:

- `part def`, `part`
- `action def`, `action`
- `calc def`
- `verification def`, `verification`
- `analysis def`, `analysis`

Each design node has the fields `UID` (the short name if present, otherwise the
qualified name), `TITLE` (the name), `ELEMENT_KIND` (for example `part def`),
`STATEMENT` (the `doc` comment, if any) and `SOURCE` (the element's source text).

Traceability from design to requirements:

- `satisfy '<UID>' by <element>;` gives `<element>` a relation to the
  requirement with role `Satisfies`.
- `verify '<UID>';` inside a verification case's `objective` gives the
  verification case a relation to the requirement with role `Verifies`.

## SysML v2 subset

The subset is plain SysML v2 textual notation. Everything else is outside it.
The StrictDoc parser tolerates unknown members inside a body by skipping them
as balanced `{ ... }` or `...;` text, so a design file that strays outside the
subset still loads.

- Packages: `package`, nested packages, `private import` / `public import`
  with `::*` and `::**`.
- Comments: `doc /* ... */`, `comment /* ... */`, `// line notes`.
- Names: identifiers and quoted names (`'Shift throughput'`), short names
  (`<'SYS-THR-001'>`), qualified names (`A::B::c`).
- Definitions and usages: `part def`, `part`, `item def`, `item`,
  `attribute def`, `attribute`, `action def`, `action`, `calc def`,
  `requirement def`, `requirement`, `constraint def`, `constraint`,
  `analysis def`, `analysis`, `verification def`, `verification`,
  `metadata def`, `enum def`.
- Specialisation and typing: `:`, `:>`, `:>>`, `redefines`, `subsets`.
- Multiplicity: `[n]`, `[n..m]`, `[*]`.
- Variability: `variation part def`, `variant part`.
- Features: `in`, `out`, `inout`, `return`, `subject`, `objective`, `ref`.
- Behaviour: `first <a> then <b>;`, `then <b>;`, `fork`, `join`, `decide`,
  `merge`, `if <expr> then <target>;`, `else <target>;`, `perform`.
- Relationships: `allocate <action> to <part>;`, `satisfy`, `verify`,
  `dependency from ... to ...;`, metadata annotations `#Name` and
  `@Name { ... }`.
- Expressions (for `calc def`, attribute values and constraints): numeric
  literals, units in brackets (`40 [s]`), strings, booleans, `+ - * / ** ^`,
  comparisons, `and or not`, parentheses, feature references, invocation
  `Calc(arg = value, ...)`, conditional `if c ? a else b`.

Added after the Pilot probes (2026-10-11). Each item is used in `model/`:

- Overridable defaults: `attribute x : T default v;`. A value bound with
  `=` in a definition cannot be redefined in a usage ("Cannot override a
  binding feature value").
- Redefinition with a body: `part :>> stations { attribute :>> capacity = 4;
  }`.
- Guarded decisions: `decide d;` then `first d if <expr> then <action>;` and
  `first d if not <expr> then <action>;`. Negation is `not`, not `!`. The
  form `if <expr> then <a>; else <b>;` is rejected by the Pilot and is not
  used.
- Fork and join: `fork f;`, `join j;`, with `first` successions into and
  out of them.
- Invocation in a guard: `first d if Bernoulli(p = pBubble) then a;`.
- Performing an action with bound parameters inside a part definition:
  `perform action run : Proc { in part :>> cart = cartridge; }`, and
  `allocate run.intake.prime to stations;` inside the same definition.
- Dot access to features of usages and of requirements:
  `'SYS-THR-001'.measuredSamplesPerShift`,
  `baseSteady.configuration.cartridge.partitionVolume`. The `::` form fails
  for requirement features ("Must be an accessible feature").
- Short names on definitions: `part def <'HW-CART'> Cartridge { ... }`.
- `satisfy '<UID>' by <usage>;` takes a usage (a part usage, or a dot path
  to one). A definition name fails ("Must be a valid feature").
- Literals with exponents and units: `0.85e-6 [mL]`, `[1/h]`, `[Pa*s]`,
  `[T]`, `[Hz]`, `[min]`, `[mm]`.
- Enum literals must not be keywords. `calc` is reserved, so the step kind
  for calc-based durations is `fixed` (see the library section).
- Repetition is written out, not as a loop. The two washes are four steps.

Units not in the Pilot library, and not used: `µL`, `nL`, `µm`, `kPa`,
`mPa*s`. Use `mL`, `mm`, `Pa`, `Pa*s`, with exponents, for example
`0.85e-6 [mL]`. Temperatures are plain `Real` values in °C, as set points.
The ramp rate is a plain `Real` in K/s. The library has no rate type.

## Simulation library conventions (generator contract)

Library file: `model/library/SimLib.sysml`, package `SimLib`. It is generic.
The generator must not contain Halcyon-specific code. Version 1 shape,
2026-10-11:

| Construct | Kind | Attributes, and meaning for the generator |
|---|---|---|
| `Probability` | attribute def `:> Real` | Branch probability, 0 to 1. |
| `DistributionKind` | enum | `fixed`, `triangular`, `normal`, `logNormal`. |
| `MetricKind` | enum | `completedPerShift`, `timeToFirstResult`, `meanTurnaround`, `meanStatTurnaround`, `invalidRate`, `utilisation`. |
| `Bernoulli` | calc def | `in p : Probability`, `return : Boolean`. A random draw. |
| `Resource` | abstract part def | `capacity : Natural default 1`. The number of identical units. A unit is seized FIFO within equal priority. |
| `BatchResource` | abstract part def `:> Resource` | `batchSize : Natural default 1`, `batchTimeout : DurationValue default 0 [s]`. A batch starts when `batchSize` items wait, or when `batchTimeout` has passed since the first waiting item arrived. Each batch takes up to `batchSize` items. Units run batches in parallel. |
| `Store` | abstract part def | `initialLevel`, `reorderLevel`, `refillSize : Natural default 0`, `refillDuration : DurationValue default 0 [s]`. Level falls when a step allocated to the store starts with `consumes > 0`. At or below `reorderLevel`, one refill of `refillSize` arrives after `refillDuration`. One refill at a time. |
| `WorkItem` | abstract item def | `priority : Natural default 0`. Higher first in every queue. STAT is 1. |
| `Step` | action def | `distribution : DistributionKind default fixed`. `nominal`: the fixed value, the triangular mode, the normal mean, or the log-normal median. A calc invocation in `nominal` gives a fixed value. `low`, `high`: triangular bounds. `sd : DurationValue`: normal standard deviation. `sigma : Real`: log-normal shape (sd of ln duration). `consumes : Natural default 0`. `retest : Boolean default false`. |
| `ArrivalProcess` | abstract attribute def | `statFraction : Probability default 0`. Share of arrivals with priority 1. |
| `BatchArrival` | attribute def `:> ArrivalProcess` | `count : Natural`, `time : DurationValue default 0 [s]`. All items arrive at `time`. |
| `PoissonArrival` | attribute def `:> ArrivalProcess` | `rate : FrequencyValue`, for example `[1/h]`. Exponential inter-arrival times. |
| `Configuration` | abstract part def | `maxRetests : Natural default 1`. Retest steps add a new run of the same item, up to this count. |
| `Scenario` | abstract part def | `arrivals : ArrivalProcess`, `warmUpTime : DurationValue default 0 [h]` (statistics start after it), `part configuration : Configuration`. |
| `SimulationVerification` | verification def | `measured` (untyped; bound to the requirement's measured attribute, for example `'SYS-THR-001'.measuredSamplesPerShift`), `metric : MetricKind`, `horizon : DurationValue default 8 [h]`, `replications : Natural default 10`, `confidence : Probability default 0.95`, `ref part scenario : Scenario`, `ref part resource : Resource [0..1]` (required for `utilisation`). |

Generator rules:

- Units and configuration. A configuration sets a unit count with
  `part :>> stations { attribute :>> capacity = 4; }`. Abstract configurations
  declare parts; concrete ones (`BaseInstrument`) set the counts.
- Allocation. `allocate <step> to <part>;` makes the step seize that
  resource for its duration. A step with several allocations seizes all of
  them together. A step waits until all its resources are free.
- Stores. `allocate <step> to <store>;` does not seize. The step draws
  `consumes` units at its start.
- Steps with no allocation take their duration without resources.
- Duration. Evaluate `nominal` when the step starts, with the feature values
  of the allocated parts and the calc inputs. Sample by `distribution`.
- Decisions. `decide d;` then `first d if <guard> then <target>;`. A guard
  of `Bernoulli(p = x)` draws a random branch. Guards that are not
  `Bernoulli` read item or part features.
- Retest. A step with `retest = true` ends the run. It adds one new run of the
  same item, if the item has fewer than `maxRetests` retests. The new run
  starts from the top of the procedure.
- Priority. Queues order by `WorkItem::priority` (higher first), then by
  arrival time.
- Verification. For `SimulationVerification`, run `replications` runs of
  `horizon` after `warmUpTime`. Take the mean of the metric and its
  `confidence` bound. For a constraint `measured >= required` use the lower
  bound. For `<=` use the upper bound. Then evaluate the requirement's
  `require constraint`.

Design-side conventions that the generator reads:

- A `verification def ModelCheck` (design package, not in SimLib) holds
  `observed` only. The generator does not run it. The conformance and
  StrictDoc tools read its `verify` relation.
- Retest and abort steps are ordinary `Step`s with `retest = true`.

## Change log

Each entry gives the date, what changed, and why.

- 2026-10-11, derivation: `#derivation` replaced by a plain
  `dependency from <child> to <parent>;`. The metadata form passes the Pilot
  only with an extra library import, and it targets connections.
- 2026-10-11, units: `µL`, `nL`, `µm`, `kPa`, `mPa*s` are not in the Pilot
  library. The model uses `mL`, `mm`, `Pa`, `Pa*s` with exponents. The
  ramp rate and temperatures are `Real`, because no quantity type fits.
- 2026-10-11, decisions: the `if ... then ...; else ...;` form is rejected.
  Guarded `first d if <expr> then <target>;` is used instead. Negation is
  `not`.
- 2026-10-11, references: `::` on requirement features fails. Dot access is
  used (`'SYS-THR-001'.measuredX`). `satisfy ... by` takes a usage, not a
  definition.
- 2026-10-11, defaults: a bound `=` cannot be redefined. Overridable values
  use `default` in SimLib and in the design.
- 2026-10-11, SimLib: `calc` is a keyword, so the enum value is not used.
  Added `Step::retest` and `Configuration::maxRetests`, so the generator does
  not match step names. `measured` in `SimulationVerification` is untyped,
  because the requirement attributes are `DurationValue` and `Real`.
- 2026-10-11, pools: a pool of identical units is one part with a
  `capacity`, not a multiplicity part. This keeps attribute reads and
  allocations single-valued. Multiplicity is not used for pools.
- 2026-10-11, loops: the two washes are written out as four steps. No loop
  construct is used.
- 2026-10-11, short names: short names are allowed on definitions, for
  example `part def <'HW-CART'> Cartridge`.

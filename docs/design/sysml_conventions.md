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

Exact derivation syntax is settled against the Pilot Implementation. If
`#derivation` is not available without extra library imports, use a plain
`dependency from ... to ...;`.

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

## Simulation library conventions (generator contract)

The generator is generic. It must not contain Halcyon-specific code. It reads
any model that uses `model/library/SimLib.sysml`. The model and generator
agents define SimLib together, keeping it small, and record the final shape
here.

Principles:

- Resources are parts that specialise `SimLib::Resource` (servers =
  `capacity`), `SimLib::BatchResource` (`batchSize`, `batchTimeout`) or
  `SimLib::Store` (consumable level, refill).
- Steps are actions that specialise `SimLib::Step` and carry a duration
  specification: fixed, triangular, normal or log-normal, or a `calc def`
  invocation over part attributes (step physics).
- `allocate <step> to <part>;` means the step seizes that resource for its
  duration. A step with several allocations seizes all of them.
- Control flow uses successions, fork/join and decide/merge. Branch
  probabilities are attributes typed `SimLib::Probability`.
- Work items (samples) are `item def`s with a priority attribute.
- Scenarios are variants of a configuration part plus an arrival process.
- Thresholds live in requirements only. A verification case binds a
  requirement's measured attribute to a simulation metric and names the
  scenario, replications and horizon. The generator evaluates the
  requirement's `require constraint` with the metric's confidence bound.

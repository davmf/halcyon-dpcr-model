# Tracker layout: one SysML file per item

The model is split the way Codebeamer organises a project: trackers at the
first level, folders inside trackers, and items. Each item is a separate
`.sysml` file, so Git history is item history. StrictDoc (fork) reads the
layout as one document per tracker; PlantUML (`!include_sysml`) and the OMG
Pilot read the files as one model.

`tools/split_to_trackers.py` converted the old layout (one file per package).

## Files

```
model/
  model.sysml                 model root: lists the trackers
  _library/                   SimLib, StrictDocWorkspace (metadata), profiles
  TRK-<X>/TRK-<X>.sysml       tracker
  TRK-<X>/<FOLDER-ID>.sysml   folder
  TRK-<X>/<ITEM-ID>.sysml     item
  TRK-<X>/_assets/            images used by the items' doc comments
```

The directory is only for tidiness. The import lines decide the tree and
its order.

## Rules

1. **Every top-level name is an ID.** A file holds exactly one top-level
   package, named by the ID of what it holds: `'MODEL'`, `'TRK-SYS'`,
   `'SYS-F-THROUGHPUT'`, `'SYS-THR-001'`. The file name is the ID.
   - The Pilot resolves a name across files only for top-level declared
     names, not short names.
   - Two files with the same top-level name give **no** Pilot error (one of
     them wins silently), so the tools must check that IDs are unique.
2. **A parent includes a child with `public import '<CHILD-ID>'::*;`.** The
   model root imports trackers as memberships (`public import 'TRK-SYS';`).
   Trackers and folders re-export their items, so `private import
   'TRK-SYS'::*;` (or `::**`) gives a file every element of the tracker.
3. **An item package holds one element** and the traces it is the client
   of: `dependency from <item> to ...`, `satisfy ... by <item>[.path]`.
   A trace change is a change of the client item.
4. **Item IDs** are the element's short name when it has one
   (`SYS-THR-001`, `HW-CART`), else the tracker prefix and the next number
   (`SC-001`). Names such as `baseBatch` and `BaseBatch` differ only by
   case, so they cannot be file names.
5. **Item imports**: the imports of the old package, its own tracker
   (`private import 'TRK-HW'::*;` for sibling items), and the tracker of
   each trace supplier. `#derivation` needs
   `private import RequirementDerivation::*;`.
6. A reference by ID inside an item (`'SYS-THR-001'.measuredSamplesPerShift`,
   `expose 'SM-001'::top::...`) resolves to the element, not to its item
   package, because imports are searched before the global scope.

## Metadata (`_library/StrictDocWorkspace.sysml`)

| Metadata | On | Attributes |
|---|---|---|
| `Model` | model root | `title` |
| `Tracker` | tracker package | `title`, `kind` (requirements, test cases, design, behaviour...), `prefix` |
| `Folder` | folder package | `title` |
| `DiagramView` | a `view` item | `options` (`!include_sysml` options), `plantuml` (lines added after the directive) |

```
package 'TRK-SYS' {
    @StrictDocWorkspace::Tracker { title = "System requirements"; kind = "requirements"; prefix = "SYS"; }
    doc /* ... */
    public import 'SYS-F-THROUGHPUT'::*;
}

package 'SYS-THR-001' {
    private import ScalarValues::*;
    private import 'TRK-STK'::**;
    private import 'TRK-SYS'::*;

    requirement <'SYS-THR-001'> 'Shift throughput' { ... }

    dependency from 'SYS-THR-001' to 'STK-THR-001';
}
```

## Views (saved diagrams)

A view is an item of its own. It exposes the item it draws, so one state
machine can have several views:

```
package 'VIEW-002' {
    private import 'TRK-BEH'::*;

    view <'VIEW-002'> 'Inside composite state 1' {
        @StrictDocWorkspace::DiagramView { options = "regions=vertical"; plantuml = "note right of newState1 : reviewed"; }
        expose 'SM-001'::top::newCompositeState1::**;
    }
}
```

## Checked (2026-11-12, Phase 0)

| Check | Result |
|---|---|
| Pilot 0.62.0, the 91 converted files | 0 errors |
| Pilot, a state machine item (StateMachineProfile) and two view items | 0 errors; a wrong `expose` path is an error |
| Generator tests (`pytest`, without the slow conformance tests) | 20 passed: same graph, scenarios and verification IDs |
| PlantUML `!include_sysml view=requirements`, old vs new layout | identical boxes and links |
| PlantUML, state machine item, `actions=false`, `regions=vertical` | drawn |
| StrictDoc parser, every file | parses (one document per file until the tracker reader exists) |

Open: StrictDoc's parser rejects `library package` (the profiles); PlantUML
does not yet draw a `view` item (`diagram=<VIEW-ID>`).

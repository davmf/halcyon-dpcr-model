"""Split the Halcyon model into the tracker layout: one .sysml file per item.

One-off migration (Phase 0 of the StrictDoc tracker workspace). StrictDoc
gets a general `split` command later; this script only handles the
constructs of this model.

Layout written to OUT (default: model/):

    model.sysml                  model root, imports each tracker package
    _library/SimLib.sysml        unchanged
    _library/StrictDocWorkspace.sysml
    <TRACKER-ID>/<TRACKER-ID>.sysml   tracker: title metadata, doc, imports
    <TRACKER-ID>/<FOLDER-ID>.sysml    folder (a nested package)
    <TRACKER-ID>/<ITEM-ID>.sysml      item: package '<ITEM-ID>' { element }

Every top-level name is an ID: the Pilot resolves names across files only
for top-level declared names, and two files with the same top-level name
give no error. A parent includes a child with `public import '<ID>'::*;`.
An item file holds the element and the traces it is the client of
(`dependency from <item>`, `satisfy ... by <item>...`).

Text is copied, not regenerated: the element keeps its comments and layout,
re-indented to sit in its item package.

Usage: python tools/split_to_trackers.py [--out DIR]
"""

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "model"

# Source file -> (tracker ID, title, kind, ID prefix)
TRACKERS = [
    ("requirements/stakeholder_requirements.sysml", "TRK-STK", "Stakeholder requirements", "requirements", "STK"),
    ("requirements/system_requirements.sysml", "TRK-SYS", "System requirements", "requirements", "SYS"),
    ("design/physics.sysml", "TRK-PHY", "Physics", "design", "PHY"),
    ("design/hardware.sysml", "TRK-HW", "Hardware", "design", "HW"),
    ("design/workflow.sysml", "TRK-WF", "Workflow", "design", "WF"),
    ("design/allocation.sysml", "TRK-AL", "Allocation", "design", "AL"),
    ("design/scenarios.sysml", "TRK-SC", "Scenarios", "design", "SC"),
    ("design/verification.sysml", "TRK-VER", "Verification", "test cases", "VER"),
]

MODEL_ID = "MODEL"
MODEL_TITLE = "Halcyon dPCR-24"

WORKSPACE_LIBRARY = """\
package StrictDocWorkspace {
    doc /*
     * Metadata of the StrictDoc tracker layout. A model root lists its
     * trackers, a tracker or a folder lists its folders and items, each
     * with `public import '<ID>'::*;`. Every top-level package name is an ID.
     */

    private import ScalarValues::*;

    metadata def Model {
        attribute title : String;
    }

    metadata def Tracker {
        doc /* kind: requirements, test cases, design, behaviour... */
        attribute title : String;
        attribute kind : String;
        attribute prefix : String;
    }

    metadata def Folder {
        attribute title : String;
    }

    metadata def DiagramView {
        doc /*
         * On a view item: the !include_sysml options of the diagram and
         * PlantUML lines added after the directive (notes, styles).
         */
        attribute options : String;
        attribute plantuml : String;
    }
}
"""


# ---------------------------------------------------------------- scanning


@dataclass
class Statement:
    """A member of a package body, as written (without leading indentation)."""

    text: str
    indent: int


def _skip_comment_or_string(text: str, i: int) -> int:
    """If text[i] starts a comment or a string, return the index after it."""
    if text.startswith("/*", i):
        end = text.index("*/", i + 2)
        return end + 2
    if text.startswith("//", i):
        end = text.find("\n", i)
        return len(text) if end < 0 else end
    if text[i] in "'\"":
        quote = text[i]
        j = i + 1
        while text[j] != quote:
            j += 2 if text[j] == "\\" else 1
        return j + 1
    return i


def split_body(body: str) -> list[Statement]:
    """Split a package body into statements ending at `;` or a closing `}`."""
    result: list[Statement] = []
    i = 0
    n = len(body)
    while i < n:
        while i < n and body[i].isspace():
            i += 1
        if i >= n:
            break
        line_start = body.rfind("\n", 0, i) + 1
        indent = i - line_start
        start = i
        depth = 0
        # `doc /* ... */` ends at its comment
        if re.match(r"doc\b", body[i:]):
            i = body.index("*/", i) + 2
            result.append(Statement(body[start:i], indent))
            continue
        while i < n:
            j = _skip_comment_or_string(body, i)
            if j != i:
                i = j
                continue
            c = body[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            elif c == ";" and depth == 0:
                i += 1
                break
            i += 1
        result.append(Statement(body[start:i], indent))
    return result


def package_parts(text: str) -> tuple[str, str]:
    """`package Name { body }` -> (name, body)."""
    m = re.match(r"\s*package\s+('(?:[^'\\]|\\.)*'|\w+)\s*\{", text)
    if m is None:
        raise ValueError("not a package: " + text[:60])
    close = text.rindex("}")
    return m.group(1), text[m.end():close]


def unquote(name: str) -> str:
    return name[1:-1] if name.startswith("'") else name


def quote(name: str) -> str:
    return name if re.fullmatch(r"[A-Za-z_]\w*", name) else "'" + name + "'"


ELEMENT_RE = re.compile(
    r"^(?:#\w+\s+)*(?:(?:abstract|variation|individual|ref)\s+)*"
    r"(?:[a-z]+\s+)+?(?:def\s+)?"
    r"(?:<('(?:[^'\\]|\\.)*'|\w+)>\s*)?"
    r"('(?:[^'\\]|\\.)*'|[A-Za-z_]\w*)"
)


def element_names(text: str) -> tuple[str | None, str]:
    m = ELEMENT_RE.match(text)
    if m is None:
        raise ValueError("cannot read the name of: " + text[:80])
    short = unquote(m.group(1)) if m.group(1) else None
    return short, unquote(m.group(2))


def reindent(stmt: Statement, indent: int) -> str:
    """Move a statement from its indentation to `indent` spaces."""
    lines = stmt.text.split("\n")
    out = [" " * indent + lines[0]]
    shift = indent - stmt.indent
    for line in lines[1:]:
        if not line.strip():
            out.append("")
        elif shift >= 0:
            out.append(" " * shift + line)
        else:
            cut = min(-shift, len(line) - len(line.lstrip(" ")))
            out.append(line[cut:])
    return "\n".join(out)


def slug(title: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").upper()


# ---------------------------------------------------------------- model


@dataclass
class Item:
    id: str
    name: str
    element: Statement
    tracker: "Tracker"
    traces: list[Statement] = field(default_factory=list)
    extra_imports: set[str] = field(default_factory=set)


@dataclass
class Folder:
    id: str
    title: str
    doc: Statement | None
    children: list[object] = field(default_factory=list)  # Folder | Item


@dataclass
class Tracker:
    id: str
    title: str
    kind: str
    prefix: str
    source_name: str
    doc: Statement | None = None
    imports: list[Statement] = field(default_factory=list)
    children: list[object] = field(default_factory=list)
    pending_traces: list[Statement] = field(default_factory=list)
    counter: int = 0


def read_tracker(path: Path, tracker: Tracker, items: dict[str, Item]) -> None:
    name, body = package_parts(path.read_text(encoding="utf-8"))
    tracker.source_name = unquote(name)
    read_members(split_body(body), tracker, tracker.children, items, top=True)


def read_members(statements, tracker, children, items, top) -> Statement | None:
    doc = None
    for s in statements:
        t = s.text
        if t.startswith("doc"):
            if doc is None:
                doc = s
        elif re.match(r"(private|public)\s+import\b", t):
            if not top:
                raise ValueError("import in a nested package is not handled: " + t)
            tracker.imports.append(s)
        elif t.startswith("package"):
            fname, fbody = package_parts(t)
            title = unquote(fname)
            folder = Folder(tracker.prefix + "-F-" + slug(title), title, None)
            folder.doc = read_members(split_body(fbody), tracker, folder.children, items, top=False)
            children.append(folder)
        elif re.match(r"(#\w+\s+)*(dependency|satisfy)\b", t):
            tracker.pending_traces.append(s)
        else:
            short, ename = element_names(t)
            # Items without a short name get the next number of the tracker:
            # names such as baseBatch and BaseBatch differ only by case.
            if short is None:
                tracker.counter += 1
            item_id = short or f"{tracker.prefix}-{tracker.counter:03d}"
            if item_id in items:
                raise ValueError("duplicate item ID " + item_id)
            item = Item(item_id, ename, s, tracker)
            items[item_id] = item
            children.append(item)
    if top:
        tracker.doc = doc
    return doc


def trace_client(stmt: Statement, items: dict[str, Item]) -> Item:
    t = stmt.text
    m = re.search(r"dependency\s+(?:\w+\s+)?from\s+('(?:[^'\\]|\\.)*'|[\w.]+)", t)
    if m is None:
        m = re.search(r"\bby\s+('(?:[^'\\]|\\.)*'|\w+)", t)
    if m is None:
        raise ValueError("trace without a client: " + t)
    ref = unquote(m.group(1)).split(".")[0]
    for item in items.values():
        if item.id == ref or item.name == ref:
            return item
    raise ValueError("trace client is not an item: " + t)


def trace_supplier_tracker(stmt: Statement, items: dict[str, Item]) -> str | None:
    t = stmt.text
    m = re.search(r"\bto\s+('(?:[^'\\]|\\.)*'|\w+)", t) or re.search(
        r"satisfy\s+(?:requirement\s+)?('(?:[^'\\]|\\.)*'|\w+)", t
    )
    if m is None:
        return None
    ref = unquote(m.group(1))
    for item in items.values():
        if item.id == ref or item.name == ref:
            return item.tracker.id
    return None


# ---------------------------------------------------------------- writing

def import_lines(tracker: Tracker, renames: dict[str, str], extra: set[str], own: bool) -> list[str]:
    lines = []
    for s in tracker.imports:
        text = s.text
        for old, new in renames.items():
            text = re.sub(r"(import\s+)" + re.escape(old) + r"(?=::)", r"\1" + new, text)
        lines.append("    " + text)
    wanted = set(extra)
    if own:
        wanted.add(tracker.id)
    already = " ".join(lines)
    for tid in sorted(wanted):
        if "'" + tid + "'::" not in already:
            lines.append(f"    private import '{tid}'::*;")
    return lines


def write_item(item: Item, out: Path, renames: dict[str, str]) -> None:
    parts = [f"package '{item.id}' {{"]
    parts += import_lines(item.tracker, renames, item.extra_imports, own=True)
    if any("#derivation" in t.text for t in item.traces):
        parts.append("    private import RequirementDerivation::*;")
    parts.append("")
    parts.append(reindent(item.element, 4))
    if item.traces:
        parts.append("")
        parts += [reindent(t, 4) for t in item.traces]
    parts.append("}")
    (out / item.tracker.id / (item.id + ".sysml")).write_text("\n".join(parts) + "\n", encoding="utf-8")


def child_imports(children) -> list[str]:
    return [f"    public import '{c.id}'::*;" for c in children]


def write_folder(folder: Folder, tracker: Tracker, out: Path, renames) -> None:
    parts = [f"package '{folder.id}' {{"]
    parts.append(f'    @StrictDocWorkspace::Folder {{ title = "{folder.title}"; }}')
    if folder.doc is not None:
        parts.append(reindent(folder.doc, 4))
    parts.append("")
    parts += child_imports(folder.children)
    parts.append("}")
    (out / tracker.id / (folder.id + ".sysml")).write_text("\n".join(parts) + "\n", encoding="utf-8")
    for c in folder.children:
        if isinstance(c, Folder):
            write_folder(c, tracker, out, renames)
        else:
            write_item(c, out, renames)


def write_tracker(tracker: Tracker, out: Path, renames) -> None:
    (out / tracker.id).mkdir(parents=True, exist_ok=True)
    parts = [f"package '{tracker.id}' {{"]
    parts.append(
        f'    @StrictDocWorkspace::Tracker {{ title = "{tracker.title}"; '
        f'kind = "{tracker.kind}"; prefix = "{tracker.prefix}"; }}'
    )
    if tracker.doc is not None:
        parts.append(reindent(tracker.doc, 4))
    parts.append("")
    parts += child_imports(tracker.children)
    parts.append("}")
    (out / tracker.id / (tracker.id + ".sysml")).write_text("\n".join(parts) + "\n", encoding="utf-8")
    for c in tracker.children:
        if isinstance(c, Folder):
            write_folder(c, tracker, out, renames)
        else:
            write_item(c, out, renames)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=SRC)
    args = parser.parse_args()
    out: Path = args.out

    items: dict[str, Item] = {}
    trackers: list[Tracker] = []
    for source, tid, title, kind, prefix in TRACKERS:
        tracker = Tracker(tid, title, kind, prefix, "")
        read_tracker(SRC / source, tracker, items)
        trackers.append(tracker)
    renames = {quote(t.source_name): f"'{t.id}'" for t in trackers}

    for tracker in trackers:
        for stmt in tracker.pending_traces:
            client = trace_client(stmt, items)
            client.traces.append(stmt)
            supplier = trace_supplier_tracker(stmt, items)
            if supplier is not None and supplier != client.tracker.id:
                client.extra_imports.add(supplier)

    staging = out.with_name(out.name + ".new")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    (staging / "_library").mkdir()
    shutil.copy(SRC / "library" / "SimLib.sysml", staging / "_library" / "SimLib.sysml")
    (staging / "_library" / "StrictDocWorkspace.sysml").write_text(WORKSPACE_LIBRARY, encoding="utf-8")
    for tracker in trackers:
        write_tracker(tracker, staging, renames)
    root = [f"package '{MODEL_ID}' {{", f'    @StrictDocWorkspace::Model {{ title = "{MODEL_TITLE}"; }}', ""]
    root += [f"    public import '{t.id}';" for t in trackers]
    root.append("}")
    (staging / "model.sysml").write_text("\n".join(root) + "\n", encoding="utf-8")

    # Keep the assets and README of the old layout next to the new files.
    for extra in ("README.md",):
        if (SRC / extra).exists():
            shutil.copy(SRC / extra, staging / extra)
    assets = SRC / "requirements" / "_assets"
    if assets.exists():
        shutil.copytree(assets, staging / "TRK-SYS" / "_assets")

    if out.exists():
        shutil.rmtree(out)
    staging.rename(out)
    count = len(list(out.rglob("*.sysml")))
    print(f"{len(trackers)} trackers, {len(items)} items, {count} files in {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

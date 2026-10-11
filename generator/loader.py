"""
SysML model to IR.

Reads every `.sysml` file under a model directory with the StrictDoc parser
(`strictdoc.backend.sysml.parser.SysMLParser`), then builds a Model:

- Definitions are looked up by name, and inherited through `:>` and `:`.
- A configuration is expanded from its part definition: attributes and parts,
  with redefinitions (`:>>`) applied on top of the supertype.
- Scenarios are part usages typed by a definition that specialises `Scenario`.
- The procedure is the action definition named in a `perform` of the
  configuration. Its steps, decisions, forks and merges form the graph. Groups
  are flattened: the entry of a group follows the group's predecessor, and
  its exit leads to the successor.
- Allocations of the configuration bind steps to resources. A resource's kind
  comes from its supertype (`Resource`, `BatchResource`, `Store`).
- Verifications are `SimulationVerification` usages with a `measured`
  feature reference, a metric, a scenario and optionally a resource.

Nothing here is Halcyon-specific. Names come from the model. Units are
converted to SI with UNIT_FACTORS. An unknown unit is an error.

Known limit: the model has no assignment that sets `sample.invalid`, so the
loaded model never marks a sample invalid. See docs/design/working_notes.md.
"""

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from strictdoc.backend.sysml.expression import (
    BinaryOperation,
    BooleanLiteral,
    Conditional,
    Expression,
    FeatureReference,
    Invocation,
    NumberLiteral,
    StringLiteral,
    UnaryOperation,
    parse_expression,
)
from strictdoc.backend.sysml.model import (
    SysMLAllocate,
    SysMLAttribute,
    SysMLBehaviourControl,
    SysMLElement,
    SysMLMember,
    SysMLPackage,
    SysMLSuccession,
    SysMLVerify,
)
from strictdoc.backend.sysml.parser import SysMLParser

from generator import ir

UNIT_FACTORS: dict[str, float] = {
    "s": 1.0,
    "min": 60.0,
    "h": 3600.0,
    "m": 1.0,
    "mm": 1e-3,
    "mL": 1e-6,
    "Pa": 1.0,
    "Pa*s": 1.0,
    "T": 1.0,
    "Hz": 1.0,
    "1/h": 1.0 / 3600.0,
    "1/s": 1.0,
    "K": 1.0,
    "K/s": 1.0,
    "W": 1.0,
}

# SimLib convention: STAT work items have priority 1. The model does not
# state it, so the loader uses the convention from SimLib's change log.
STAT_PRIORITY = 1

RESOURCE_ROOT_KINDS: dict[str, ir.ResourceKind] = {
    "BatchResource": ir.ResourceKind.BATCH,
    "Store": ir.ResourceKind.STORE,
    "Resource": ir.ResourceKind.UNIT,
}


class LoaderError(Exception):
    """The model cannot be turned into IR."""


def model_files(model_dir: Path) -> list[Path]:
    return sorted(model_dir.rglob("*.sysml"))


def parse_model(model_dir: Path) -> list[SysMLPackage]:
    """Parse every SysML file. Returns the top-level packages."""
    packages: list[SysMLPackage] = []
    for path in model_files(model_dir):
        parsed = SysMLParser.parse_file(str(path))
        for member in parsed.members:
            if isinstance(member, SysMLPackage):
                packages.append(member)
    return packages


def _walk(members: Sequence[SysMLMember]) -> Iterator[SysMLMember]:
    for member in members:
        yield member
        if isinstance(member, (SysMLPackage, SysMLElement)):
            yield from _walk(member.members)


def _package_members(package: SysMLPackage) -> Iterator[SysMLMember]:
    """Members of a package, including nested packages, not element bodies."""
    for member in package.members:
        yield member
        if isinstance(member, SysMLPackage):
            yield from _package_members(member)


def _simple_name(qualified: str) -> str:
    return qualified.split("::")[-1]


def _feature_key(member: object) -> str | None:
    """The name a feature is known by: its name, or what it redefines."""
    name = getattr(member, "name", None)
    if name:
        return str(name)
    redefines = getattr(member, "redefines", None) or []
    if redefines:
        return str(redefines[0])
    return None


def _unit_factor(unit: str | None) -> float:
    if unit is None:
        return 1.0
    if unit not in UNIT_FACTORS:
        raise LoaderError(f"unit not in the SI table: {unit!r}")
    return UNIT_FACTORS[unit]


@dataclass
class _Instance:
    """An expanded configuration or part: attributes, parts and bindings."""

    type_name: str | None
    attributes: dict[str, tuple[Expression, str | None]] = field(
        default_factory=dict
    )
    children: dict[str, _Instance] = field(default_factory=dict)
    allocations: list[SysMLAllocate] = field(default_factory=list)
    performs: list[SysMLElement] = field(default_factory=list)

    def copy(self) -> _Instance:
        return _Instance(
            type_name=self.type_name,
            attributes=dict(self.attributes),
            children={k: v.copy() for k, v in self.children.items()},
            allocations=list(self.allocations),
            performs=list(self.performs),
        )


class _Definitions:
    """Definitions by simple name, with supertype lookup."""

    def __init__(self, packages: Sequence[SysMLPackage]) -> None:
        self.by_name: dict[str, SysMLElement] = {}
        for member in _walk(list(packages)):
            if (
                isinstance(member, SysMLElement)
                and member.is_definition
                and member.name
            ):
                if member.name in self.by_name:
                    raise LoaderError(f"duplicate definition: {member.name}")
                self.by_name[member.name] = member

    def get(self, name: str) -> SysMLElement | None:
        return self.by_name.get(_simple_name(name))

    def supertypes(self, definition: SysMLElement) -> list[str]:
        return [
            _simple_name(target)
            for spec in definition.specializations
            if spec.operator in (":>", ":")
            for target in spec.targets
        ]

    def chain(self, name: str) -> list[str]:
        """The definition name and all its supertypes, nearest first."""
        seen: list[str] = []
        pending = [name]
        while pending:
            current = pending.pop(0)
            if current in seen:
                continue
            seen.append(current)
            definition = self.get(current)
            if definition is not None:
                pending.extend(self.supertypes(definition))
        return seen

    def is_a(self, name: str, base: str) -> bool:
        return base in self.chain(name)


class _Expander:
    """Expands definitions and usages into _Instance trees."""

    def __init__(self, definitions: _Definitions) -> None:
        self.definitions = definitions

    def expand_type(self, type_name: str | None) -> _Instance:
        if type_name is None:
            return _Instance(type_name=None)
        definition = self.definitions.get(type_name)
        if definition is None:
            return _Instance(type_name=_simple_name(type_name))
        instance = _Instance(type_name=definition.name)
        for supertype in self.definitions.supertypes(definition):
            base = self.expand_type(supertype)
            instance = _merge_base(instance, base)
        for member in definition.members:
            self.apply_member(instance, member)
        return instance

    def expand_usage(
        self,
        element: SysMLElement,
        base: _Instance | None,
    ) -> _Instance:
        type_name = _type_of(element)
        if base is None:
            instance = self.expand_type(type_name)
        else:
            instance = base.copy()
            if type_name is not None:
                instance.type_name = _simple_name(type_name)
        for member in element.members:
            self.apply_member(instance, member)
        return instance

    def apply_member(self, instance: _Instance, member: SysMLMember) -> None:
        if isinstance(member, SysMLAttribute):
            key = _feature_key(member)
            if key is None:
                return
            value = member.value or member.default_value
            if value is not None:
                instance.attributes[key] = (value, member.units)
            return
        if isinstance(member, SysMLElement):
            self._apply_element(instance, member)
            return
        if isinstance(member, SysMLAllocate):
            instance.allocations.append(member)
            return

    def _apply_element(
        self,
        instance: _Instance,
        element: SysMLElement,
    ) -> None:
        if element.kind == "attribute":
            key = _feature_key(element)
            if key is not None and element.value is not None:
                instance.attributes[key] = (element.value, None)
            return
        if element.kind == "part":
            key = _feature_key(element)
            if key is None:
                return
            base = instance.children.get(key)
            instance.children[key] = self.expand_usage(element, base)
            return
        if element.kind == "action" and "perform" in element.modifiers:
            instance.performs.append(element)


def _merge_base(instance: _Instance, base: _Instance) -> _Instance:
    merged = _Instance(type_name=instance.type_name)
    merged.attributes = {**base.attributes, **instance.attributes}
    merged.children = {k: v.copy() for k, v in base.children.items()}
    merged.children.update(instance.children)
    merged.allocations = base.allocations + instance.allocations
    merged.performs = base.performs + instance.performs
    return merged


def _type_of(element: SysMLElement) -> str | None:
    for spec in element.specializations:
        if spec.operator == ":" and spec.targets:
            return _simple_name(spec.targets[0])
    return None


class _Converter:
    """Converts SysML expressions to IR expressions."""

    def __init__(
        self,
        rename: Callable[[list[str]], str],
        calc_parameters: dict[str, list[str]],
    ) -> None:
        self.rename = rename
        self.calc_parameters = calc_parameters

    def convert(
        self,
        expression: Expression,
        default_unit: str | None = None,
    ) -> ir.Expr:
        if isinstance(expression, NumberLiteral):
            unit = expression.unit or default_unit
            return ir.Literal(expression.value * _unit_factor(unit))
        if isinstance(expression, BooleanLiteral):
            return ir.Literal(1.0 if expression.value else 0.0)
        if isinstance(expression, StringLiteral):
            raise LoaderError("string values are not supported")
        if isinstance(expression, FeatureReference):
            path = expression.path or [expression.name]
            return ir.Ref(self.rename(path))
        if isinstance(expression, UnaryOperation):
            return ir.Unary(
                expression.operator,
                self.convert(expression.operand),
            )
        if isinstance(expression, BinaryOperation):
            return ir.Binary(
                expression.operator,
                self.convert(expression.left),
                self.convert(expression.right),
            )
        if isinstance(expression, Conditional):
            return ir.Conditional(
                self.convert(expression.condition),
                self.convert(expression.consequence),
                self.convert(expression.alternative),
            )
        if isinstance(expression, Invocation):
            return self._invocation(expression)
        raise LoaderError(f"unsupported expression: {expression!r}")

    def _invocation(self, invocation: Invocation) -> ir.Expr:
        callee = _simple_name(invocation.callee)
        parameters = self.calc_parameters.get(callee)
        arguments: list[tuple[str, ir.Expr]] = []
        for position, argument in enumerate(invocation.arguments):
            name = argument.name
            if name is None:
                if parameters is None or position >= len(parameters):
                    raise LoaderError(f"cannot bind argument of {callee}")
                name = parameters[position]
            arguments.append((name, self.convert(argument.value)))
        return ir.Call(callee, tuple(sorted(arguments)))


def _attribute_value(
    value: tuple[Expression, str | None],
    converter: _Converter,
) -> ir.Expr:
    expression, unit = value
    return converter.convert(expression, default_unit=unit)


def _evaluate_constant(
    expression: ir.Expr,
    calcs: dict[str, ir.CalcDef],
) -> float | None:
    try:
        return ir.evaluate(expression, {}, calcs)
    except ir.ExpressionError:
        return None


def _flatten(
    instance: _Instance,
    prefix: str,
    calcs: dict[str, ir.CalcDef],
    converter: _Converter,
    values: dict[str, float],
) -> None:
    for key, value in instance.attributes.items():
        expression = _attribute_value(value, converter)
        constant = _evaluate_constant(expression, calcs)
        if constant is not None:
            values[f"{prefix}{key}"] = constant
    for key, child in instance.children.items():
        _flatten(child, f"{prefix}{key}.", calcs, converter, values)


def _renamer(bindings: dict[str, str]) -> Callable[[list[str]], str]:
    """Rewrite a path that starts with a bound procedure parameter."""

    def rename(path: list[str]) -> str:
        head, rest = path[0], path[1:]
        if head in bindings:
            return ".".join([bindings[head], *rest])
        return ".".join(path)

    return rename


def _feature_paths(expression: Expression) -> list[list[str]]:
    """Every feature reference path in an expression, in order."""
    if isinstance(expression, FeatureReference):
        return [expression.path or [expression.name]]
    if isinstance(expression, UnaryOperation):
        return _feature_paths(expression.operand)
    if isinstance(expression, BinaryOperation):
        return _feature_paths(expression.left) + _feature_paths(
            expression.right
        )
    if isinstance(expression, Conditional):
        return (
            _feature_paths(expression.condition)
            + _feature_paths(expression.consequence)
            + _feature_paths(expression.alternative)
        )
    if isinstance(expression, Invocation):
        paths: list[list[str]] = []
        for argument in expression.arguments:
            paths += _feature_paths(argument.value)
        return paths
    return []


def _scenario_of(expression: Expression, scenarios: set[str]) -> str:
    for path in _feature_paths(expression):
        if path[0] in scenarios:
            return path[0]
    # A literal observed value names no scenario. Any scenario will do,
    # because the value does not depend on the configuration.
    return next(iter(sorted(scenarios)))


def _scenario_renamer(scenario: str) -> Callable[[list[str]], str]:
    """Paths `<scenario>.configuration.x` become `x`, the configuration key."""

    def rename(path: list[str]) -> str:
        rest = path[1:] if path[0] == scenario else path
        if rest and rest[0] == "configuration":
            rest = rest[1:]
        return ".".join(rest)

    return rename


def _allocation_map(
    allocations: Sequence[SysMLAllocate],
) -> dict[str, list[str]]:
    """Resources of each step, from the allocate statements."""
    result: dict[str, list[str]] = {}
    for allocate in allocations:
        step = allocate.source_path[-1]
        resource = allocate.target_path[-1]
        targets = result.setdefault(step, [])
        if resource not in targets:
            targets.append(resource)
    return result


def _resource_kind(
    definitions: _Definitions,
    type_name: str | None,
) -> ir.ResourceKind | None:
    if type_name is None:
        return None
    for base, kind in RESOURCE_ROOT_KINDS.items():
        if definitions.is_a(type_name, base):
            return kind
    return None


class ModelLoader:
    """Builds a Model from parsed packages."""

    def __init__(self, packages: Sequence[SysMLPackage]) -> None:
        self.packages = list(packages)
        self.definitions = _Definitions(self.packages)
        self.expander = _Expander(self.definitions)
        self.calcs = self._load_calcs()
        self.calc_parameters = {
            name: list(calc.parameters) for name, calc in self.calcs.items()
        }

    def load(self) -> ir.Model:
        scenario_parts = self._scenario_parts()
        if not scenario_parts:
            raise LoaderError("no scenario usages found")
        first = next(iter(scenario_parts.values()))
        configuration = self.expander.expand_type(
            self._configuration_type(first)
        )
        if not configuration.performs:
            raise LoaderError("the configuration performs no procedure")
        perform = configuration.performs[0]
        procedure_name = _type_of(perform)
        if procedure_name is None:
            raise LoaderError("perform needs a procedure type")
        procedure = self.definitions.get(procedure_name)
        if procedure is None:
            raise LoaderError(f"no definition for {procedure_name}")
        allocations = _allocation_map(configuration.allocations)
        converter = _Converter(
            _renamer(_bindings(perform)), self.calc_parameters
        )
        builder = _GraphBuilder(
            self.definitions, converter, procedure, allocations
        )
        nodes, start = builder.build()
        procedure_values = self._procedure_values(procedure)
        scenarios = {
            name: self._scenario(name, element, procedure_values)
            for name, element in scenario_parts.items()
        }
        resource_names = set(scenarios[next(iter(scenarios))].resources)
        for step_name, targets in allocations.items():
            for target in targets:
                if target not in resource_names:
                    raise LoaderError(
                        f"{step_name} allocated to unknown resource {target}"
                    )
        model = ir.Model(
            name=procedure.name or "model",
            start=start,
            nodes=nodes,
            calcs=self.calcs,
            scenarios=scenarios,
            requirements=self._requirements(),
            verifications=self._verifications(),
            model_checks=self._model_checks(scenario_parts),
            item_name=self._item_name(procedure),
            stat_priority=STAT_PRIORITY,
        )
        ir.validate(model)
        return model

    def _load_calcs(self) -> dict[str, ir.CalcDef]:
        calcs: dict[str, ir.CalcDef] = {}
        names = [
            d.name
            for d in self.definitions.by_name.values()
            if d.kind == "calc" and d.name
        ]
        parameters: dict[str, list[str]] = {}
        for name in names:
            definition = self.definitions.by_name[name]
            parameters[name] = [
                _feature_key(m) or ""
                for m in definition.members
                if isinstance(m, SysMLAttribute) and "in" in m.modifiers
            ]
        converter = _Converter(lambda path: ".".join(path), parameters)
        for name in names:
            definition = self.definitions.by_name[name]
            body: ir.Expr | None = None
            for member in definition.members:
                if (
                    isinstance(member, SysMLAttribute)
                    and "return" in member.modifiers
                    and member.value is not None
                ):
                    body = converter.convert(member.value)
            if body is None:
                # A random draw such as Bernoulli. The decision logic
                # handles it, so it has no expression here.
                continue
            calcs[name] = ir.CalcDef(
                name=name,
                parameters=tuple(parameters[name]),
                body=body,
            )
        return calcs

    def _scenario_parts(self) -> dict[str, SysMLElement]:
        parts: dict[str, SysMLElement] = {}
        # Scenarios are package-level usages. Features inside definitions
        # (for example `ref part scenario : Scenario` in a verification) are
        # not scenarios.
        for package in self.packages:
            for member in _package_members(package):
                if not isinstance(member, SysMLElement):
                    continue
                if member.kind != "part" or member.is_definition:
                    continue
                type_name = _type_of(member)
                if type_name and self.definitions.is_a(type_name, "Scenario"):
                    if member.name is None:
                        raise LoaderError("scenario usage needs a name")
                    parts[member.name] = member
        return parts

    def _configuration_type(self, scenario: SysMLElement) -> str:
        feature = self._scenario_feature(scenario, "configuration")
        if isinstance(feature, SysMLElement) and _type_of(feature):
            return _type_of(feature) or ""
        raise LoaderError("scenario has no configuration type")

    def _item_name(self, procedure: SysMLElement) -> str:
        for member in procedure.members:
            if (
                isinstance(member, SysMLElement)
                and member.kind == "item"
                and _type_of(member) is not None
                and self.definitions.is_a(_type_of(member) or "", "WorkItem")
            ):
                return member.name or "sample"
        return "sample"

    def _scenario(
        self,
        name: str,
        element: SysMLElement,
        procedure_values: dict[str, float],
    ) -> ir.Scenario:
        configuration_type = self._configuration_type(element)
        configuration = self.expander.expand_type(configuration_type)
        converter = _Converter(lambda p: ".".join(p), self.calc_parameters)
        values: dict[str, float] = dict(procedure_values)
        _flatten(configuration, "", self.calcs, converter, values)
        arrivals_feature = self._scenario_feature(element, "arrivals")
        arrivals, stat_fraction = self._arrivals(arrivals_feature, converter)
        warm_up = self._scenario_number(
            element, "warmUpTime", converter, default=0.0
        )
        max_retests = int(values.get("maxRetests", 1.0))
        resources = self._resources(configuration, converter)
        return ir.Scenario(
            name=name,
            arrivals=arrivals,
            stat_fraction=stat_fraction,
            warm_up_s=warm_up,
            max_retests=max_retests,
            values=values,
            resources=resources,
        )

    def _procedure_values(self, procedure: SysMLElement) -> dict[str, float]:
        """Constant attributes of the procedure, such as pBubble."""
        converter = _Converter(lambda p: ".".join(p), self.calc_parameters)
        values: dict[str, float] = {}
        for member in procedure.members:
            if isinstance(member, SysMLAttribute) and member.value is not None:
                key = _feature_key(member)
                if key is None:
                    continue
                constant = _evaluate_constant(
                    _attribute_value((member.value, member.units), converter),
                    self.calcs,
                )
                if constant is not None:
                    values[key] = constant
        return values

    def _scenario_feature(
        self,
        element: SysMLElement,
        key: str,
    ) -> SysMLMember | None:
        """Find a feature of a scenario usage or of its type chain."""
        for owner in self._owners(element):
            for member in owner.members:
                if _feature_key(member) == key:
                    return member
        return None

    def _owners(self, element: SysMLElement) -> list[SysMLElement]:
        """The usage, then the definitions of its type and supertypes."""
        owners: list[SysMLElement] = [element]
        type_name = _type_of(element)
        if type_name is None:
            return owners
        for name in self.definitions.chain(type_name):
            definition = self.definitions.get(name)
            if definition is not None:
                owners.append(definition)
        return owners

    def _arrivals(
        self,
        feature: SysMLElement | None,
        converter: _Converter,
    ) -> tuple[ir.Arrivals, float]:
        if not isinstance(feature, SysMLElement):
            raise LoaderError("scenario has no arrivals")
        type_name = _type_of(feature)
        if type_name is None:
            raise LoaderError("arrivals need a type")
        values: dict[str, float] = {}
        instance = self.expander.expand_type(type_name)
        for member in feature.members:
            if isinstance(member, SysMLAttribute):
                key = _feature_key(member)
                if key and member.value is not None:
                    instance.attributes[key] = (member.value, member.units)
        for key, value in instance.attributes.items():
            constant = _evaluate_constant(
                _attribute_value(value, converter), self.calcs
            )
            if constant is not None:
                values[key] = constant
        stat_fraction = values.get("statFraction", 0.0)
        if self.definitions.is_a(type_name, "BatchArrival"):
            return (
                ir.BatchArrivals(
                    count=int(values["count"]),
                    time_s=values.get("time", 0.0),
                ),
                stat_fraction,
            )
        if self.definitions.is_a(type_name, "PoissonArrival"):
            return (
                ir.PoissonArrivals(rate_per_s=values["rate"]),
                stat_fraction,
            )
        raise LoaderError(f"unknown arrival process: {type_name}")

    def _scenario_number(
        self,
        element: SysMLElement,
        key: str,
        converter: _Converter,
        default: float,
    ) -> float:
        feature = self._scenario_feature(element, key)
        if not isinstance(feature, (SysMLAttribute, SysMLElement)):
            return default
        if feature.value is None:
            return default
        value = _evaluate_constant(
            converter.convert(feature.value, default_unit=feature.units),
            self.calcs,
        )
        return default if value is None else value

    def _default_of(self, definition_name: str, key: str) -> float:
        definition = self.definitions.get(definition_name)
        if definition is None:
            raise LoaderError(f"no definition {definition_name}")
        for member in definition.members:
            if isinstance(member, SysMLAttribute) and member.name == key:
                if member.default_value is None:
                    break
                return float(
                    _evaluate_constant(
                        _Converter(lambda p: ".".join(p), {}).convert(
                            member.default_value, default_unit=member.units
                        ),
                        self.calcs,
                    )
                    or 0.0
                )
        raise LoaderError(f"no default for {definition_name}.{key}")

    def _resources(
        self,
        configuration: _Instance,
        converter: _Converter,
    ) -> dict[str, ir.ResourceSpec]:
        resources: dict[str, ir.ResourceSpec] = {}
        for name, child in configuration.children.items():
            kind = _resource_kind(self.definitions, child.type_name)
            if kind is None:
                continue
            values: dict[str, float] = {}
            _flatten(child, "", self.calcs, converter, values)
            if kind is ir.ResourceKind.STORE:
                resources[name] = ir.ResourceSpec(
                    name=name,
                    kind=kind,
                    initial_level=int(values.get("initialLevel", 0)),
                    reorder_level=int(values.get("reorderLevel", 0)),
                    refill_size=int(values.get("refillSize", 0)),
                    refill_duration_s=values.get("refillDuration", 0.0),
                )
            else:
                resources[name] = ir.ResourceSpec(
                    name=name,
                    kind=kind,
                    capacity=int(values.get("capacity", 1)),
                    batch_size=int(values.get("batchSize", 1)),
                    batch_timeout_s=values.get("batchTimeout", 0.0),
                )
        return resources

    def _requirements(self) -> dict[str, ir.Requirement]:
        requirements: dict[str, ir.Requirement] = {}
        converter = _Converter(lambda p: ".".join(p), {})
        for member in _walk(self.packages):
            if not (
                isinstance(member, SysMLElement)
                and member.kind == "requirement"
                and member.short_name
            ):
                continue
            constraint_text = member.require_constraint_text
            if constraint_text is None:
                # Stakeholder requirements have no constraint to check.
                continue
            constraint = converter.convert(parse_expression(constraint_text))
            thresholds: dict[str, float] = {}
            for feature in member.members:
                if isinstance(feature, SysMLAttribute) and feature.value:
                    key = _feature_key(feature)
                    if key is None:
                        continue
                    value = _evaluate_constant(
                        converter.convert(
                            feature.value, default_unit=feature.units
                        ),
                        self.calcs,
                    )
                    if value is not None:
                        thresholds[key] = value
            measured = next(
                (
                    _feature_key(feature)
                    for feature in member.members
                    if isinstance(feature, SysMLAttribute)
                    and (_feature_key(feature) or "").startswith("measured")
                ),
                None,
            )
            requirements[member.short_name] = ir.Requirement(
                uid=member.short_name,
                title=member.name or "",
                statement=member.doc or "",
                constraint=constraint,
                thresholds=thresholds,
                measured_name=measured,
            )
        return requirements

    def _model_checks(
        self,
        scenario_parts: dict[str, SysMLElement],
    ) -> list[ir.ModelCheck]:
        """Design checks: verification usages typed by ModelCheck."""
        checks: list[ir.ModelCheck] = []
        for member in _walk(self.packages):
            if not (
                isinstance(member, SysMLElement)
                and member.kind == "verification"
                and not member.is_definition
                and _type_of(member) == "ModelCheck"
            ):
                continue
            uid: str | None = None
            observed: Expression | None = None
            for feature in member.members:
                if (
                    isinstance(feature, SysMLElement)
                    and feature.kind == "objective"
                ):
                    for verify in feature.members:
                        if isinstance(verify, SysMLVerify):
                            uid = verify.requirement
                elif _feature_key(feature) == "observed":
                    observed = getattr(feature, "value", None)
            if uid is None or observed is None:
                raise LoaderError(f"incomplete model check: {member.name}")
            scenario = _scenario_of(observed, set(scenario_parts))
            converter = _Converter(
                _scenario_renamer(scenario), self.calc_parameters
            )
            checks.append(
                ir.ModelCheck(
                    requirement_uid=uid,
                    observed=converter.convert(observed),
                    scenario=scenario,
                )
            )
        return checks

    def _verifications(self) -> list[ir.SimulationVerification]:
        verifications: list[ir.SimulationVerification] = []
        for member in _walk(self.packages):
            if not (
                isinstance(member, SysMLElement)
                and member.kind == "verification"
                and not member.is_definition
                and self.definitions.is_a(
                    _type_of(member) or "", "SimulationVerification"
                )
            ):
                continue
            verifications.append(self._verification(member))
        return verifications

    def _verification(self, element: SysMLElement) -> ir.SimulationVerification:
        uid: str | None = None
        measured: str | None = None
        metric: ir.MetricKind | None = None
        scenario: str | None = None
        resource: str | None = None
        replications = int(
            self._default_of("SimulationVerification", "replications")
        )
        confidence = self._default_of("SimulationVerification", "confidence")
        horizon = self._default_of("SimulationVerification", "horizon")
        for member in element.members:
            if isinstance(member, SysMLElement) and member.kind == "objective":
                for verify in member.members:
                    if isinstance(verify, SysMLVerify):
                        uid = verify.requirement
            key = _feature_key(member)
            if key is None:
                continue
            value = getattr(member, "value", None)
            if key == "measured" and isinstance(value, FeatureReference):
                path = value.path or [value.name]
                uid, measured = path[0], path[-1]
            elif key == "metric" and isinstance(value, FeatureReference):
                metric = ir.MetricKind(value.path[-1])
            elif key == "scenario" and isinstance(value, FeatureReference):
                scenario = value.path[-1]
            elif key == "resource" and isinstance(value, FeatureReference):
                resource = value.path[-1]
            elif key == "horizon" and value is not None:
                horizon = (
                    _evaluate_constant(
                        self.expander_constant(value, member.units), self.calcs
                    )
                    or horizon
                )
            elif key == "replications" and value is not None:
                replications = int(value.value)
            elif key == "confidence" and value is not None:
                confidence = float(value.value)
        if (
            uid is None
            or measured is None
            or metric is None
            or scenario is None
        ):
            raise LoaderError(f"incomplete verification: {element.name}")
        return ir.SimulationVerification(
            case_id=element.short_name or element.name or "",
            requirement_uid=uid,
            measured_name=measured,
            metric=metric,
            scenario=scenario,
            horizon_s=horizon,
            replications=replications,
            confidence=confidence,
            resource=resource,
        )

    def expander_constant(
        self,
        value: Expression,
        unit: str | None,
    ) -> ir.Expr:
        return _Converter(lambda p: ".".join(p), {}).convert(
            value, default_unit=unit
        )


class _GraphBuilder:
    """Flattens the groups of one procedure into IR nodes."""

    def __init__(
        self,
        definitions: _Definitions,
        converter: _Converter,
        procedure: SysMLElement,
        allocations: dict[str, list[str]],
    ) -> None:
        self.definitions = definitions
        self.converter = converter
        self.procedure = procedure
        self.allocations = allocations
        self.markers: dict[str, str] = {}
        self.steps: dict[str, ir.Step] = {}
        self.edges: list[tuple[str, str, ir.Guard | None]] = []
        self.parallel: dict[str, list[str]] = {}
        self.decisions: dict[str, list[ir.Branch]] = {}
        self.retests: set[str] = set()
        self.step_names: set[str] = set()

    def build(self) -> tuple[dict[str, ir.Node], str]:
        entry, _ = self._group(self.procedure)
        for source, target, guard in self.edges:
            self._connect(source, target, guard)
        nodes: dict[str, ir.Node] = {}
        for name, step in self.steps.items():
            targets = self.parallel.get(name, [])
            if len(targets) > 1:
                raise LoaderError(f"step {name} has several successors")
            nodes[name] = ir.Step(
                name=step.name,
                duration=step.duration,
                next=tuple(targets),
                allocations=tuple(self.allocations.get(name, [])),
                consumes=step.consumes,
                retest=step.retest,
                assignments=(),
            )
        for name, kind in self.markers.items():
            if kind == "decide":
                nodes[name] = ir.Decision(
                    name, tuple(self.decisions.get(name, []))
                )
            elif kind == "fork":
                nodes[name] = ir.Fork(name, tuple(self.parallel.get(name, [])))
            elif kind == "join":
                nodes[name] = ir.Join(name, tuple(self.parallel.get(name, [])))
            elif kind == "merge":
                nodes[name] = ir.Merge(name, tuple(self.parallel.get(name, [])))
            else:
                raise LoaderError(f"unknown control kind: {kind}")
        return nodes, entry

    def _is_step(self, element: SysMLElement) -> bool:
        type_name = _type_of(element)
        return bool(
            element.kind == "action"
            and not element.is_definition
            and type_name is not None
            and self.definitions.is_a(type_name, "Step")
        )

    def _group(self, group: SysMLElement) -> tuple[str, str]:
        """Return (entry, exit) leaf names of a group."""
        children: dict[str, tuple[str, str]] = {}
        order: list[str] = []
        local_edges: list[SysMLSuccession] = []
        for member in group.members:
            if isinstance(member, SysMLElement) and member.kind == "action":
                if "perform" in member.modifiers:
                    continue
                name = member.name
                if name is None:
                    continue
                if self._is_step(member):
                    self._register_step(member)
                    children[name] = (name, name)
                elif not member.is_definition and member.members:
                    children[name] = self._group(member)
                else:
                    continue
                order.append(name)
            elif isinstance(member, SysMLBehaviourControl):
                if member.name is None:
                    raise LoaderError("behaviour control needs a name")
                self._register_control(member)
                children[member.name] = (member.name, member.name)
                order.append(member.name)
            elif isinstance(member, SysMLSuccession):
                local_edges.append(member)
        incoming = {edge.then for edge in local_edges}
        outgoing = {edge.first for edge in local_edges}
        entries = [n for n in order if n not in incoming]
        ends = [n for n in order if n not in outgoing and n not in self.retests]
        if not entries or not ends:
            raise LoaderError(f"group {group.name} has no entry or exit")
        for edge in local_edges:
            if edge.first not in children or edge.then not in children:
                raise LoaderError(f"unknown node in succession: {edge.first}")
            source = children[edge.first][1]
            target = children[edge.then][0]
            self.edges.append((source, target, self._guard(edge)))
        return children[entries[0]][0], children[ends[0]][1]

    def _guard(self, edge: SysMLSuccession) -> ir.Guard | None:
        if edge.guard is None:
            return None
        return self._convert_guard(edge.guard)

    def _convert_guard(self, expression: Expression) -> ir.Guard:
        negated = False
        operand = expression
        if (
            isinstance(expression, UnaryOperation)
            and expression.operator == "not"
        ):
            negated = True
            operand = expression.operand
        if isinstance(operand, Invocation) and (
            _simple_name(operand.callee) == "Bernoulli"
        ):
            probability: ir.Expr | None = None
            for argument in operand.arguments:
                if argument.name in (None, "p"):
                    probability = self.converter.convert(argument.value)
            if probability is None:
                raise LoaderError("Bernoulli needs argument p")
            return ir.BernoulliGuard(probability, negated)
        return ir.ConditionGuard(self.converter.convert(expression))

    def _register_step(self, element: SysMLElement) -> None:
        name = element.name
        assert name is not None
        if name in self.step_names or name in self.markers:
            raise LoaderError(f"duplicate node name: {name}")
        self.step_names.add(name)
        features: dict[str, tuple[Expression, str | None]] = {}
        for member in element.members:
            if isinstance(member, SysMLAttribute) and member.value is not None:
                key = _feature_key(member)
                if key is not None:
                    features[key] = (member.value, member.units)
        if "nominal" not in features:
            raise LoaderError(f"step {name} has no nominal duration")

        def expr(key: str) -> ir.Expr | None:
            if key not in features:
                return None
            return _attribute_value(features[key], self.converter)

        distribution = ir.Distribution.FIXED
        if "distribution" in features:
            distribution_value = features["distribution"][0]
            if isinstance(distribution_value, FeatureReference):
                distribution = ir.Distribution(distribution_value.path[-1])
        retest = False
        if "retest" in features:
            flag = features["retest"][0]
            retest = isinstance(flag, BooleanLiteral) and flag.value
        consumes = 0
        if "consumes" in features:
            consumes = int(_number(features["consumes"][0]))
        nominal = expr("nominal")
        assert nominal is not None
        duration = ir.Duration(
            distribution=distribution,
            nominal=nominal,
            low=expr("low"),
            high=expr("high"),
            sd=expr("sd"),
            sigma=expr("sigma"),
        )
        self.steps[name] = ir.Step(
            name=name,
            duration=duration,
            consumes=consumes,
            retest=retest,
        )
        if retest:
            self.retests.add(name)

    def _register_control(self, control: SysMLBehaviourControl) -> None:
        name = control.name
        assert name is not None
        if name in self.step_names or name in self.markers:
            raise LoaderError(f"duplicate node name: {name}")
        self.markers[name] = control.kind

    def _connect(
        self,
        source: str,
        target: str,
        guard: ir.Guard | None,
    ) -> None:
        if self.markers.get(source) == "decide":
            if guard is None:
                raise LoaderError(f"decision {source} needs a guard")
            self.decisions.setdefault(source, []).append(
                ir.Branch(guard, target)
            )
            return
        if guard is not None:
            raise LoaderError(f"guard on a non-decision: {source}")
        self.parallel.setdefault(source, []).append(target)


def _number(expression: Expression) -> float:
    if isinstance(expression, NumberLiteral):
        return expression.value
    raise LoaderError("expected a number")


def _bindings(perform: SysMLElement) -> dict[str, str]:
    """Map each procedure parameter to the configuration path it is bound to."""
    bindings: dict[str, str] = {}
    for member in perform.members:
        value = getattr(member, "value", None)
        key = _feature_key(member)
        if key is None or not isinstance(value, FeatureReference):
            continue
        bindings[key] = ".".join(value.path or [value.name])
    return bindings


def load_model(model_dir: Path) -> ir.Model:
    """Load the Halcyon-style model from a directory of SysML files."""
    return ModelLoader(parse_model(model_dir)).load()

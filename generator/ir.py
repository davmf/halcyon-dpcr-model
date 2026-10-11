"""
Engine-independent intermediate representation (IR) of a simulation model.

The loader turns SysML into these types. The Salabim backend, the analytic
bounds and the verification layers read them. Nothing here depends on
Salabim or on StrictDoc.

Conventions:
- All quantities are SI: seconds, cubic metres, pascals, hertz.
- Booleans are floats: 1.0 is true, 0.0 is false.
- Names in expressions are keys of a values mapping. The loader writes them
  as dotted paths relative to the configuration, for example
  `cartridge.partitionVolume`, and as `pBubble` for procedure attributes.
"""

import enum
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


class Distribution(enum.Enum):
    FIXED = "fixed"
    TRIANGULAR = "triangular"
    NORMAL = "normal"
    LOG_NORMAL = "logNormal"


class MetricKind(enum.Enum):
    COMPLETED_PER_SHIFT = "completedPerShift"
    TIME_TO_FIRST_RESULT = "timeToFirstResult"
    MEAN_TURNAROUND = "meanTurnaround"
    MEAN_STAT_TURNAROUND = "meanStatTurnaround"
    INVALID_RATE = "invalidRate"
    UTILISATION = "utilisation"


class ResourceKind(enum.Enum):
    UNIT = "unit"
    BATCH = "batch"
    STORE = "store"


@dataclass(frozen=True)
class Literal:
    value: float


@dataclass(frozen=True)
class Ref:
    name: str


@dataclass(frozen=True)
class Unary:
    operator: str
    operand: Expr


@dataclass(frozen=True)
class Binary:
    operator: str
    left: Expr
    right: Expr


@dataclass(frozen=True)
class Call:
    function: str
    arguments: tuple[tuple[str, Expr], ...]


@dataclass(frozen=True)
class Conditional:
    condition: Expr
    when_true: Expr
    when_false: Expr


Expr = Literal | Ref | Unary | Binary | Call | Conditional


@dataclass(frozen=True)
class CalcDef:
    """A calc def: named parameters and one return expression."""

    name: str
    parameters: tuple[str, ...]
    body: Expr


class ExpressionError(Exception):
    """Raised when an expression cannot be evaluated."""


_BINARY_OPERATIONS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "**": lambda a, b: a**b,
    "^": lambda a, b: a**b,
    "%": lambda a, b: a % b,
    "<": lambda a, b: float(a < b),
    "<=": lambda a, b: float(a <= b),
    ">": lambda a, b: float(a > b),
    ">=": lambda a, b: float(a >= b),
    "==": lambda a, b: float(a == b),
    "!=": lambda a, b: float(a != b),
    "and": lambda a, b: float(bool(a) and bool(b)),
    "or": lambda a, b: float(bool(a) or bool(b)),
    "xor": lambda a, b: float(bool(a) != bool(b)),
}


def evaluate(
    expr: Expr,
    values: Mapping[str, float],
    calcs: Mapping[str, CalcDef],
) -> float:
    """Evaluate an expression. Names are looked up in values."""
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, Ref):
        if expr.name not in values:
            raise ExpressionError(f"unknown reference: {expr.name}")
        return values[expr.name]
    if isinstance(expr, Unary):
        operand = evaluate(expr.operand, values, calcs)
        if expr.operator == "-":
            return -operand
        if expr.operator == "+":
            return operand
        if expr.operator == "not":
            return float(not bool(operand))
        raise ExpressionError(f"unknown unary operator: {expr.operator}")
    if isinstance(expr, Binary):
        operation = _BINARY_OPERATIONS.get(expr.operator)
        if operation is None:
            raise ExpressionError(f"unknown operator: {expr.operator}")
        return operation(
            evaluate(expr.left, values, calcs),
            evaluate(expr.right, values, calcs),
        )
    if isinstance(expr, Call):
        return _evaluate_call(expr, values, calcs)
    if isinstance(expr, Conditional):
        if evaluate(expr.condition, values, calcs):
            return evaluate(expr.when_true, values, calcs)
        return evaluate(expr.when_false, values, calcs)
    raise ExpressionError(f"unknown expression node: {expr!r}")


def _evaluate_call(
    call: Call,
    values: Mapping[str, float],
    calcs: Mapping[str, CalcDef],
) -> float:
    definition = calcs.get(call.function)
    if definition is None:
        raise ExpressionError(f"unknown calc def: {call.function}")
    bound: dict[str, float] = {}
    supplied = dict(call.arguments)
    for parameter in definition.parameters:
        if parameter not in supplied:
            raise ExpressionError(
                f"{call.function}: missing argument {parameter}"
            )
        bound[parameter] = evaluate(supplied[parameter], values, calcs)
    return evaluate(definition.body, bound, calcs)


@dataclass(frozen=True)
class Duration:
    """
    Duration of a step. `nominal` is the fixed value, the triangular mode,
    the normal mean or the log-normal median. Other fields are per kind.
    """

    distribution: Distribution
    nominal: Expr
    low: Expr | None = None
    high: Expr | None = None
    sd: Expr | None = None
    sigma: Expr | None = None

    def mean(
        self,
        values: Mapping[str, float],
        calcs: Mapping[str, CalcDef],
    ) -> float:
        """Expected value of the duration, in seconds."""
        nominal = evaluate(self.nominal, values, calcs)
        if self.distribution is Distribution.TRIANGULAR:
            assert self.low is not None and self.high is not None
            low = evaluate(self.low, values, calcs)
            high = evaluate(self.high, values, calcs)
            return (low + nominal + high) / 3.0
        if self.distribution is Distribution.LOG_NORMAL:
            assert self.sigma is not None
            sigma = evaluate(self.sigma, values, calcs)
            return nominal * math.exp(sigma * sigma / 2.0)
        return nominal


@dataclass(frozen=True)
class Assignment:
    """Sets an item attribute, for example `sample.invalid := true`."""

    target: str
    value: Expr


@dataclass(frozen=True)
class Step:
    name: str
    duration: Duration
    next: tuple[str, ...] = ()
    allocations: tuple[str, ...] = ()
    consumes: int = 0
    retest: bool = False
    assignments: tuple[Assignment, ...] = ()


@dataclass(frozen=True)
class BernoulliGuard:
    probability: Expr
    negated: bool = False


@dataclass(frozen=True)
class ConditionGuard:
    condition: Expr


Guard = BernoulliGuard | ConditionGuard


@dataclass(frozen=True)
class Branch:
    guard: Guard
    target: str


@dataclass(frozen=True)
class Decision:
    name: str
    branches: tuple[Branch, ...]


@dataclass(frozen=True)
class Fork:
    name: str
    next: tuple[str, ...]


@dataclass(frozen=True)
class Join:
    name: str
    next: tuple[str, ...]


@dataclass(frozen=True)
class Merge:
    name: str
    next: tuple[str, ...]


Node = Step | Decision | Fork | Join | Merge


@dataclass(frozen=True)
class ResourceSpec:
    """A resource of one configuration: unit pool, batch pool or store."""

    name: str
    kind: ResourceKind
    capacity: int = 1
    batch_size: int = 1
    batch_timeout_s: float = 0.0
    initial_level: int = 0
    reorder_level: int = 0
    refill_size: int = 0
    refill_duration_s: float = 0.0


@dataclass(frozen=True)
class BatchArrivals:
    count: int
    time_s: float = 0.0


@dataclass(frozen=True)
class PoissonArrivals:
    rate_per_s: float


Arrivals = BatchArrivals | PoissonArrivals


@dataclass(frozen=True)
class Scenario:
    """A configuration variant with its arrival process and warm-up."""

    name: str
    arrivals: Arrivals
    stat_fraction: float
    warm_up_s: float
    max_retests: int
    values: Mapping[str, float]
    resources: Mapping[str, ResourceSpec]


@dataclass(frozen=True)
class Requirement:
    """A SYS requirement: the UID, the constraint and its thresholds."""

    uid: str
    title: str
    statement: str
    constraint: Expr
    thresholds: Mapping[str, float]
    measured_name: str | None = None


@dataclass(frozen=True)
class SimulationVerification:
    """One simulated check of a requirement under one scenario."""

    case_id: str
    requirement_uid: str
    measured_name: str
    metric: MetricKind
    scenario: str
    horizon_s: float
    replications: int = 10
    confidence: float = 0.95
    resource: str | None = None


@dataclass(frozen=True)
class ModelCheck:
    """A design check: an observed design value against a requirement."""

    requirement_uid: str
    observed: Expr
    scenario: str


@dataclass(frozen=True)
class Model:
    """The whole model: the process graph, calcs, scenarios and checks."""

    name: str
    start: str
    nodes: Mapping[str, Node]
    calcs: Mapping[str, CalcDef]
    scenarios: Mapping[str, Scenario]
    requirements: Mapping[str, Requirement]
    verifications: Sequence[SimulationVerification]
    model_checks: Sequence[ModelCheck] = ()
    item_name: str = "sample"
    stat_priority: int = 1

    def join_inputs(self, name: str) -> int:
        """Number of incoming successions to a join node."""
        count = 0
        for node in self.nodes.values():
            if name in _successors(node):
                count += 1
        return count

    def scenario(self, name: str) -> Scenario:
        if name not in self.scenarios:
            known = ", ".join(sorted(self.scenarios))
            raise KeyError(f"unknown scenario {name!r}; known: {known}")
        return self.scenarios[name]


def _successors(node: Node) -> tuple[str, ...]:
    if isinstance(node, Decision):
        return tuple(branch.target for branch in node.branches)
    return node.next


def successors(node: Node) -> tuple[str, ...]:
    """Names of the nodes that follow a node in the control-flow graph."""
    return _successors(node)


def validate(model: Model) -> None:
    """Raise ValueError when the graph refers to unknown nodes."""
    if model.start not in model.nodes:
        raise ValueError(f"start node not in graph: {model.start}")
    for node in model.nodes.values():
        for target in successors(node):
            if target not in model.nodes:
                raise ValueError(f"{node.name} refers to unknown node {target}")
    for verification in model.verifications:
        if verification.scenario not in model.scenarios:
            raise ValueError(
                f"verification of {verification.requirement_uid} refers to "
                f"unknown scenario {verification.scenario}"
            )

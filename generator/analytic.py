"""
Analytic steady-state bounds from the IR (no simulation).

For each scenario with Poisson arrivals:

- expected visits of each node per sample, by propagating probabilities
  through the graph (the graph has no loops, because retests end a run);
- expected busy seconds per sample of each resource (a step seizes all its
  resources for its mean duration; a batch resource gives one batch's
  duration shared over batchSize items, which assumes full batches);
- utilisation = arrival rate x busy per sample / capacity;
- throughput bound = capacity / busy per sample, and the bottleneck is the
  resource with the smallest bound.

Retests and the invalid path are not included. A condition guard on a flag
(such as sample.invalid) takes the probability that the flag is set, which
is the visit probability of the steps that assign it.
"""

from dataclasses import dataclass

from generator import ir
from generator.ir import (
    BernoulliGuard,
    ConditionGuard,
    Decision,
    Fork,
    Join,
    PoissonArrivals,
    ResourceKind,
    Step,
    Unary,
)

SECONDS_PER_SHIFT = 8 * 3600.0


@dataclass(frozen=True)
class ResourceBound:
    name: str
    capacity: int
    busy_per_sample_s: float
    utilisation: float
    throughput_per_shift: float


@dataclass(frozen=True)
class CapacityBounds:
    scenario: str
    arrival_rate_per_h: float
    resources: dict[str, ResourceBound]
    bottleneck: str
    throughput_bound_per_shift: float


def _topological_order(model: ir.Model) -> list[str]:
    order: list[str] = []
    state: dict[str, int] = {}

    def visit(name: str) -> None:
        if state.get(name) == 2:
            return
        if state.get(name) == 1:
            raise ValueError(f"cycle in the graph at {name}")
        state[name] = 1
        for target in ir.successors(model.nodes[name]):
            visit(target)
        state[name] = 2
        order.append(name)

    visit(model.start)
    order.reverse()
    return order


def _branch_probabilities(
    model: ir.Model,
    scenario: ir.Scenario,
    decision: Decision,
    flags: dict[str, float],
) -> dict[str, float]:
    """Probability of each branch target. Guards are checked in order."""
    probabilities: dict[str, float] = {}
    remaining = 1.0
    for branch in decision.branches:
        guard = branch.guard
        if isinstance(guard, BernoulliGuard):
            p = ir.evaluate(guard.probability, scenario.values, model.calcs)
            share = (1.0 - p) if guard.negated else p
        else:
            assert isinstance(guard, ConditionGuard)
            share = _flag_share(guard.condition, flags)
        taken = min(share, remaining)
        probabilities[branch.target] = (
            probabilities.get(branch.target, 0.0) + taken
        )
        remaining -= taken
    return probabilities


def _flag_share(condition: ir.Expr, flags: dict[str, float]) -> float:
    """Probability that a flag condition holds, given the flags so far."""
    negated = False
    operand = condition
    if isinstance(operand, Unary) and operand.operator == "not":
        negated = True
        operand = operand.operand
    if not isinstance(operand, ir.Ref):
        raise TypeError("only flag conditions can be bounded analytically")
    true_share = flags.get(operand.name, 0.0)
    return (1.0 - true_share) if negated else true_share


def expected_visits(
    model: ir.Model,
    scenario: ir.Scenario,
) -> dict[str, float]:
    """Expected number of visits of each node per sample (retests ignored).

    Nodes are visited in topological order, so a flag set by an assignment
    is known before the decisions that test it.
    """
    visits: dict[str, float] = {name: 0.0 for name in model.nodes}
    flags: dict[str, float] = {}
    visits[model.start] = 1.0
    for name in _topological_order(model):
        node = model.nodes[name]
        if isinstance(node, Step):
            for assignment in node.assignments:
                value = ir.evaluate(
                    assignment.value, scenario.values, model.calcs
                )
                if value > 0.5:
                    flags[assignment.target] = (
                        flags.get(assignment.target, 0.0) + visits[name]
                    )
        if isinstance(node, Decision):
            shares = _branch_probabilities(model, scenario, node, flags)
            for target, share in shares.items():
                visits[target] += visits[name] * share
        else:
            # A join passes one token on, after all its inputs arrived.
            outflow = visits[name]
            if isinstance(node, Join):
                outflow /= model.join_inputs(name)
            for target in ir.successors(node):
                visits[target] += outflow
    return visits


def capacity_bounds(model: ir.Model, scenario_name: str) -> CapacityBounds:
    """Analytic utilisation and throughput bounds for a Poisson scenario."""
    scenario = model.scenario(scenario_name)
    if not isinstance(scenario.arrivals, PoissonArrivals):
        raise TypeError(f"{scenario_name} has no Poisson arrivals")
    rate = scenario.arrivals.rate_per_s
    visits = expected_visits(model, scenario)
    busy: dict[str, float] = {name: 0.0 for name in scenario.resources}
    for name, node in model.nodes.items():
        if not isinstance(node, Step):
            continue
        mean = node.duration.mean(scenario.values, model.calcs)
        for resource in node.allocations:
            spec = scenario.resources[resource]
            if spec.kind is ResourceKind.STORE:
                continue
            if spec.kind is ResourceKind.BATCH:
                busy[resource] += visits[name] * mean / spec.batch_size
            else:
                busy[resource] += visits[name] * mean
    resources: dict[str, ResourceBound] = {}
    for name, spec in scenario.resources.items():
        if spec.kind is ResourceKind.STORE or busy[name] == 0.0:
            continue
        per_sample = busy[name]
        resources[name] = ResourceBound(
            name=name,
            capacity=spec.capacity,
            busy_per_sample_s=per_sample,
            utilisation=rate * per_sample / spec.capacity,
            throughput_per_shift=(
                spec.capacity / per_sample * SECONDS_PER_SHIFT
            ),
        )
    bottleneck = min(
        resources.values(), key=lambda bound: bound.throughput_per_shift
    )
    return CapacityBounds(
        scenario=scenario_name,
        arrival_rate_per_h=rate * 3600.0,
        resources=resources,
        bottleneck=bottleneck.name,
        throughput_bound_per_shift=bottleneck.throughput_per_shift,
    )


def most_likely_path_seconds(
    model: ir.Model,
    scenario: ir.Scenario,
) -> float:
    """Duration of the most likely path from start to its end, no queueing.

    At each decision the branch with the largest share is taken. At each
    fork the longest parallel branch sets the time to the join. A batch step
    adds the batch timeout, because a lone item waits for it.
    """

    def walk(name: str) -> tuple[float, str | None]:
        node = model.nodes[name]
        if isinstance(node, Join):
            return 0.0, name
        if isinstance(node, Fork):
            spans = [walk(target) for target in node.next]
            joins = {end for _, end in spans}
            if len(joins) != 1 or None in joins:
                raise ValueError(f"fork {name} does not meet at one join")
            join_name = joins.pop()
            assert join_name is not None
            longest = max(seconds for seconds, _ in spans)
            rest, end = walk_after_join(join_name)
            return longest + rest, end
        if isinstance(node, Decision):
            shares = _branch_probabilities(model, scenario, node, {})
            target = max(shares, key=lambda key: shares[key])
            rest, end = walk(target)
            return rest, end
        if isinstance(node, Step):
            seconds = node.duration.mean(scenario.values, model.calcs)
            for resource in node.allocations:
                spec = scenario.resources[resource]
                if spec.kind is ir.ResourceKind.BATCH:
                    seconds += spec.batch_timeout_s
        else:
            seconds = 0.0
        successors = ir.successors(node)
        if not successors:
            return seconds, None
        rest, end = walk(successors[0])
        return seconds + rest, end

    def walk_after_join(join_name: str) -> tuple[float, str | None]:
        successors = ir.successors(model.nodes[join_name])
        if not successors:
            return 0.0, None
        return walk(successors[0])

    total, _ = walk(model.start)
    return total


def retest_probability(model: ir.Model, scenario: ir.Scenario) -> float:
    """Probability that one run ends in a retest step (no retests counted)."""
    visits = expected_visits(model, scenario)
    return sum(
        visits[name]
        for name, node in model.nodes.items()
        if isinstance(node, Step) and node.retest
    )


def invalid_rate(model: ir.Model, scenario: ir.Scenario) -> float:
    """Share of samples that stay without a result after every retest.

    Each run ends in a retest with probability q. A sample is INVALID when
    all its runs (the first and maxRetests retests) end in a retest step.
    """
    q = retest_probability(model, scenario)
    return q ** (scenario.max_retests + 1)

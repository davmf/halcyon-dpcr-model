"""
Salabim backend: runs one replication of a Model in yieldless style.

This is the only module that uses Salabim for the simulation. It turns the
IR into components:

- _Source creates work items (batch or Poisson arrivals).
- _Sample owns one work item. It runs the procedure once per run, and starts
  a new run when a retest step asks for one and retests remain.
- _Token walks the control-flow graph of one run. A fork starts extra tokens;
  a join lets only the last arriving token continue.
- Unit resources are sim.Resource pools. A step requests all its units in one
  call, so it waits until every unit is free. Priority is the negated
  WorkItem priority, because Salabim serves lower values first.
- A batch resource has a queue and one _BatchDispatcher. The dispatcher waits
  for a free unit, then forms a batch from the queue: it takes up to batchSize
  items when batchSize is reached, or when batchTimeout has passed since the
  oldest waiting item arrived. A _BatchRun holds the unit for the batch.
- Stores are sim.Resource pools with capacity equal to the stock. A draw
  claims units and never releases them. A refill raises the capacity.

Random streams are seeded per purpose (arrivals, durations, branches), so one
seed gives one result. Nothing here reads the model files.
"""

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, field

import salabim as sim

from generator.ir import (
    Assignment,
    BatchArrivals,
    BernoulliGuard,
    Branch,
    ConditionGuard,
    Decision,
    Distribution,
    Duration,
    Fork,
    Join,
    Merge,
    Model,
    Node,
    PoissonArrivals,
    ResourceKind,
    ResourceSpec,
    Scenario,
    Step,
    evaluate,
)
from generator.results import (
    BusyInterval,
    Outcome,
    RunResult,
    SampleRecord,
    TraceEvent,
)


@dataclass(frozen=True)
class RunOptions:
    """Options of one replication."""

    seed: int
    horizon_s: float
    duration_scale: float = 1.0
    overrides: Mapping[str, float] = field(default_factory=dict)
    record_trace: bool = False
    drain: bool = False
    animator: object | None = None
    blind_animation: bool = True


class _Pool:
    """A resource of the scenario, with its Salabim objects."""

    def __init__(self, spec: ResourceSpec) -> None:
        self.spec = spec
        self.resource: sim.Resource | None = None
        self.queue: sim.Queue | None = None
        if spec.kind is ResourceKind.STORE:
            self.resource = sim.Resource(spec.name, capacity=spec.initial_level)
        elif spec.kind is ResourceKind.UNIT:
            self.resource = sim.Resource(spec.name, capacity=spec.capacity)
        else:
            self.queue = sim.Queue(f"{spec.name}-queue")
        self.refill_pending = False
        self.free_units = spec.capacity
        self.unit_freed = sim.State(f"{spec.name}-freed", value=False)
        self.arrived = sim.State(f"{spec.name}-arrived", value=False)
        self.full = sim.State(f"{spec.name}-full", value=False)
        self.waiting: list[_Token] = []


class _Engine:
    """State shared by the components of one replication."""

    def __init__(
        self,
        model: Model,
        scenario: Scenario,
        options: RunOptions,
    ) -> None:
        self.model = model
        self.scenario = scenario
        self.options = options
        self.values: dict[str, float] = dict(scenario.values)
        self.values.update(options.overrides)
        self.arrival_rng = random.Random(f"{options.seed}:arrivals")
        self.duration_rng = random.Random(f"{options.seed}:durations")
        self.branch_rng = random.Random(f"{options.seed}:branches")
        self.pools: dict[str, _Pool] = {
            name: _Pool(spec) for name, spec in scenario.resources.items()
        }
        self.end_s = scenario.warm_up_s + options.horizon_s
        self.samples: list[_Sample] = []
        self.busy: list[BusyInterval] = []
        self.trace: list[TraceEvent] = []
        self.arrivals_total = 0
        self.counters: dict[str, int] = {
            "tokens_started": 0,
            "steps_done": 0,
            "retests": 0,
            "batches_launched": 0,
            "refills": 0,
        }

    def spawn_sample(self) -> None:
        """Create one work item. STAT with the scenario's share."""
        priority = 0
        if self.arrival_rng.random() < self.scenario.stat_fraction:
            priority = self.model.stat_priority
        self.arrivals_total += 1
        sample = _Sample(
            engine=self,
            sample_id=self.arrivals_total,
            work_priority=priority,
        )
        self.samples.append(sample)
        if self.options.animator is not None:
            self.options.animator.on_sample_created(sample)

    def sample_duration(self, duration: Duration) -> float:
        """Draw one duration in seconds. Applies the duration scale."""
        values = self.values
        calcs = self.model.calcs
        nominal = evaluate(duration.nominal, values, calcs)
        rng = self.duration_rng
        if duration.distribution is Distribution.TRIANGULAR:
            assert duration.low is not None and duration.high is not None
            low = evaluate(duration.low, values, calcs)
            high = evaluate(duration.high, values, calcs)
            drawn = rng.triangular(low, high, nominal)
        elif duration.distribution is Distribution.NORMAL:
            assert duration.sd is not None
            sd = evaluate(duration.sd, values, calcs)
            drawn = max(0.0, rng.gauss(nominal, sd))
        elif duration.distribution is Distribution.LOG_NORMAL:
            assert duration.sigma is not None
            sigma = evaluate(duration.sigma, values, calcs)
            drawn = nominal * math.exp(sigma * rng.gauss(0.0, 1.0))
        else:
            drawn = nominal
        return drawn * self.options.duration_scale

    def item_values(self, sample: _Sample) -> dict[str, float]:
        """Scenario values plus the item attributes, as `item.attribute`."""
        merged = dict(self.values)
        prefix = self.model.item_name
        for key, value in sample.attributes.items():
            merged[f"{prefix}.{key}"] = value
        return merged


class _Source(sim.Component):
    def setup(self, engine: _Engine) -> None:
        self.engine = engine

    def process(self) -> None:
        arrivals = self.engine.scenario.arrivals
        if isinstance(arrivals, BatchArrivals):
            self.hold(arrivals.time_s)
            for _ in range(arrivals.count):
                self.engine.spawn_sample()
            return
        assert isinstance(arrivals, PoissonArrivals)
        while True:
            gap = self.engine.arrival_rng.expovariate(arrivals.rate_per_s)
            self.hold(gap)
            if self.env.now() >= self.engine.end_s:
                return
            self.engine.spawn_sample()


class _Run:
    """One pass of a work item through the procedure."""

    def __init__(self, sample: _Sample, engine: _Engine) -> None:
        self.sample = sample
        self.engine = engine
        self.active = 0
        self.joins: dict[str, int] = {}
        self.retest_requested = False
        self.done = sim.State(f"run-{sample.sample_id}", value=False)

    def spawn(self, start: str) -> None:
        self.active += 1
        _Token(owner=self, start=start)

    def token_ended(self) -> None:
        self.active -= 1
        if self.active == 0:
            self.done.set(True)


class _Sample(sim.Component):
    """One work item. The component waits for each run to end."""

    def setup(
        self, engine: _Engine, sample_id: int, work_priority: int
    ) -> None:
        self.engine = engine
        self.sample_id = sample_id
        self.work_priority = work_priority
        self.arrival_s = self.env.now()
        self.attributes: dict[str, float] = {"invalid": 0.0}
        self.runs = 0
        self.retests = 0
        self.finish_s: float | None = None
        self.outcome: str | None = None

    def process(self) -> None:
        max_retests = self.engine.scenario.max_retests
        while True:
            self.attributes["invalid"] = 0.0
            self.runs += 1
            run = _Run(self, self.engine)
            run.spawn(self.engine.model.start)
            self.wait(run.done)
            if run.retest_requested and self.retests < max_retests:
                self.retests += 1
                self.engine.counters["retests"] += 1
                continue
            self.finish_s = self.env.now()
            if run.retest_requested:
                invalid = self.attributes["invalid"] > 0.5
                self.outcome = Outcome.INVALID if invalid else Outcome.ABORTED
            else:
                self.outcome = Outcome.REPORTED
            return


class _Token(sim.Component):
    """Walks the graph of one run from a start node."""

    def setup(self, owner: _Run, start: str) -> None:
        self.owner = owner
        self.start = start
        self.engine = owner.engine
        self.engine.counters["tokens_started"] += 1
        self.batch_done: sim.State | None = None
        self.batch_enqueued_s = 0.0
        self.batch_duration: Duration | None = None

    def process(self) -> None:
        sample = self.owner.sample
        model = self.engine.model
        node_name: str | None = self.start
        while node_name is not None:
            node = model.nodes[node_name]
            if isinstance(node, Join) and not self._join_arrival(node):
                break
            node_name = self._visit(node, sample)
        self.owner.token_ended()

    def _visit(self, node: Node, sample: _Sample) -> str | None:
        if isinstance(node, Step):
            return self._step(node, sample)
        if isinstance(node, Decision):
            return self._decide(node, sample)
        if isinstance(node, Fork):
            for target in node.next[1:]:
                self.owner.spawn(target)
            return node.next[0]
        if isinstance(node, (Join, Merge)):
            return node.next[0] if node.next else None
        raise TypeError(f"unknown node: {node!r}")

    def _join_arrival(self, node: Join) -> bool:
        """Count this token at a join. True only for the last arrival."""
        arrived = self.owner.joins.get(node.name, 0) + 1
        self.owner.joins[node.name] = arrived
        return arrived >= self.engine.model.join_inputs(node.name)

    def _decide(self, node: Decision, sample: _Sample) -> str:
        draw = self.engine.branch_rng.random()
        values = self.engine.item_values(sample)
        for branch in node.branches:
            if _guard_passes(branch, draw, values, self.engine):
                return branch.target
        raise RuntimeError(f"no branch of {node.name} matched")

    def _step(self, step: Step, sample: _Sample) -> str | None:
        engine = self.engine
        pools = [engine.pools[name] for name in step.allocations]
        for pool in pools:
            if pool.spec.kind is ResourceKind.STORE and step.consumes > 0:
                self.request((pool.resource, step.consumes))
                self._refill_if_low(pool)
        units = [p for p in pools if p.spec.kind is ResourceKind.UNIT]
        batches = [p for p in pools if p.spec.kind is ResourceKind.BATCH]
        if batches and (len(batches) > 1 or units):
            raise NotImplementedError(
                f"{step.name}: a batch step cannot use other resources"
            )
        enqueued_at = self.env.now()
        if batches:
            self._enqueue_batch(batches[0], step)
        elif units:
            priority = -sample.work_priority
            self.request(*[(p.resource, 1, priority) for p in units])
            start = self.env.now()
            self.hold(engine.sample_duration(step.duration))
            self.release(*[p.resource for p in units])
            for pool in units:
                engine.busy.append(
                    BusyInterval(
                        pool.spec.name, start, self.env.now(), sample.sample_id
                    )
                )
        else:
            self.hold(engine.sample_duration(step.duration))
        if engine.options.record_trace:
            engine.trace.append(
                TraceEvent(
                    sample.sample_id,
                    step.name,
                    tuple(step.allocations),
                    enqueued_at,
                    self.env.now(),
                )
            )
        for assignment in step.assignments:
            _apply_assignment(assignment, engine, sample)
        if step.retest:
            self.owner.retest_requested = True
        engine.counters["steps_done"] += 1
        return step.next[0] if step.next else None

    def _refill_if_low(self, pool: _Pool) -> None:
        assert pool.resource is not None
        spec = pool.spec
        level = pool.resource.available_quantity()
        if level <= spec.reorder_level and not pool.refill_pending:
            pool.refill_pending = True
            _Refill(pool=pool, engine=self.engine)

    def _enqueue_batch(self, pool: _Pool, step: Step) -> None:
        """Join the batch queue and wait until the batch run is done."""
        assert pool.queue is not None
        self.batch_done = sim.State(f"{pool.spec.name}-done", value=False)
        self.batch_enqueued_s = self.env.now()
        self.batch_duration = step.duration
        pool.waiting.append(self)
        self.enter(pool.queue)
        pool.arrived.set(True)
        if len(pool.waiting) >= pool.spec.batch_size:
            pool.full.set(True)
        self.wait(self.batch_done)


class _Refill(sim.Component):
    def setup(self, pool: _Pool, engine: _Engine) -> None:
        self.pool = pool
        self.engine = engine

    def process(self) -> None:
        self.hold(self.pool.spec.refill_duration_s)
        resource = self.pool.resource
        assert resource is not None
        resource.set_capacity(resource.capacity() + self.pool.spec.refill_size)
        self.pool.refill_pending = False
        self.engine.counters["refills"] += 1


class _BatchDispatcher(sim.Component):
    """Forms batches from the queue whenever a unit is free."""

    def setup(self, pool: _Pool, engine: _Engine) -> None:
        self.pool = pool
        self.engine = engine

    def process(self) -> None:
        pool = self.pool
        spec = pool.spec
        while True:
            while not pool.waiting:
                pool.arrived.set(False)
                self.wait(pool.arrived)
            while pool.free_units == 0:
                pool.unit_freed.set(False)
                self.wait(pool.unit_freed)
            oldest = pool.waiting[0]
            deadline = oldest.batch_enqueued_s + spec.batch_timeout_s
            while len(pool.waiting) < spec.batch_size:
                remaining = deadline - self.env.now()
                if remaining <= 0:
                    break
                pool.full.set(False)
                self.wait(pool.full, fail_delay=remaining)
            taken = pool.waiting[: spec.batch_size]
            del pool.waiting[: spec.batch_size]
            assert pool.queue is not None
            for member in taken:
                pool.queue.remove(member)
            pool.full.set(len(pool.waiting) >= spec.batch_size)
            pool.free_units -= 1
            duration = taken[0].batch_duration
            assert duration is not None
            _BatchRun(
                pool=pool,
                members=taken,
                duration=duration,
                engine=self.engine,
            )


class _BatchRun(sim.Component):
    """Holds one unit of a batch resource for one batch."""

    def setup(
        self,
        pool: _Pool,
        members: list[_Token],
        duration: Duration,
        engine: _Engine,
    ) -> None:
        self.pool = pool
        self.members = members
        self.duration = duration
        self.engine = engine

    def process(self) -> None:
        start = self.env.now()
        self.hold(self.engine.sample_duration(self.duration))
        end = self.env.now()
        self.pool.free_units += 1
        self.pool.unit_freed.set(True)
        self.engine.counters["batches_launched"] += 1
        self.engine.busy.append(
            BusyInterval(self.pool.spec.name, start, end, 0)
        )
        for member in self.members:
            assert member.batch_done is not None
            member.batch_done.set(True)


def _guard_passes(
    branch: Branch,
    draw: float,
    values: Mapping[str, float],
    engine: _Engine,
) -> bool:
    guard = branch.guard
    if isinstance(guard, BernoulliGuard):
        probability = evaluate(guard.probability, values, engine.model.calcs)
        success = draw < probability
        return success != guard.negated
    assert isinstance(guard, ConditionGuard)
    return bool(evaluate(guard.condition, values, engine.model.calcs))


def _apply_assignment(
    assignment: Assignment,
    engine: _Engine,
    sample: _Sample,
) -> None:
    prefix = engine.model.item_name + "."
    if not assignment.target.startswith(prefix):
        raise ValueError(f"unsupported assignment: {assignment.target}")
    key = assignment.target[len(prefix) :]
    values = engine.item_values(sample)
    sample.attributes[key] = evaluate(
        assignment.value, values, engine.model.calcs
    )


def simulate(
    model: Model,
    scenario_name: str,
    options: RunOptions,
) -> RunResult:
    """Run one replication and return its records."""
    scenario = model.scenario(scenario_name)
    env = sim.Environment(
        trace=False,
        blind_animation=options.blind_animation,
    )
    engine = _Engine(model, scenario, options)
    for pool in engine.pools.values():
        if pool.spec.kind is ResourceKind.BATCH:
            _BatchDispatcher(pool=pool, engine=engine)
    if options.animator is not None:
        options.animator.attach(engine)
    _Source(engine=engine)
    if options.drain:
        env.run()
        end_s = env.now()
    else:
        env.run(till=engine.end_s)
        end_s = engine.end_s
    in_process = sum(1 for s in engine.samples if s.outcome is None)
    records = tuple(
        SampleRecord(
            sample_id=s.sample_id,
            priority=s.work_priority,
            arrival_s=s.arrival_s,
            finish_s=s.finish_s,
            outcome=s.outcome,
            runs=s.runs,
        )
        for s in engine.samples
    )
    queue_mean = {}
    for name, pool in engine.pools.items():
        if pool.resource is not None and pool.spec.kind is ResourceKind.UNIT:
            queue_mean[name] = pool.resource.requesters().length.mean()
        elif pool.queue is not None:
            queue_mean[name] = pool.queue.length.mean()
    capacities = {
        name: int(pool.spec.capacity)
        for name, pool in engine.pools.items()
        if pool.spec.kind is not ResourceKind.STORE
    }
    if options.animator is not None:
        options.animator.close()
    return RunResult(
        scenario=scenario_name,
        seed=options.seed,
        warm_up_s=0.0 if options.drain else scenario.warm_up_s,
        end_s=end_s,
        capacities=capacities,
        samples=records,
        busy=tuple(engine.busy),
        queue_mean=queue_mean,
        trace=tuple(engine.trace),
        arrivals_total=engine.arrivals_total,
        in_process=in_process,
        counters=dict(engine.counters),
    )

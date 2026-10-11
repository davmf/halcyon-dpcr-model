"""
Hand-built IR of the Halcyon dPCR-24 model.

Stand-in for the loader until the StrictDoc parser can read the process
model (see generator/loader.py). Every value and allocation is copied from
model/design/*.sysml and model/library/SimLib.sysml. Test-only: the
generator itself must not depend on this module.

Known deviation: the model has no assignment that sets `sample.invalid`.
`markInvalid` gets an assignment here, because its name and the invalid
rate in docs/design/capacity_estimate.md assume that it marks the sample.
See the report in docs/design/working_notes.md.
"""

from generator.ir import (
    Arrivals,
    Assignment,
    BatchArrivals,
    BernoulliGuard,
    Binary,
    Branch,
    CalcDef,
    Call,
    ConditionGuard,
    Decision,
    Distribution,
    Duration,
    Expr,
    Fork,
    Join,
    Literal,
    Merge,
    MetricKind,
    Model,
    Node,
    PoissonArrivals,
    Ref,
    Requirement,
    ResourceKind,
    ResourceSpec,
    Scenario,
    SimulationVerification,
    Step,
    Unary,
)

MINUTE = 60.0
HOUR = 3600.0
MILLILITRE = 1e-6  # m^3 per mL


def _lit(value: float) -> Expr:
    return Literal(value)


def _ref(name: str) -> Expr:
    return Ref(name)


def _mul(left: Expr, right: Expr) -> Expr:
    return Binary("*", left, right)


def _div(left: Expr, right: Expr) -> Expr:
    return Binary("/", left, right)


def _add(left: Expr, right: Expr) -> Expr:
    return Binary("+", left, right)


def _call(function: str, **arguments: Expr) -> Expr:
    return Call(function, tuple(sorted(arguments.items())))


def _calcs() -> dict[str, CalcDef]:
    """Calc defs of design/physics.sysml, with the model's pi."""
    pi = _lit(3.14159265)
    diameter, length = _ref("diameter"), _ref("length")
    pressure, viscosity = _ref("pressure"), _ref("viscosity")
    channel_volume = _div(
        _mul(_mul(pi, diameter), _mul(diameter, length)), _lit(4)
    )
    flow = _div(
        _mul(
            _mul(_mul(pi, diameter), _mul(diameter, diameter)),
            _mul(diameter, pressure),
        ),
        _mul(_mul(_lit(128), viscosity), length),
    )
    partition = _ref("partitionVolume")
    droplet = _ref("dropletVolume")
    frequency = _ref("frequency")
    hot_start, cycles = _ref("hotStart"), _ref("cycles")
    denature, anneal = _ref("denatureHold"), _ref("annealHold")
    ramp_delta, ramp_rate = _ref("rampDelta"), _ref("rampRate")
    thermal = _add(
        hot_start,
        _mul(
            cycles,
            _add(
                _add(denature, anneal),
                _div(_mul(_lit(2), ramp_delta), ramp_rate),
            ),
        ),
    )
    return {
        "ChannelVolume": CalcDef(
            "ChannelVolume", ("diameter", "length"), channel_volume
        ),
        "HagenPoiseuilleFlow": CalcDef(
            "HagenPoiseuilleFlow",
            ("pressure", "viscosity", "length", "diameter"),
            flow,
        ),
        "PrimingTime": CalcDef(
            "PrimingTime",
            ("pressure", "viscosity", "length", "diameter"),
            _div(
                _call(
                    "ChannelVolume",
                    diameter=diameter,
                    length=length,
                ),
                _call(
                    "HagenPoiseuilleFlow",
                    pressure=pressure,
                    viscosity=viscosity,
                    length=length,
                    diameter=diameter,
                ),
            ),
        ),
        "DropletCount": CalcDef(
            "DropletCount",
            ("partitionVolume", "dropletVolume"),
            _div(partition, droplet),
        ),
        "DropletGenerationTime": CalcDef(
            "DropletGenerationTime",
            ("partitionVolume", "dropletVolume", "frequency"),
            _div(partition, _mul(droplet, frequency)),
        ),
        "ThermalRunTime": CalcDef(
            "ThermalRunTime",
            (
                "hotStart",
                "cycles",
                "denatureHold",
                "annealHold",
                "rampDelta",
                "rampRate",
            ),
            thermal,
        ),
        "ImagingTime": CalcDef(
            "ImagingTime",
            ("channels", "timePerChannel"),
            _mul(_ref("channels"), _ref("timePerChannel")),
        ),
    }


def _fixed(nominal: float) -> Duration:
    return Duration(Distribution.FIXED, _lit(nominal))


def _step(
    name: str,
    duration: Duration,
    next_: tuple[str, ...] = (),
    allocations: tuple[str, ...] = (),
    consumes: int = 0,
    retest: bool = False,
    assignments: tuple[Assignment, ...] = (),
) -> Step:
    return Step(
        name=name,
        duration=duration,
        next=next_,
        allocations=allocations,
        consumes=consumes,
        retest=retest,
        assignments=assignments,
    )


def _nodes() -> dict[str, Node]:
    pressure = _ref("pneumatics.setPressure")
    prime_time = _call(
        "PrimingTime",
        pressure=pressure,
        viscosity=_ref("cartridge.fluidViscosity"),
        length=_ref("cartridge.primingPathLength"),
        diameter=_ref("cartridge.channelDiameter"),
    )
    generation = _call(
        "DropletGenerationTime",
        partitionVolume=_ref("cartridge.partitionVolume"),
        dropletVolume=_ref("generators.dropletVolume"),
        frequency=_ref("generators.dropletFrequency"),
    )
    thermal = _call(
        "ThermalRunTime",
        hotStart=_ref("blocks.hotStartTime"),
        cycles=_ref("blocks.cycles"),
        denatureHold=_ref("blocks.denatureHold"),
        annealHold=_ref("blocks.annealHold"),
        rampDelta=_ref("blocks.rampDelta"),
        rampRate=_ref("blocks.rampRate"),
    )
    imaging = _call(
        "ImagingTime",
        channels=_ref("imagers.channels"),
        timePerChannel=_ref("imagers.timePerChannel"),
    )
    invalid = "sample.invalid"
    bubble = BernoulliGuard(_ref("pBubble"))
    not_bubble = BernoulliGuard(_ref("pBubble"), negated=True)
    low = BernoulliGuard(_ref("pLowDroplets"))
    not_low = BernoulliGuard(_ref("pLowDroplets"), negated=True)
    reprime_triangle = Duration(
        Distribution.TRIANGULAR,
        _lit(30.0),
        low=_lit(20.0),
        high=_lit(40.0),
    )
    nodes: list[Node] = [
        # Intake: load, prime.
        _step("scanBarcode", _fixed(10.0), ("transferLoad",), ("rack",)),
        _step(
            "transferLoad",
            _fixed(30.0),
            ("primeCartridge",),
            ("shuttle",),
        ),
        _step(
            "primeCartridge",
            Duration(Distribution.FIXED, prime_time),
            ("bubble1",),
            ("stations", "pneumatics"),
        ),
        Decision(
            "bubble1",
            (
                Branch(bubble, "reprime"),
                Branch(not_bubble, "primed"),
            ),
        ),
        _step(
            "reprime",
            reprime_triangle,
            ("bubble2",),
            ("stations", "pneumatics"),
        ),
        Decision(
            "bubble2",
            (
                Branch(bubble, "abortCartridge"),
                Branch(not_bubble, "primed"),
            ),
        ),
        _step(
            "abortCartridge",
            _fixed(10.0),
            ("abortRetest",),
            ("stations",),
        ),
        _step("abortRetest", _fixed(0.0), (), (), retest=True),
        Merge("primed", ("pipette",)),
        # Extraction.
        _step("pipette", _fixed(60.0), ("lysis",), ("stations", "gantry")),
        _step("lysis", _fixed(360.0), ("beadBind",), ("stations",)),
        _step("beadBind", _fixed(180.0), ("washDispense1",), ("stations",)),
        _step(
            "washDispense1",
            _fixed(20.0),
            ("washCapture1",),
            ("stations", "gantry"),
        ),
        _step("washCapture1", _fixed(130.0), ("washDispense2",), ("stations",)),
        _step(
            "washDispense2",
            _fixed(20.0),
            ("washCapture2",),
            ("stations", "gantry"),
        ),
        _step("washCapture2", _fixed(130.0), ("split",), ("stations",)),
        Fork("split", ("elutionDispense", "masterMix")),
        _step(
            "elutionDispense",
            _fixed(20.0),
            ("elute",),
            ("stations", "gantry"),
        ),
        _step("elute", _fixed(240.0), ("joined",), ("stations",)),
        _step(
            "masterMix",
            _fixed(40.0),
            ("joined",),
            ("gantry", "reagentStore"),
            consumes=1,
        ),
        Join("joined", ("transferToPartition",)),
        _step(
            "transferToPartition",
            _fixed(30.0),
            ("meter",),
            ("shuttle",),
        ),
        # Partitioning.
        _step(
            "meter",
            _fixed(30.0),
            ("generate",),
            ("generators", "pneumatics"),
        ),
        _step(
            "generate",
            Duration(Distribution.FIXED, generation),
            ("lowCount1",),
            ("generators", "pneumatics"),
        ),
        Decision(
            "lowCount1",
            (
                Branch(low, "regenerate"),
                Branch(not_low, "partitioned"),
            ),
        ),
        _step(
            "regenerate",
            Duration(Distribution.FIXED, generation),
            ("lowCount2",),
            ("generators", "pneumatics"),
        ),
        Decision(
            "lowCount2",
            (
                Branch(low, "markInvalid"),
                Branch(not_low, "partitioned"),
            ),
        ),
        _step(
            "markInvalid",
            _fixed(0.0),
            ("partitioned",),
            assignments=(Assignment(invalid, _lit(1.0)),),
        ),
        Merge("partitioned", ("transferToAmplification",)),
        _step(
            "transferToAmplification",
            _fixed(30.0),
            ("thermalCycle",),
            ("shuttle",),
        ),
        # Amplification and readout.
        _step(
            "thermalCycle",
            Duration(Distribution.FIXED, thermal),
            ("transferToReadout",),
            ("blocks",),
        ),
        _step(
            "transferToReadout",
            _fixed(30.0),
            ("imaging",),
            ("shuttle",),
        ),
        _step(
            "imaging",
            Duration(Distribution.FIXED, imaging),
            ("poissonAnalysis",),
            ("imagers",),
        ),
        _step("poissonAnalysis", _fixed(60.0), ("invalidCheck",)),
        Decision(
            "invalidCheck",
            (
                Branch(ConditionGuard(_ref(invalid)), "reflexRetest"),
                Branch(
                    ConditionGuard(Unary("not", _ref(invalid))),
                    "report",
                ),
            ),
        ),
        _step("reflexRetest", _fixed(0.0), (), (), retest=True),
        _step("report", _fixed(0.0), ("transferToWaste",)),
        _step("transferToWaste", _fixed(30.0), (), ("shuttle",)),
    ]
    return {node.name: node for node in nodes}


def _resources(
    stations: int,
    pneumatics: int,
    generators: int,
    blocks: int,
    imagers: int,
) -> dict[str, ResourceSpec]:
    unit = ResourceKind.UNIT
    return {
        "rack": ResourceSpec("rack", unit, capacity=1),
        "shuttle": ResourceSpec("shuttle", unit, capacity=1),
        "gantry": ResourceSpec("gantry", unit, capacity=1),
        "stations": ResourceSpec("stations", unit, capacity=stations),
        "pneumatics": ResourceSpec("pneumatics", unit, capacity=pneumatics),
        "generators": ResourceSpec("generators", unit, capacity=generators),
        "blocks": ResourceSpec(
            "blocks",
            ResourceKind.BATCH,
            capacity=blocks,
            batch_size=4,
            batch_timeout_s=10 * MINUTE,
        ),
        "imagers": ResourceSpec("imagers", unit, capacity=imagers),
        "reagentStore": ResourceSpec(
            "reagentStore",
            ResourceKind.STORE,
            initial_level=100,
            reorder_level=20,
            refill_size=96,
            refill_duration_s=15 * MINUTE,
        ),
        "wasteStore": ResourceSpec(
            "wasteStore", ResourceKind.STORE, initial_level=0
        ),
    }


def _values() -> dict[str, float]:
    return {
        "pBubble": 0.05,
        "pLowDroplets": 0.03,
        "pneumatics.setPressure": 20000.0,
        "cartridge.fluidViscosity": 0.002,
        "cartridge.primingPathLength": 0.3,
        "cartridge.channelDiameter": 0.1e-3,
        "cartridge.channelCount": 4.0,
        "cartridge.partitionVolume": 0.017 * MILLILITRE,
        "generators.dropletVolume": 0.85e-6 * MILLILITRE,
        "generators.dropletFrequency": 120.0,
        "blocks.hotStartTime": 5 * MINUTE,
        "blocks.cycles": 40.0,
        "blocks.denatureHold": 15.0,
        "blocks.annealHold": 30.0,
        "blocks.rampDelta": 35.0,
        "blocks.rampRate": 4.0,
        "imagers.channels": 4.0,
        "imagers.timePerChannel": 45.0,
        "stations.heater.maxTemperature": 100.0,
        "reagentStore.initialLevel": 100.0,
    }


def _scenario(
    name: str,
    arrivals: Arrivals,
    stat_fraction: float,
    warm_up_s: float,
    capacities: tuple[int, int, int, int, int],
) -> Scenario:
    resources = _resources(*capacities)
    return Scenario(
        name=name,
        arrivals=arrivals,
        stat_fraction=stat_fraction,
        warm_up_s=warm_up_s,
        max_retests=1,
        values=_values(),
        resources=resources,
    )


def _scenarios() -> dict[str, Scenario]:
    base = (4, 2, 2, 2, 1)
    high = (4, 2, 2, 3, 2)
    steady = PoissonArrivals(rate_per_s=12.0 / HOUR)
    return {
        "baseBatch": _scenario(
            "baseBatch",
            BatchArrivals(count=24, time_s=0.0),
            0.0,
            0.0,
            base,
        ),
        "baseSteady": _scenario("baseSteady", steady, 0.1, HOUR, base),
        "highThroughput": _scenario("highThroughput", steady, 0.1, HOUR, high),
    }


def _requirements() -> dict[str, Requirement]:
    def compare(operator: str, measured: str, required: str) -> Expr:
        return Binary(operator, _ref(measured), _ref(required))

    specs = [
        (
            "SYS-THR-001",
            "Shift throughput",
            ">=",
            "measuredSamplesPerShift",
            "requiredSamplesPerShift",
            96.0,
        ),
        (
            "SYS-UTL-001",
            "Imager utilisation",
            "<=",
            "measuredImagerUtilisation",
            "requiredImagerUtilisation",
            0.85,
        ),
        (
            "SYS-TAT-001",
            "Time to first result",
            "<=",
            "measuredTimeToFirstResult",
            "requiredTimeToFirstResult",
            90 * MINUTE,
        ),
        (
            "SYS-TAT-002",
            "Mean turnaround",
            "<=",
            "measuredMeanTurnaround",
            "requiredMeanTurnaround",
            2.5 * HOUR,
        ),
        (
            "SYS-TAT-003",
            "STAT turnaround",
            "<=",
            "measuredMeanStatTurnaround",
            "requiredMeanStatTurnaround",
            2 * HOUR,
        ),
        (
            "SYS-VAL-001",
            "Invalid result rate",
            "<=",
            "measuredInvalidRate",
            "requiredInvalidRate",
            0.02,
        ),
    ]
    requirements: dict[str, Requirement] = {}
    for uid, title, operator, measured, required, threshold in specs:
        requirements[uid] = Requirement(
            uid=uid,
            title=title,
            statement="",
            constraint=compare(operator, measured, required),
            thresholds={required: threshold},
            measured_name=measured,
        )
    return requirements


def _verifications() -> tuple[SimulationVerification, ...]:
    return (
        SimulationVerification(
            "SYS-THR-001",
            "measuredSamplesPerShift",
            MetricKind.COMPLETED_PER_SHIFT,
            "baseSteady",
            8 * HOUR,
        ),
        SimulationVerification(
            "SYS-UTL-001",
            "measuredImagerUtilisation",
            MetricKind.UTILISATION,
            "baseSteady",
            8 * HOUR,
            resource="imagers",
        ),
        SimulationVerification(
            "SYS-TAT-001",
            "measuredTimeToFirstResult",
            MetricKind.TIME_TO_FIRST_RESULT,
            "baseBatch",
            3 * HOUR,
        ),
        SimulationVerification(
            "SYS-TAT-002",
            "measuredMeanTurnaround",
            MetricKind.MEAN_TURNAROUND,
            "baseSteady",
            16 * HOUR,
        ),
        SimulationVerification(
            "SYS-TAT-003",
            "measuredMeanStatTurnaround",
            MetricKind.MEAN_STAT_TURNAROUND,
            "baseSteady",
            16 * HOUR,
        ),
        SimulationVerification(
            "SYS-VAL-001",
            "measuredInvalidRate",
            MetricKind.INVALID_RATE,
            "baseSteady",
            16 * HOUR,
        ),
    )


def build_model() -> Model:
    """Return the Halcyon IR, matching the model files in model/."""
    return Model(
        name="Halcyon dPCR-24",
        start="scanBarcode",
        nodes=_nodes(),
        calcs=_calcs(),
        scenarios=_scenarios(),
        requirements=_requirements(),
        verifications=_verifications(),
    )

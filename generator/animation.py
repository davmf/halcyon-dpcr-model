"""
2D Salabim animation of the instrument layout, live or as video.

The layout is generated from the IR: one box per resource of the scenario,
in declaration order, in a grid. Nothing here is specific to Halcyon.

- Boxes are coloured by state: idle (grey), busy (blue) when every unit
  is claimed, waiting (orange) when a queue has formed.
- Each cartridge is a circle placed on the box of the resource it uses.
  A cartridge with no resource is drawn in the waiting area on the left.
- A poller process updates positions every 10 simulated seconds.
- A clock, the completed count, and the queue length of each resource are
  text labels.

Two modes:
- live: a desktop window (needs a display, tkinter).
- video: a file (.mp4 or .gif), created headless with blind animation.

The animator holds no simulation state. It reads the engine's samples and
pools, so it can be removed without changing the results.
"""

from pathlib import Path

import salabim as sim

from generator.ir import ResourceKind

VIDEO_SPEED = 60.0
WIDTH = 1200
HEIGHT = 720
BOX_W = 230
BOX_H = 130
COLUMNS = 4

IDLE = "#e4e3df"
BUSY = "#2a78d6"
WAITING = "#eb6834"
TEXT = "#0b0b0b"
SURFACE = "#fcfcfb"


class Animator:
    """Attaches to one replication. Create one per run."""

    def __init__(self, live: bool = False, video: Path | None = None) -> None:
        if live and video is not None:
            raise ValueError("choose live or video, not both")
        if not live and video is None:
            raise ValueError("choose live or video")
        self.live = live
        self.video = video
        self.env: sim.Environment | None = None
        self.engine: object | None = None
        self.boxes: dict[str, tuple[float, float]] = {}

    def attach(self, env: sim.Environment, engine: object) -> None:
        """Build the layout and start the poller. Called by the backend."""
        self.env = env
        self.engine = engine
        options = {
            "animate": True,
            "width": WIDTH,
            "height": HEIGHT,
            "x0": 0,
            "y0": 0,
            "x1": WIDTH,
            "background_color": SURFACE,
            "modelname": "dPCR analyser",
        }
        if self.video is not None:
            self.video.parent.mkdir(parents=True, exist_ok=True)
            options["video"] = str(self.video)
            options["fps"] = 25
            # Simulated seconds per video second: one hour takes a minute.
            options["speed"] = VIDEO_SPEED
        env.animation_parameters(**options)
        self._layout()
        _Poller(animator=self, engine=engine, drawing_env=env)

    def _layout(self) -> None:
        engine = self.engine
        assert engine is not None and self.env is not None
        env = self.env
        scenario = engine.scenario  # type: ignore[attr-defined]
        pools = engine.pools  # type: ignore[attr-defined]
        names = list(scenario.resources)
        for index, name in enumerate(names):
            column = index % COLUMNS
            row = index // COLUMNS
            x = 40 + column * (BOX_W + 40)
            y = HEIGHT - 110 - row * (BOX_H + 60)
            self.boxes[name] = (x + BOX_W / 2, y + BOX_H / 2)
            pool = pools[name]
            spec = pool.spec

            def colour(
                pool: object = pool,
            ) -> str:
                return _state_colour(pool)

            sim.AnimateRectangle(
                spec=(x, y, x + BOX_W, y + BOX_H),
                fillcolor=colour,
                linecolor=TEXT,
                env=env,
            )
            sim.AnimateText(
                text=spec.name,
                x=x + 8,
                y=y + BOX_H - 18,
                fontsize=16,
                textcolor=TEXT,
                env=env,
            )
            sim.AnimateText(
                text=lambda pool=pool: _pool_text(pool),
                x=x + 8,
                y=y + 14,
                fontsize=13,
                textcolor=TEXT,
                env=env,
            )
        sim.AnimateText(
            text=lambda: f"t = {self.env.now() / 3600:.2f} h",
            x=40,
            y=HEIGHT - 40,
            fontsize=18,
            textcolor=TEXT,
            env=env,
        )
        sim.AnimateText(
            text=lambda: f"completed: {_completed(engine)}",
            x=300,
            y=HEIGHT - 40,
            fontsize=18,
            textcolor=TEXT,
            env=env,
        )
        sim.AnimateText(
            text="waiting",
            x=20,
            y=60,
            fontsize=12,
            textcolor=TEXT,
            env=env,
        )

    def on_sample_created(self, sample: object) -> None:
        """Hook kept for symmetry. Circles are created by the poller."""
        del sample

    def close(self) -> None:
        if self.video is not None and self.env is not None:
            self.env.video_close()


def _state_colour(pool: object) -> str:
    spec = pool.spec  # type: ignore[attr-defined]
    if spec.kind is ResourceKind.STORE:
        return IDLE
    queue = pool.waiting if hasattr(pool, "waiting") else []  # type: ignore[attr-defined]
    if len(queue) > 0 or _queue_length(pool) > 0:
        return WAITING
    if _busy_units(pool) > 0:
        return BUSY
    return IDLE


def _queue_length(pool: object) -> int:
    resource = pool.resource  # type: ignore[attr-defined]
    if resource is not None:
        return len(resource.requesters())
    return 0


def _busy_units(pool: object) -> int:
    resource = pool.resource  # type: ignore[attr-defined]
    if resource is not None:
        return int(resource.claimed_quantity())
    return int(pool.spec.capacity - pool.free_units)  # type: ignore[attr-defined]


def _pool_text(pool: object) -> str:
    spec = pool.spec  # type: ignore[attr-defined]
    if spec.kind is ResourceKind.STORE:
        resource = pool.resource  # type: ignore[attr-defined]
        return f"stock {int(resource.available_quantity())}"
    return (
        f"busy {_busy_units(pool)}/{int(spec.capacity)}  "
        f"queue {len(pool.waiting) if spec.kind is ResourceKind.BATCH else _queue_length(pool)}"  # type: ignore[attr-defined]
    )


def _completed(engine: object) -> int:
    return sum(
        1
        for sample in engine.samples  # type: ignore[attr-defined]
        if sample.outcome is not None  # type: ignore[attr-defined]
    )


class _Poller(sim.Component):
    """Moves the cartridge circles every 10 simulated seconds."""

    def setup(
        self,
        animator: Animator,
        engine: object,
        drawing_env: sim.Environment,
    ) -> None:
        self.animator = animator
        self.engine = engine
        self.drawn: set[int] = set()
        self.drawing_env = drawing_env

    def process(self) -> None:
        while True:
            self._update()
            self.hold(10.0)

    def _update(self) -> None:
        engine = self.engine
        for sample in engine.samples:  # type: ignore[attr-defined]
            if sample.sample_id not in self.drawn:
                self.drawn.add(sample.sample_id)
                _draw_sample(self.animator, sample, self.drawing_env)
            _place(self.animator, sample)


def _place(animator: Animator, sample: object) -> None:
    current = getattr(sample, "current", ())
    if sample.outcome is not None:  # type: ignore[attr-defined]
        sample.anim_position = (8.0, 8.0)  # type: ignore[attr-defined]
        return
    if current:
        centre = animator.boxes.get(current[0], (600.0, 300.0))
        offset = (sample.sample_id % 5) * 14 - 28  # type: ignore[attr-defined]
        sample.anim_position = (centre[0] + offset, centre[1])  # type: ignore[attr-defined]
    else:
        sample.anim_position = (60.0 + (sample.sample_id % 6) * 16, 60.0)  # type: ignore[attr-defined]


def _draw_sample(
    animator: Animator, sample: object, env: sim.Environment
) -> None:
    sample.anim_position = (60.0, 60.0)  # type: ignore[attr-defined]
    sim.AnimateCircle(
        radius=6,
        x=lambda: sample.anim_position[0],  # type: ignore[attr-defined]
        y=lambda: sample.anim_position[1],  # type: ignore[attr-defined]
        fillcolor=lambda: (
            WAITING if sample.work_priority > 0 else BUSY  # type: ignore[attr-defined]
        ),
        linecolor=TEXT,
        env=env,
    )
    del animator

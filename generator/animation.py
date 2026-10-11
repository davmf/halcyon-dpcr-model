"""
2D Salabim animation of the instrument, live or as video.

Layout, generated from the IR and the scenario only:

- Title bar along the top: the scenario name.
- Stage area on the left. One box per resource, in the order the procedure
  first uses them (workflow order), in a grid of COLUMNS columns.
- Panel on the right: legend, clock, completed count, and live utilisation
  bars per resource with the queue length.
- A cartridge is a dot on the box of the resource it uses. Dots are routine
  (dark) or STAT (aqua). A dot with no resource keeps its last position.
- A batch resource shows its fill, for example "fill 3/4".

Box colours: idle grey, busy blue, waiting orange (a queue has formed).
The model has no faults, so no fault colour is drawn.

Two modes: live (desktop window, needs a display) and video (headless
blind animation, .mp4 or .gif). The animator only reads engine state.
"""

from pathlib import Path

import salabim as sim

from generator import ir
from generator.ir import ResourceKind

WIDTH = 1200
HEIGHT = 760
TITLE_H = 60
PANEL_X = 880
COLUMNS = 3
BOX_W = 250
BOX_H = 120
BOX_GAP_X = 30
BOX_GAP_Y = 40
STAGE_X = 40
STAGE_TOP = HEIGHT - TITLE_H - 60
POLL_S = 10.0
DEFAULT_SPEED = 60.0  # simulated seconds per wall-clock second
VIDEO_FPS = 25
GIF_FPS = 4

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
IDLE = "#e4e3df"
BUSY = "#2a78d6"
WAITING = "#eb6834"
ROUTINE_DOT = "#52514e"
STAT_DOT = "#1baf7a"
BAR_TRACK = "#e4e3df"


def workflow_order(model: ir.Model, scenario: ir.Scenario) -> list[str]:
    """Resources in the order the procedure first uses them, then the rest.

    Steps are visited in topological order, so a resource is placed where
    the procedure first needs it, not where a breadth-first walk reaches it.
    """
    order: list[str] = []
    seen: set[str] = set()
    for name in topological_order(model):
        node = model.nodes[name]
        if isinstance(node, ir.Step):
            for resource in node.allocations:
                if resource not in seen:
                    seen.add(resource)
                    order.append(resource)
    order.extend(name for name in scenario.resources if name not in seen)
    return [name for name in order if name in scenario.resources]


def topological_order(model: ir.Model) -> list[str]:
    """Nodes from the start to the ends, every node after its predecessors."""
    order: list[str] = []
    state: dict[str, int] = {}

    def visit(name: str) -> None:
        if state.get(name) is not None:
            return
        state[name] = 1
        for target in ir.successors(model.nodes[name]):
            visit(target)
        order.append(name)

    visit(model.start)
    order.reverse()
    return order


class Animator:
    """Attaches to one replication. Create one per run."""

    def __init__(
        self,
        live: bool = False,
        video: Path | None = None,
        gif: bool = False,
        speed: float = DEFAULT_SPEED,
    ) -> None:
        if live and video is not None:
            raise ValueError("choose live or video, not both")
        if not live and video is None:
            raise ValueError("choose live or video")
        if speed <= 0:
            raise ValueError("speed must be positive")
        self.live = live
        self.video = video
        self.gif = gif
        self.speed = speed
        self.env: sim.Environment | None = None
        self.engine: object | None = None
        self.centres: dict[str, tuple[float, float]] = {}

    def attach(self, env: sim.Environment, engine: object) -> None:
        """Set up the window or video, the layout, and the poller."""
        self.env = env
        self.engine = engine
        options: dict[str, object] = {
            "animate": True,
            "width": WIDTH,
            "height": HEIGHT,
            "x0": 0,
            "y0": 0,
            "x1": WIDTH,
            "background_color": SURFACE,
            "show_time": False,
            "show_fps": False,
            "show_menu_buttons": False,
            # An empty model name hides Salabim's default subtitle.
            "modelname": "",
            "speed": self.speed,
        }
        if self.video is not None:
            self.video.parent.mkdir(parents=True, exist_ok=True)
            options["video"] = str(self.video)
            options["fps"] = GIF_FPS if self.gif else VIDEO_FPS
        env.animation_parameters(**options)  # type: ignore[arg-type]
        self._title()
        self._stages()
        self._panel()
        _Poller(animator=self, engine=engine, drawing_env=env)

    def close(self) -> None:
        if self.video is not None and self.env is not None:
            self.env.video_close()

    # Layout -----------------------------------------------------------

    def _title(self) -> None:
        engine = self.engine
        assert engine is not None and self.env is not None
        name = engine.scenario.name  # type: ignore[attr-defined]
        sim.AnimateText(
            text=f"Halcyon dPCR-24  |  scenario {name}",
            x=STAGE_X,
            y=HEIGHT - 38,
            fontsize=20,
            textcolor=TEXT,
            env=self.env,
        )

    def _stages(self) -> None:
        engine = self.engine
        assert engine is not None and self.env is not None
        model = engine.model  # type: ignore[attr-defined]
        scenario = engine.scenario  # type: ignore[attr-defined]
        pools = engine.pools  # type: ignore[attr-defined]
        for index, name in enumerate(workflow_order(model, scenario)):
            column = index % COLUMNS
            row = index // COLUMNS
            x = STAGE_X + column * (BOX_W + BOX_GAP_X)
            top = STAGE_TOP - row * (BOX_H + BOX_GAP_Y)
            y = top - BOX_H
            self.centres[name] = (x + BOX_W / 2, y + BOX_H / 2)
            pool = pools[name]
            sim.AnimateRectangle(
                spec=(x, y, x + BOX_W, y + BOX_H),
                fillcolor=lambda pool=pool: _state_colour(pool),
                linecolor=TEXT_SECONDARY,
                env=self.env,
            )
            sim.AnimateText(
                text=_label(name, pool),
                x=x + 10,
                y=top - 22,
                fontsize=15,
                textcolor=TEXT,
                env=self.env,
            )
            sim.AnimateText(
                text=lambda pool=pool: _pool_text(pool),
                x=x + 10,
                y=y + 12,
                fontsize=12,
                textcolor=TEXT_SECONDARY,
                env=self.env,
            )

    def _panel(self) -> None:
        engine = self.engine
        assert engine is not None and self.env is not None
        env = self.env
        pools = engine.pools  # type: ignore[attr-defined]
        y = HEIGHT - TITLE_H - 30
        sim.AnimateText(
            text="Legend",
            x=PANEL_X,
            y=y,
            fontsize=15,
            textcolor=TEXT,
            env=env,
        )
        legend = [
            (IDLE, "box idle"),
            (BUSY, "box busy"),
            (WAITING, "box waiting (queue)"),
            (ROUTINE_DOT, "dot routine sample"),
            (STAT_DOT, "dot STAT sample"),
        ]
        for offset, (colour, text) in enumerate(legend):
            row_y = y - 26 - offset * 22
            sim.AnimateRectangle(
                spec=(PANEL_X, row_y - 6, PANEL_X + 14, row_y + 8),
                fillcolor=colour,
                linecolor=TEXT_SECONDARY,
                env=env,
            )
            sim.AnimateText(
                text=text,
                x=PANEL_X + 22,
                y=row_y - 4,
                fontsize=12,
                textcolor=TEXT_SECONDARY,
                env=env,
            )
        clock_y = y - 26 - len(legend) * 22 - 30
        sim.AnimateText(
            text=lambda: _clock_text(env),
            x=PANEL_X,
            y=clock_y,
            fontsize=17,
            textcolor=TEXT,
            env=env,
        )
        sim.AnimateText(
            text=lambda: f"completed: {_completed(engine)}",
            x=PANEL_X,
            y=clock_y - 28,
            fontsize=17,
            textcolor=TEXT,
            env=env,
        )
        sim.AnimateText(
            text="Utilisation (live)",
            x=PANEL_X,
            y=clock_y - 62,
            fontsize=14,
            textcolor=TEXT,
            env=env,
        )
        bar_top = clock_y - 90
        bar_width = 230.0
        names = [
            name
            for name in workflow_order(
                engine.model,  # type: ignore[attr-defined]
                engine.scenario,  # type: ignore[attr-defined]
            )
            if pools[name].spec.kind is not ResourceKind.STORE
        ]
        for index, name in enumerate(names):
            row_y = bar_top - index * 44
            sim.AnimateRectangle(
                spec=(PANEL_X, row_y - 8, PANEL_X + bar_width, row_y + 8),
                fillcolor=BAR_TRACK,
                linecolor=BAR_TRACK,
                env=env,
            )
            pool = pools[name]
            sim.AnimateRectangle(
                spec=lambda pool=pool, row_y=row_y: (
                    PANEL_X,
                    row_y - 8,
                    PANEL_X + bar_width * _utilisation_now(pool),
                    row_y + 8,
                ),
                fillcolor=BUSY,
                linecolor=BUSY,
                env=env,
            )
            sim.AnimateText(
                text=lambda pool=pool, name=name: (
                    f"{name}  {_utilisation_now(pool) * 100:3.0f}%  "
                    f"queue {_queue_now(pool)}"
                ),
                x=PANEL_X,
                y=row_y + 14,
                fontsize=11,
                textcolor=TEXT_SECONDARY,
                env=env,
            )


class _Poller(sim.Component):
    """Moves the dots every POLL_S simulated seconds."""

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
            self.hold(POLL_S)

    def _update(self) -> None:
        for sample in self.engine.samples:  # type: ignore[attr-defined]
            if sample.sample_id not in self.drawn:
                self.drawn.add(sample.sample_id)
                _draw_dot(sample, self.drawing_env)
            _place(self.animator, sample)


def _place(animator: Animator, sample: object) -> None:
    if sample.outcome is not None:  # type: ignore[attr-defined]
        # Finished samples leave the picture; the completed count keeps them.
        sample.anim_position = (-100.0, -100.0)  # type: ignore[attr-defined]
        return
    current = getattr(sample, "current", ())
    if current and current[0] in animator.centres:
        centre_x, centre_y = animator.centres[current[0]]
        offset = (sample.sample_id % 7 - 3) * 14.0  # type: ignore[attr-defined]
        sample.anim_position = (  # type: ignore[attr-defined]
            centre_x + offset,
            centre_y,
        )


def _draw_dot(sample: object, env: sim.Environment) -> None:
    sample.anim_position = (STAGE_X - 14.0, 60.0)  # type: ignore[attr-defined]
    sim.AnimateCircle(
        radius=6,
        x=lambda: sample.anim_position[0],  # type: ignore[attr-defined]
        y=lambda: sample.anim_position[1],  # type: ignore[attr-defined]
        fillcolor=lambda: (
            STAT_DOT
            if sample.work_priority > 0  # type: ignore[attr-defined]
            else ROUTINE_DOT
        ),
        linecolor=SURFACE,
        env=env,
    )


def _label(name: str, pool: object) -> str:
    spec = pool.spec  # type: ignore[attr-defined]
    return f"{name} ({spec.kind.value})"


def _state_colour(pool: object) -> str:
    spec = pool.spec  # type: ignore[attr-defined]
    if spec.kind is ResourceKind.STORE:
        return IDLE
    if _queue_now(pool) > 0:
        return WAITING
    if _busy_units(pool) > 0:
        return BUSY
    return IDLE


def _busy_units(pool: object) -> int:
    spec = pool.spec  # type: ignore[attr-defined]
    if spec.kind is ResourceKind.BATCH:
        return int(spec.capacity - pool.free_units)  # type: ignore[attr-defined]
    resource = pool.resource  # type: ignore[attr-defined]
    return int(resource.claimed_quantity())


def _utilisation_now(pool: object) -> float:
    spec = pool.spec  # type: ignore[attr-defined]
    return min(1.0, _busy_units(pool) / max(1, int(spec.capacity)))


def _queue_now(pool: object) -> int:
    spec = pool.spec  # type: ignore[attr-defined]
    if spec.kind is ResourceKind.BATCH:
        return len(pool.waiting)  # type: ignore[attr-defined]
    resource = pool.resource  # type: ignore[attr-defined]
    return len(resource.requesters())


def _pool_text(pool: object) -> str:
    spec = pool.spec  # type: ignore[attr-defined]
    if spec.kind is ResourceKind.STORE:
        resource = pool.resource  # type: ignore[attr-defined]
        return f"stock {int(resource.available_quantity())}"
    if spec.kind is ResourceKind.BATCH:
        members = len(pool.waiting)  # type: ignore[attr-defined]
        return (
            f"fill {min(members, spec.batch_size)}/{spec.batch_size}  "
            f"units busy {_busy_units(pool)}/{int(spec.capacity)}"
        )
    return f"busy {_busy_units(pool)}/{int(spec.capacity)}"


def _completed(engine: object) -> int:
    return sum(
        1
        for sample in engine.samples  # type: ignore[attr-defined]
        if sample.outcome is not None  # type: ignore[attr-defined]
    )


def _clock_text(env: sim.Environment) -> str:
    hours, rest = divmod(int(env.now()), 3600)
    minutes, seconds = divmod(rest, 60)
    return f"clock {hours:02d}:{minutes:02d}:{seconds:02d}"

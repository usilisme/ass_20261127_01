"""Simulation engine: runs every car's commands step by step. It has no I/O.

Rules:

* At step *n*, each car that is still active runs its *n*-th command. Cars go one
  after another, in the order they were given.
* A forward move that would leave the field is ignored, but it still uses up the step.
* A car with no commands left stays where it is (other cars can still hit it).
* A car that moves into a cell holding another car collides with it. All cars
  involved stop and run no further commands; their wrecks stay on the field.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from auto_driving.domain import Car, Command, Direction, Field, Position


@dataclass(frozen=True)
class Collision:
    """Where and when a car collided, and which car(s) it collided with."""

    with_cars: tuple[str, ...]
    position: Position
    step: int


@dataclass(frozen=True)
class CarResult:
    """A car's state at the end of a simulation."""

    name: str
    position: Position
    direction: Direction
    collision: Collision | None = None
    path: tuple[Position, ...] = ()
    """Every position the car occupied, in order: its start first, its final position last."""

    @property
    def collided(self) -> bool:
        return self.collision is not None


class _CarState:
    """State of one car that changes during a single simulation run."""

    __slots__ = ("car", "collision", "direction", "path", "position")

    def __init__(self, car: Car) -> None:
        self.car = car
        self.position = car.position
        self.direction = car.direction
        self.collision: Collision | None = None
        self.path: list[Position] = [car.position]

    @property
    def active(self) -> bool:
        return self.collision is None

    def to_result(self) -> CarResult:
        return CarResult(
            self.car.name, self.position, self.direction, self.collision, tuple(self.path)
        )


class Simulator:
    """Runs a set of cars on a field and returns each car's result."""

    def __init__(self, field: Field) -> None:
        self.field = field

    def run(self, cars: Sequence[Car]) -> list[CarResult]:
        """Simulate `cars` and return one result per car, in the same order.

        The input cars are never modified, so the same list can be run more than once.
        """
        states = [_CarState(car) for car in cars]
        total_steps = max((len(car.commands) for car in cars), default=0)

        for step in range(1, total_steps + 1):
            for state in states:
                if state.active and step <= len(state.car.commands):
                    self._apply(state, state.car.commands[step - 1], step, states)

        return [state.to_result() for state in states]

    def _apply(
        self, state: _CarState, command: Command, step: int, states: Sequence[_CarState]
    ) -> None:
        if command is Command.LEFT:
            state.direction = state.direction.turn_left()
        elif command is Command.RIGHT:
            state.direction = state.direction.turn_right()
        else:
            self._move_forward(state, step, states)

    def _move_forward(self, state: _CarState, step: int, states: Sequence[_CarState]) -> None:
        target = state.position.step(state.direction)
        if not self.field.contains(target):
            return  # would leave the field: ignore the command
        state.position = target
        state.path.append(target)

        occupants = [other for other in states if other is not state and other.position == target]
        if not occupants:
            return
        state.collision = Collision(tuple(o.car.name for o in occupants), target, step)
        for other in occupants:
            if other.active:  # a car that already crashed keeps its first collision
                other.collision = Collision((state.car.name,), target, step)

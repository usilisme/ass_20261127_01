"""Domain model: the immutable value objects the simulation works with."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Direction(Enum):
    """Compass direction a car faces. The value is the (dx, dy) of one forward step."""

    N = (0, 1)
    E = (1, 0)
    S = (0, -1)
    W = (-1, 0)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    def turn_left(self) -> Direction:
        return _CLOCKWISE[(_CLOCKWISE.index(self) - 1) % len(_CLOCKWISE)]

    def turn_right(self) -> Direction:
        return _CLOCKWISE[(_CLOCKWISE.index(self) + 1) % len(_CLOCKWISE)]


_CLOCKWISE: tuple[Direction, ...] = (Direction.N, Direction.E, Direction.S, Direction.W)


class Command(Enum):
    """A single instruction for a car."""

    LEFT = "L"
    RIGHT = "R"
    FORWARD = "F"


@dataclass(frozen=True)
class Position:
    """A grid coordinate. (0, 0) is the bottom-left corner."""

    x: int
    y: int

    def step(self, direction: Direction) -> Position:
        """Return the neighbouring position one step in `direction`."""
        return Position(self.x + direction.dx, self.y + direction.dy)

    def __str__(self) -> str:
        return f"({self.x},{self.y})"


@dataclass(frozen=True)
class Field:
    """Rectangular field. Valid coordinates are 0..width-1 by 0..height-1."""

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Field width and height must be positive.")

    def contains(self, position: Position) -> bool:
        return 0 <= position.x < self.width and 0 <= position.y < self.height


@dataclass(frozen=True)
class Car:
    """A car's initial configuration as the user entered it."""

    name: str
    position: Position
    direction: Direction
    commands: tuple[Command, ...] = ()

    @property
    def command_string(self) -> str:
        return "".join(command.value for command in self.commands)

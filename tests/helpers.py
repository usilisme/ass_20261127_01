"""Helpers shared by the test modules."""

from __future__ import annotations

from collections.abc import Iterable

from auto_driving.domain import Car, Direction, Position
from auto_driving.parsing import parse_commands


def make_car(name: str, x: int, y: int, direction: str, commands: str = "") -> Car:
    return Car(name, Position(x, y), Direction[direction], parse_commands(commands))


class ScriptedIO:
    """Feeds scripted input lines to the CLI and records everything it prints."""

    def __init__(self, inputs: Iterable[str]) -> None:
        self._inputs = iter(inputs)
        self.lines: list[str] = []

    def input(self) -> str:
        try:
            return next(self._inputs)
        except StopIteration:
            raise EOFError from None

    def output(self, line: str) -> None:
        self.lines.append(line)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

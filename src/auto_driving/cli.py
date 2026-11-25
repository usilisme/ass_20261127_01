"""Interactive command-line interface that follows the prompt flow in the specification.

Input and output functions are passed in (defaulting to `input` and `print`), so the
whole session can be driven and checked from tests.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import TextIO, TypeVar

from auto_driving.domain import Car, Field, Position
from auto_driving.formatting import format_car, format_result
from auto_driving.parsing import (
    ValidationError,
    parse_car_name,
    parse_commands,
    parse_field_size,
    parse_menu_choice,
    parse_position,
)
from auto_driving.simulator import Simulator
from auto_driving.visualization import ASCII_SYMBOLS, UNICODE_SYMBOLS, Symbols, render_field

T = TypeVar("T")
InputFn = Callable[[], str]
OutputFn = Callable[[str], None]

WELCOME = "Welcome to Auto Driving Car Simulation!"
FIELD_PROMPT = "Please enter the width and height of the simulation field in x y format:"
NAME_PROMPT = "Please enter the name of the car:"
SETUP_MENU = (
    "Please choose from the following options:",
    "[1] Add a car to field",
    "[2] Run simulation",
)
END_MENU = (
    "Please choose from the following options:",
    "[1] Start over",
    "[2] Exit",
)
GOODBYE = "Thank you for running the simulation. Goodbye!"
NO_CARS = "Invalid input: please add at least one car before running the simulation."


class _ExitRequested(Exception):
    """Internal signal: input ended (EOF) or the user pressed Ctrl-C."""


class AutoDrivingCLI:
    """One interactive session: field setup, adding cars, running, start over / exit."""

    def __init__(
        self,
        input_fn: InputFn = input,
        output_fn: OutputFn = print,
        *,
        show_grid: bool = True,
        color: bool = False,
        symbols: Symbols = UNICODE_SYMBOLS,
    ) -> None:
        """`show_grid` draws the field after each simulation; turn it off to get output that
        matches the specification exactly. `color` adds ANSI colours to the drawing."""
        self._input = input_fn
        self._output = output_fn
        self._show_grid = show_grid
        self._color = color
        self._symbols = symbols

    def run(self) -> None:
        try:
            while True:
                field = self._ask_field()
                cars = self._setup_cars(field)
                self._show_results(field, cars)
                if self._ask_menu(END_MENU) != "1":
                    break
        except _ExitRequested:
            pass
        self._say(GOODBYE)

    # ---- flow steps ---------------------------------------------------------

    def _ask_field(self) -> Field:
        self._say(WELCOME, "", FIELD_PROMPT)
        field = self._ask(parse_field_size, FIELD_PROMPT)
        self._say(f"You have created a field of {field.width} x {field.height}.", "")
        return field

    def _setup_cars(self, field: Field) -> list[Car]:
        cars: list[Car] = []
        while True:
            if self._ask_menu(SETUP_MENU) == "1":
                cars.append(self._ask_car(field, cars))
                self._say("Your current list of cars are:", *map(format_car, cars), "")
            elif not cars:
                self._say(NO_CARS, "")
            else:
                return cars

    def _ask_car(self, field: Field, cars: Sequence[Car]) -> Car:
        names = [car.name for car in cars]
        occupied: Mapping[Position, str] = {car.position: car.name for car in cars}

        self._say(NAME_PROMPT)
        name = self._ask(lambda text: parse_car_name(text, names), NAME_PROMPT)

        position_prompt = f"Please enter initial position of car {name} in x y Direction format:"
        self._say(position_prompt)
        position, direction = self._ask(
            lambda text: parse_position(text, field, occupied), position_prompt
        )

        commands_prompt = f"Please enter the commands for car {name}:"
        self._say(commands_prompt)
        commands = self._ask(parse_commands, commands_prompt)
        return Car(name, position, direction, commands)

    def _show_results(self, field: Field, cars: Sequence[Car]) -> None:
        results = Simulator(field).run(cars)
        self._say(
            "Your current list of cars are:",
            *map(format_car, cars),
            "",
            "After simulation, the result is:",
            *map(format_result, results),
            "",
        )
        if self._show_grid:
            self._say(*render_field(field, results, color=self._color, symbols=self._symbols), "")

    # ---- helpers ------------------------------------------------------------

    def _ask_menu(self, menu: Sequence[str]) -> str:
        self._say(*menu)
        return self._ask(parse_menu_choice, "\n".join(menu))

    def _ask(self, parser: Callable[[str], T], reprompt: str) -> T:
        """Read input until `parser` accepts it, showing the error and prompt again on bad input."""
        while True:
            try:
                text = self._input()
            except (EOFError, KeyboardInterrupt):
                raise _ExitRequested from None
            try:
                return parser(text)
            except ValidationError as error:
                self._say(f"Invalid input: {error}", reprompt)

    def _say(self, *lines: str) -> None:
        for line in lines:
            self._output(line)


def main(argv: Sequence[str] | None = None) -> int:
    """Console-script entry point."""
    args = _parse_args(argv)
    AutoDrivingCLI(
        show_grid=not args.no_grid,
        color=use_color(args.color, sys.stdout, os.environ),
        symbols=pick_symbols(sys.stdout),
    ).run()
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="auto-driving",
        description="Interactive simulation of autonomous cars on a rectangular field.",
    )
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="colour each car in the field drawing (default: auto, i.e. when writing to a "
        "terminal and NO_COLOR is not set)",
    )
    parser.add_argument(
        "--no-grid",
        action="store_true",
        help="do not draw the field after the simulation (output then matches the "
        "specification exactly)",
    )
    return parser.parse_args(argv)


def use_color(mode: str, stream: TextIO, environ: Mapping[str, str]) -> bool:
    """Decide whether to use colour, following the https://no-color.org convention."""
    if mode != "auto":
        return mode == "always"
    if "NO_COLOR" in environ or environ.get("TERM") == "dumb":
        return False
    return stream.isatty()


def pick_symbols(stream: TextIO) -> Symbols:
    """Use the Unicode symbols unless the output encoding cannot show them."""
    encoding = getattr(stream, "encoding", None)
    return UNICODE_SYMBOLS if UNICODE_SYMBOLS.can_be_encoded(encoding) else ASCII_SYMBOLS

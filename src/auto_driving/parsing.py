"""Turn the text a user typed into domain objects, or raise `ValidationError`.

Leading and trailing whitespace is ignored. Directions and commands can be typed in
lower case.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from auto_driving.domain import Command, Direction, Field, Position

_VALID_COMMANDS = frozenset(command.value for command in Command)


class ValidationError(ValueError):
    """Raised when user input is invalid. The message is meant to be shown to the user."""


def parse_field_size(text: str) -> Field:
    """Parse `"<width> <height>"`, e.g. `"10 10"`."""
    parts = text.split()
    if len(parts) != 2:
        raise ValidationError("Please enter exactly two numbers: width and height (e.g. 10 10).")
    width, height = _parse_ints(parts, "Width and height must be whole numbers (e.g. 10 10).")
    if width <= 0 or height <= 0:
        raise ValidationError("Width and height must be greater than zero.")
    return Field(width, height)


def parse_car_name(text: str, existing_names: Sequence[str]) -> str:
    """Parse a car name. It must be non-empty, unique and contain no comma."""
    name = text.strip()
    if not name:
        raise ValidationError("Car name cannot be empty.")
    if "," in name:
        raise ValidationError("Car name cannot contain a comma.")
    if name in existing_names:
        raise ValidationError(f"A car named {name} already exists. Please choose a unique name.")
    return name


def parse_position(
    text: str, field: Field, occupied: Mapping[Position, str]
) -> tuple[Position, Direction]:
    """Parse `"<x> <y> <Direction>"`, e.g. `"1 2 N"`.

    `occupied` maps the start positions of cars already added to their names.
    """
    parts = text.split()
    if len(parts) != 3:
        raise ValidationError("Please enter position as: x y Direction (e.g. 1 2 N).")
    x, y = _parse_ints(parts[:2], "x and y must be whole numbers.")
    try:
        direction = Direction[parts[2].upper()]
    except KeyError:
        raise ValidationError("Direction must be one of N, S, E, W.") from None

    position = Position(x, y)
    if not field.contains(position):
        raise ValidationError(
            f"Position {position} is outside the field. "
            f"x must be 0-{field.width - 1} and y must be 0-{field.height - 1}."
        )
    if position in occupied:
        raise ValidationError(
            f"Position {position} is already occupied by car {occupied[position]}."
        )
    return position, direction


def parse_commands(text: str) -> tuple[Command, ...]:
    """Parse a command string such as `"FFRFFFFRRL"`. An empty string is allowed."""
    raw = text.strip().upper()
    invalid = sorted(set(raw) - _VALID_COMMANDS)
    if invalid:
        raise ValidationError(
            f"Invalid command(s): {', '.join(invalid)}. "
            "Only L, R and F are allowed (e.g. FFRFFFFRRL)."
        )
    return tuple(Command(char) for char in raw)


def parse_menu_choice(text: str) -> str:
    """Parse a menu choice: `"1"` or `"2"`."""
    choice = text.strip()
    if choice not in ("1", "2"):
        raise ValidationError("Please enter 1 or 2.")
    return choice


def _parse_ints(parts: Sequence[str], message: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in parts)
    except ValueError:
        raise ValidationError(message) from None

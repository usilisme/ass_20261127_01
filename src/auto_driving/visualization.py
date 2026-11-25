"""Draw the field after a simulation: where each car started, its path, and where it ended.

Each car has its own colour. The symbols are:

* ``+``  the car's starting position
* ``·``  a cell the car drove through
* ``●``  the car's final position
* ``X``  a crash (drawn white on red, whichever cars were involved)

When marks share a cell, the more important one is drawn: crash > final > start > path.
If two cars have the same kind of mark in a cell, the car added later is drawn.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import IntEnum

from auto_driving.domain import Field, Position
from auto_driving.simulator import CarResult

# Bright then normal ANSI foreground colours. Red is left out so it only means "crash".
CAR_COLORS: tuple[str, ...] = ("96", "95", "93", "92", "94", "36", "35", "33", "32", "34")
CRASH_STYLE = "1;97;41"  # bold white on red

DEFAULT_MAX_WIDTH = 40
DEFAULT_MAX_HEIGHT = 40


class MarkKind(IntEnum):
    """What a cell shows. A higher value wins when several marks share a cell."""

    TRAIL = 1
    START = 2
    FINAL = 3
    CRASH = 4


@dataclass(frozen=True)
class Symbols:
    """The characters used to draw a grid."""

    trail: str
    start: str
    final: str
    crash: str
    horizontal: str
    vertical: str
    top_left: str
    top_right: str
    bottom_left: str
    bottom_right: str

    def for_kind(self, kind: MarkKind) -> str:
        return {
            MarkKind.TRAIL: self.trail,
            MarkKind.START: self.start,
            MarkKind.FINAL: self.final,
            MarkKind.CRASH: self.crash,
        }[kind]

    def can_be_encoded(self, encoding: str | None) -> bool:
        text = "".join(vars(self).values())
        try:
            text.encode(encoding or "ascii")
        except (UnicodeEncodeError, LookupError):
            return False
        return True


UNICODE_SYMBOLS = Symbols("·", "+", "●", "X", "─", "│", "┌", "┐", "└", "┘")
ASCII_SYMBOLS = Symbols(".", "+", "O", "X", "-", "|", "+", "+", "+", "+")


@dataclass(frozen=True)
class Mark:
    """What to draw in one cell, and which car (index into the results) it belongs to."""

    kind: MarkKind
    car_index: int


@dataclass(frozen=True)
class Viewport:
    """The part of the field being drawn (inclusive bounds)."""

    x_min: int
    x_max: int
    y_min: int
    y_max: int

    @property
    def width(self) -> int:
        return self.x_max - self.x_min + 1

    @property
    def height(self) -> int:
        return self.y_max - self.y_min + 1


def build_marks(results: Sequence[CarResult]) -> dict[Position, Mark]:
    """Work out which mark each cell shows. Cells with no mark are left out."""
    marks: dict[Position, Mark] = {}

    def place(position: Position, kind: MarkKind, car_index: int) -> None:
        current = marks.get(position)
        if current is None or kind >= current.kind:
            marks[position] = Mark(kind, car_index)

    for index, result in enumerate(results):
        path = result.path or (result.position,)
        for position in path[1:-1]:
            place(position, MarkKind.TRAIL, index)
        place(path[0], MarkKind.START, index)
        place(result.position, MarkKind.CRASH if result.collided else MarkKind.FINAL, index)
    return marks


def choose_viewport(
    field: Field, positions: Iterable[Position], max_width: int, max_height: int
) -> Viewport | None:
    """Return the area to draw: the whole field if it fits, otherwise the area the cars
    used (plus a one-cell margin). Returns None if even that is too big."""
    if field.width <= max_width and field.height <= max_height:
        return Viewport(0, field.width - 1, 0, field.height - 1)

    points = list(positions)
    if not points:
        return None
    viewport = Viewport(
        max(min(p.x for p in points) - 1, 0),
        min(max(p.x for p in points) + 1, field.width - 1),
        max(min(p.y for p in points) - 1, 0),
        min(max(p.y for p in points) + 1, field.height - 1),
    )
    if viewport.width > max_width or viewport.height > max_height:
        return None
    return viewport


def render_field(
    field: Field,
    results: Sequence[CarResult],
    *,
    color: bool = False,
    symbols: Symbols = UNICODE_SYMBOLS,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
) -> list[str]:
    """Return the lines of a drawing of the field, with a legend underneath."""
    marks = build_marks(results)
    viewport = choose_viewport(field, marks, max_width, max_height)
    if viewport is None:
        return [
            f"(The field is {field.width} x {field.height} and the cars' paths cover more than "
            f"{max_width} x {max_height} cells, which is too large to draw.)"
        ]

    lines: list[str] = []
    if (viewport.width, viewport.height) != (field.width, field.height):
        lines.append(
            f"Showing x {viewport.x_min}-{viewport.x_max}, y {viewport.y_min}-{viewport.y_max} "
            f"of the {field.width} x {field.height} field:"
        )
    lines.extend(_grid(viewport, marks, color, symbols))
    lines.append("")
    lines.extend(_legend(results, color, symbols))
    return lines


def _grid(
    viewport: Viewport, marks: dict[Position, Mark], color: bool, symbols: Symbols
) -> list[str]:
    label_width = len(str(viewport.y_max))
    cell_width = max(3, len(str(viewport.x_max)) + 1)
    margin = " " * label_width
    border = symbols.horizontal * (cell_width * viewport.width)

    lines = [f"{margin} {symbols.top_left}{border}{symbols.top_right}"]
    for y in range(viewport.y_max, viewport.y_min - 1, -1):
        cells = "".join(
            _cell(marks.get(Position(x, y)), cell_width, color, symbols)
            for x in range(viewport.x_min, viewport.x_max + 1)
        )
        lines.append(f"{y:>{label_width}} {symbols.vertical}{cells}{symbols.vertical}")
    lines.append(f"{margin} {symbols.bottom_left}{border}{symbols.bottom_right}")
    x_labels = "".join(
        f"{x:^{cell_width}}" for x in range(viewport.x_min, viewport.x_max + 1)
    ).rstrip()
    lines.append(f"{margin}  {x_labels}")
    return lines


def _cell(mark: Mark | None, width: int, color: bool, symbols: Symbols) -> str:
    if mark is None:
        return " " * width
    glyph = _paint(symbols.for_kind(mark.kind), _style(mark), color)
    left = (width - 1) // 2
    return " " * left + glyph + " " * (width - 1 - left)


def _legend(results: Sequence[CarResult], color: bool, symbols: Symbols) -> list[str]:
    crash = _paint(symbols.crash, CRASH_STYLE, color)
    cars = "   ".join(
        f"{_paint(symbols.final, car_color(index), color)} {result.name}"
        for index, result in enumerate(results)
    )
    return [
        f"Legend: {symbols.start} start   {symbols.trail} path   "
        f"{symbols.final} final position   {crash} crash",
        f"Cars:   {cars}",
    ]


def car_color(index: int) -> str:
    """ANSI colour code for the car at `index`. Colours repeat after len(CAR_COLORS) cars."""
    return CAR_COLORS[index % len(CAR_COLORS)]


def _style(mark: Mark) -> str:
    return CRASH_STYLE if mark.kind is MarkKind.CRASH else car_color(mark.car_index)


def _paint(text: str, style: str, color: bool) -> str:
    return f"\033[{style}m{text}\033[0m" if color else text

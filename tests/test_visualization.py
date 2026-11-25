import re

import pytest

from auto_driving.domain import Field, Position
from auto_driving.simulator import CarResult, Simulator
from auto_driving.visualization import (
    ASCII_SYMBOLS,
    CAR_COLORS,
    CRASH_STYLE,
    UNICODE_SYMBOLS,
    Mark,
    MarkKind,
    Viewport,
    build_marks,
    car_color,
    choose_viewport,
    render_field,
)

from .helpers import make_car

ANSI = re.compile(r"\033\[[0-9;]*m")


def simulate(field, *cars):
    return Simulator(field).run(list(cars))


def grid_rows(lines):
    """Map y -> row text inside the border, for a drawing without colour."""
    rows = {}
    for line in lines:
        match = re.match(r"^\s*(\d+) │(.*)│$", line)
        if match:
            rows[int(match.group(1))] = match.group(2)
    return rows


def cell(lines, x, y, x_min=0, cell_width=3):
    row = grid_rows(lines)[y]
    start = (x - x_min) * cell_width
    return row[start : start + cell_width].strip()


class TestBuildMarks:
    def test_single_car_start_trail_and_final(self):
        [result] = simulate(Field(5, 5), make_car("A", 0, 0, "N", "FFRF"))
        assert result.path == (Position(0, 0), Position(0, 1), Position(0, 2), Position(1, 2))
        assert build_marks([result]) == {
            Position(0, 0): Mark(MarkKind.START, 0),
            Position(0, 1): Mark(MarkKind.TRAIL, 0),
            Position(0, 2): Mark(MarkKind.TRAIL, 0),
            Position(1, 2): Mark(MarkKind.FINAL, 0),
        }

    def test_car_that_never_moves_shows_final_over_start(self):
        [result] = simulate(Field(5, 5), make_car("A", 2, 2, "N", "LR"))
        assert build_marks([result]) == {Position(2, 2): Mark(MarkKind.FINAL, 0)}

    def test_returning_to_start_keeps_final_on_top(self):
        [result] = simulate(Field(5, 5), make_car("A", 1, 1, "N", "FRRF"))
        assert build_marks([result])[Position(1, 1)] == Mark(MarkKind.FINAL, 0)

    def test_crash_cell_shows_crash_for_both_cars(self):
        a, b = simulate(
            Field(10, 10),
            make_car("A", 1, 2, "N", "FFRFFFFRRL"),
            make_car("B", 7, 8, "W", "FFLFFFFFFF"),
        )
        marks = build_marks([a, b])
        assert marks[Position(5, 4)].kind is MarkKind.CRASH
        assert marks[Position(1, 2)] == Mark(MarkKind.START, 0)
        assert marks[Position(7, 8)] == Mark(MarkKind.START, 1)
        assert marks[Position(1, 3)] == Mark(MarkKind.TRAIL, 0)
        assert marks[Position(5, 5)] == Mark(MarkKind.TRAIL, 1)

    def test_start_beats_another_cars_trail(self):
        # B moves away first, then A drives through B's starting cell.
        b, a = simulate(Field(5, 5), make_car("B", 1, 0, "N", "F"), make_car("A", 0, 0, "E", "FFF"))
        assert build_marks([b, a])[Position(1, 0)] == Mark(MarkKind.START, 0)

    def test_later_car_wins_a_tie(self):
        north = make_car("A", 0, 0, "N").direction
        a = CarResult(
            "A", Position(2, 0), north, path=(Position(0, 0), Position(1, 0), Position(2, 0))
        )
        b = CarResult(
            "B", Position(1, 2), north, path=(Position(1, 3), Position(1, 0), Position(1, 2))
        )
        assert build_marks([a, b])[Position(1, 0)] == Mark(MarkKind.TRAIL, 1)

    def test_result_without_path_uses_its_position(self):
        result = CarResult("A", Position(3, 3), make_car("A", 0, 0, "N").direction)
        assert build_marks([result]) == {Position(3, 3): Mark(MarkKind.FINAL, 0)}


class TestViewport:
    def test_whole_field_when_it_fits(self):
        assert choose_viewport(Field(10, 5), [], 40, 40) == Viewport(0, 9, 0, 4)

    def test_crops_large_field_to_used_area_with_margin(self):
        positions = [Position(100, 200), Position(105, 203)]
        assert choose_viewport(Field(1000, 1000), positions, 40, 40) == Viewport(99, 106, 199, 204)

    def test_margin_is_clipped_to_the_field(self):
        assert choose_viewport(Field(100, 100), [Position(0, 99)], 40, 40) == Viewport(0, 1, 98, 99)

    def test_too_large_to_draw(self):
        positions = [Position(0, 0), Position(500, 0)]
        assert choose_viewport(Field(1000, 1000), positions, 40, 40) is None

    def test_no_positions_on_large_field(self):
        assert choose_viewport(Field(1000, 1000), [], 40, 40) is None


class TestRenderField:
    def test_scenario_1_exact_drawing(self):
        results = simulate(Field(10, 10), make_car("A", 1, 2, "N", "FFRFFFFRRL"))
        assert render_field(Field(10, 10), results) == [
            "  ┌──────────────────────────────┐",
            "9 │                              │",
            "8 │                              │",
            "7 │                              │",
            "6 │                              │",
            "5 │                              │",
            "4 │    ·  ·  ·  ·  ●             │",
            "3 │    ·                         │",
            "2 │    +                         │",
            "1 │                              │",
            "0 │                              │",
            "  └──────────────────────────────┘",
            "    0  1  2  3  4  5  6  7  8  9",
            "",
            "Legend: + start   · path   ● final position   X crash",
            "Cars:   ● A",
        ]

    def test_scenario_2_crash_is_drawn(self):
        field = Field(10, 10)
        results = simulate(
            field, make_car("A", 1, 2, "N", "FFRFFFFRRL"), make_car("B", 7, 8, "W", "FFLFFFFFFF")
        )
        lines = render_field(field, results)
        assert cell(lines, 5, 4) == "X"
        assert cell(lines, 1, 2) == "+"
        assert cell(lines, 7, 8) == "+"
        assert cell(lines, 5, 6) == "·"
        assert "Cars:   ● A   ● B" in lines

    def test_each_car_gets_its_own_colour(self):
        field = Field(10, 10)
        results = simulate(field, make_car("A", 0, 0, "N", "F"), make_car("B", 5, 5, "E", "F"))
        text = "\n".join(render_field(field, results, color=True))
        assert f"\033[{CAR_COLORS[0]}m●\033[0m A" in text
        assert f"\033[{CAR_COLORS[1]}m●\033[0m B" in text
        assert f"\033[{CAR_COLORS[0]}m+\033[0m" in text
        assert f"\033[{CAR_COLORS[1]}m+\033[0m" in text

    def test_crash_uses_crash_style(self):
        field = Field(5, 5)
        results = simulate(field, make_car("A", 0, 0, "E", "F"), make_car("B", 1, 0, "N"))
        text = "\n".join(render_field(field, results, color=True))
        assert f"\033[{CRASH_STYLE}mX\033[0m" in text

    def test_colour_does_not_change_layout(self):
        field = Field(6, 4)
        results = simulate(field, make_car("A", 0, 0, "N", "FFRFF"), make_car("B", 5, 3, "S", "FF"))
        plain = render_field(field, results)
        coloured = [ANSI.sub("", line) for line in render_field(field, results, color=True)]
        assert coloured == plain

    def test_ascii_symbols(self):
        field = Field(3, 2)
        results = simulate(field, make_car("A", 0, 0, "E", "FF"))
        lines = render_field(field, results, symbols=ASCII_SYMBOLS)
        assert lines[:5] == [
            "  +---------+",
            "1 |         |",
            "0 | +  .  O |",
            "  +---------+",
            "    0  1  2",
        ]
        assert all(line.isascii() for line in lines)

    def test_large_field_is_cropped_with_a_note(self):
        field = Field(200, 200)
        results = simulate(field, make_car("A", 150, 150, "N", "FF"))
        lines = render_field(field, results)
        assert lines[0] == "Showing x 149-151, y 149-153 of the 200 x 200 field:"
        assert cell(lines[1:], 150, 152, x_min=149, cell_width=4) == "●"

    def test_too_large_field_shows_a_message(self):
        field = Field(500, 500)
        results = simulate(field, make_car("A", 0, 0, "E", "F" * 100))
        [line] = render_field(field, results)
        assert "too large to draw" in line

    @pytest.mark.parametrize("width", [3, 10, 40])
    def test_rows_have_equal_width(self, width):
        field = Field(width, 3)
        results = simulate(field, make_car("A", 0, 0, "E", "F" * width))
        rows = [line for line in render_field(field, results) if "│" in line or "┌" in line]
        assert len({len(row) for row in rows}) == 1


def test_car_colours_repeat_after_palette_runs_out():
    assert car_color(0) == car_color(len(CAR_COLORS))
    assert len(set(CAR_COLORS)) == len(CAR_COLORS)
    # Red is kept for crashes only.
    assert "31" not in CAR_COLORS
    assert "91" not in CAR_COLORS


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [("utf-8", True), ("ascii", False), ("cp1252", False), (None, False), ("nope", False)],
)
def test_unicode_symbols_encodability(encoding, expected):
    assert UNICODE_SYMBOLS.can_be_encoded(encoding) is expected
    assert ASCII_SYMBOLS.can_be_encoded(encoding) is (encoding != "nope")

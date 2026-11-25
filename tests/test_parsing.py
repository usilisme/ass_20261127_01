import pytest

from auto_driving.domain import Command, Direction, Field, Position
from auto_driving.parsing import (
    ValidationError,
    parse_car_name,
    parse_commands,
    parse_field_size,
    parse_menu_choice,
    parse_position,
)

FIELD = Field(10, 10)


class TestFieldSize:
    def test_valid(self):
        assert parse_field_size(" 10   5 ") == Field(10, 5)

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("", "exactly two numbers"),
            ("10", "exactly two numbers"),
            ("10 10 10", "exactly two numbers"),
            ("a b", "whole numbers"),
            ("10.5 3", "whole numbers"),
            ("0 10", "greater than zero"),
            ("10 -1", "greater than zero"),
        ],
    )
    def test_invalid(self, text, message):
        with pytest.raises(ValidationError, match=message):
            parse_field_size(text)


class TestCarName:
    def test_valid_and_stripped(self):
        assert parse_car_name("  Car 1 ", []) == "Car 1"

    @pytest.mark.parametrize(
        ("text", "existing", "message"),
        [
            ("", [], "cannot be empty"),
            ("   ", [], "cannot be empty"),
            ("A", ["A"], "already exists"),
            ("A,B", [], "comma"),
        ],
    )
    def test_invalid(self, text, existing, message):
        with pytest.raises(ValidationError, match=message):
            parse_car_name(text, existing)

    def test_names_are_case_sensitive(self):
        assert parse_car_name("a", ["A"]) == "a"


class TestPosition:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("1 2 N", (Position(1, 2), Direction.N)),
            ("1 2 n", (Position(1, 2), Direction.N)),
            ("9 9 W", (Position(9, 9), Direction.W)),
            ("  0   0  s ", (Position(0, 0), Direction.S)),
        ],
    )
    def test_valid(self, text, expected):
        assert parse_position(text, FIELD, {}) == expected

    @pytest.mark.parametrize(
        ("text", "message"),
        [
            ("", "x y Direction"),
            ("1 2", "x y Direction"),
            ("1 2 N X", "x y Direction"),
            ("a 2 N", "whole numbers"),
            ("1 2 X", "N, S, E, W"),
            ("1 2 NE", "N, S, E, W"),
            ("10 0 N", "outside the field"),
            ("0 10 N", "outside the field"),
            ("-1 0 N", "outside the field"),
        ],
    )
    def test_invalid(self, text, message):
        with pytest.raises(ValidationError, match=message):
            parse_position(text, FIELD, {})

    def test_already_occupied(self):
        with pytest.raises(ValidationError, match="occupied by car A"):
            parse_position("1 2 N", FIELD, {Position(1, 2): "A"})


class TestCommands:
    def test_valid_and_case_insensitive(self):
        assert parse_commands(" ffr ") == (Command.FORWARD, Command.FORWARD, Command.RIGHT)

    def test_empty_is_allowed(self):
        assert parse_commands("") == ()

    @pytest.mark.parametrize(("text", "bad"), [("FFX", "X"), ("F F", " "), ("1F2", "1, 2")])
    def test_invalid(self, text, bad):
        with pytest.raises(ValidationError, match=f"Invalid command\\(s\\): {bad}\\."):
            parse_commands(text)


class TestMenuChoice:
    @pytest.mark.parametrize("text", ["1", " 2 "])
    def test_valid(self, text):
        assert parse_menu_choice(text) == text.strip()

    @pytest.mark.parametrize("text", ["", "0", "3", "one", "1 2"])
    def test_invalid(self, text):
        with pytest.raises(ValidationError):
            parse_menu_choice(text)

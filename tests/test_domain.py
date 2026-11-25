import pytest

from auto_driving.domain import Car, Command, Direction, Field, Position


class TestDirection:
    def test_turn_right_cycles_clockwise(self):
        seen = []
        direction = Direction.N
        for _ in range(4):
            direction = direction.turn_right()
            seen.append(direction)
        assert seen == [Direction.E, Direction.S, Direction.W, Direction.N]

    def test_turn_left_cycles_counter_clockwise(self):
        seen = []
        direction = Direction.N
        for _ in range(4):
            direction = direction.turn_left()
            seen.append(direction)
        assert seen == [Direction.W, Direction.S, Direction.E, Direction.N]

    @pytest.mark.parametrize("direction", list(Direction))
    def test_left_then_right_is_identity(self, direction):
        assert direction.turn_left().turn_right() is direction


class TestPosition:
    @pytest.mark.parametrize(
        ("direction", "expected"),
        [
            (Direction.N, Position(5, 6)),
            (Direction.S, Position(5, 4)),
            (Direction.E, Position(6, 5)),
            (Direction.W, Position(4, 5)),
        ],
    )
    def test_step(self, direction, expected):
        assert Position(5, 5).step(direction) == expected

    def test_str(self):
        assert str(Position(1, 2)) == "(1,2)"


class TestField:
    @pytest.mark.parametrize(
        ("x", "y", "inside"),
        [
            (0, 0, True),
            (9, 9, True),
            (10, 9, False),
            (9, 10, False),
            (-1, 0, False),
            (0, -1, False),
        ],
    )
    def test_contains(self, x, y, inside):
        assert Field(10, 10).contains(Position(x, y)) is inside

    @pytest.mark.parametrize(("width", "height"), [(0, 5), (5, 0), (-1, 5)])
    def test_rejects_non_positive_size(self, width, height):
        with pytest.raises(ValueError, match="must be positive"):
            Field(width, height)


def test_car_command_string():
    car = Car("A", Position(0, 0), Direction.N, (Command.FORWARD, Command.LEFT, Command.RIGHT))
    assert car.command_string == "FLR"

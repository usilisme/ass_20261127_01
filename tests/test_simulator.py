import pytest

from auto_driving.domain import Direction, Field, Position
from auto_driving.simulator import Collision, Simulator

from .helpers import make_car


@pytest.fixture
def sim() -> Simulator:
    return Simulator(Field(10, 10))


class TestSpecScenarios:
    def test_scenario_1_single_car(self, sim):
        [result] = sim.run([make_car("A", 1, 2, "N", "FFRFFFFRRL")])
        assert result.position == Position(5, 4)
        assert result.direction is Direction.S
        assert not result.collided

    def test_scenario_2_two_cars_collide(self, sim):
        a, b = sim.run(
            [make_car("A", 1, 2, "N", "FFRFFFFRRL"), make_car("B", 7, 8, "W", "FFLFFFFFFF")]
        )
        assert a.collision == Collision(("B",), Position(5, 4), 7)
        assert b.collision == Collision(("A",), Position(5, 4), 7)

    def test_collided_cars_stop_processing_commands(self, sim):
        a, b = sim.run(
            [make_car("A", 1, 2, "N", "FFRFFFFRRL"), make_car("B", 7, 8, "W", "FFLFFFFFFF")]
        )
        # A's remaining "RRL" and B's remaining "FFF" are never run.
        assert (a.position, a.direction) == (Position(5, 4), Direction.E)
        assert (b.position, b.direction) == (Position(5, 4), Direction.S)


class TestBoundaries:
    def test_moving_off_the_field_is_ignored(self, sim):
        [result] = sim.run([make_car("A", 0, 0, "S", "F")])
        assert (result.position, result.direction) == (Position(0, 0), Direction.S)

    def test_ignored_move_still_uses_its_step(self):
        [result] = Simulator(Field(3, 3)).run([make_car("A", 2, 2, "N", "FFFLF")])
        assert (result.position, result.direction) == (Position(1, 2), Direction.W)

    @pytest.mark.parametrize(
        ("direction", "x", "y"), [("N", 2, 2), ("S", 2, 0), ("E", 4, 1), ("W", 0, 1)]
    )
    def test_each_edge_is_enforced(self, direction, x, y):
        [result] = Simulator(Field(5, 3)).run([make_car("A", x, y, direction, "FFFF")])
        assert result.position == Position(x, y)

    def test_one_by_one_field(self):
        [result] = Simulator(Field(1, 1)).run([make_car("A", 0, 0, "N", "FRFRFRF")])
        assert (result.position, result.direction) == (Position(0, 0), Direction.W)


class TestCommandLengths:
    def test_car_with_fewer_commands_stays_put(self, sim):
        a, b = sim.run([make_car("A", 0, 0, "N", "F"), make_car("B", 5, 5, "E", "FFFF")])
        assert a.position == Position(0, 1)
        assert b.position == Position(9, 5)

    def test_car_with_no_commands(self, sim):
        [result] = sim.run([make_car("A", 3, 3, "W")])
        assert (result.position, result.direction, result.collision) == (
            Position(3, 3),
            Direction.W,
            None,
        )

    def test_no_cars(self, sim):
        assert sim.run([]) == []


class TestCollisions:
    def test_hitting_a_stationary_car(self, sim):
        a, b = sim.run([make_car("A", 0, 0, "E", "FF"), make_car("B", 2, 0, "N")])
        assert a.collision == Collision(("B",), Position(2, 0), 2)
        assert b.collision == Collision(("A",), Position(2, 0), 2)

    def test_head_on_cars_collide_when_first_moves_into_second(self, sim):
        # Cars move one after another, so A moves into B's cell before B moves.
        a, b = sim.run([make_car("A", 0, 0, "E", "F"), make_car("B", 1, 0, "W", "F")])
        assert a.collision == Collision(("B",), Position(1, 0), 1)
        assert b.collision == Collision(("A",), Position(1, 0), 1)

    def test_car_moving_away_in_same_step_avoids_collision(self, sim):
        # B goes first and moves away, so A can take B's old cell.
        b, a = sim.run([make_car("B", 1, 0, "E", "F"), make_car("A", 0, 0, "E", "F")])
        assert not (a.collided)
        assert not (b.collided)
        assert (a.position, b.position) == (Position(1, 0), Position(2, 0))

    def test_third_car_hits_existing_wreck(self, sim):
        a, b, c = sim.run(
            [
                make_car("A", 0, 0, "E", "F"),
                make_car("B", 1, 0, "N"),
                make_car("C", 1, 2, "S", "FF"),
            ]
        )
        assert a.collision == Collision(("B",), Position(1, 0), 1)
        assert b.collision == Collision(("A",), Position(1, 0), 1)  # keeps its first collision
        assert c.collision == Collision(("A", "B"), Position(1, 0), 2)

    def test_uncollided_cars_continue_after_others_crash(self, sim):
        a, b, c = sim.run(
            [
                make_car("A", 0, 0, "E", "F"),
                make_car("B", 1, 0, "N"),
                make_car("C", 5, 5, "N", "FFF"),
            ]
        )
        assert a.collided
        assert b.collided
        assert (c.position, c.collision) == (Position(5, 8), None)

    def test_rotation_never_causes_collision(self, sim):
        a, b = sim.run([make_car("A", 0, 0, "N", "LRLR"), make_car("B", 9, 9, "S", "RLRL")])
        assert not (a.collided)
        assert not (b.collided)


class TestPurity:
    def test_input_cars_are_not_modified(self, sim):
        car = make_car("A", 1, 2, "N", "FFRFFFFRRL")
        sim.run([car])
        assert (car.position, car.direction) == (Position(1, 2), Direction.N)

    def test_simulation_is_repeatable(self, sim):
        cars = [make_car("A", 1, 2, "N", "FFRFFFFRRL"), make_car("B", 7, 8, "W", "FFLFFFFFFF")]
        assert sim.run(cars) == sim.run(cars)

"""How cars and results are shown to the user."""

from __future__ import annotations

from auto_driving.domain import Car
from auto_driving.simulator import CarResult


def format_car(car: Car) -> str:
    """E.g. `- A, (1,2) N, FFRFFFFRRL`."""
    return f"- {car.name}, {car.position} {car.direction.name}, {car.command_string}"


def format_result(result: CarResult) -> str:
    """E.g. `- A, (5,4) S` or `- A, collides with B at (5,4) at step 7`."""
    if result.collision is not None:
        collision = result.collision
        others = ", ".join(collision.with_cars)
        return (
            f"- {result.name}, collides with {others} "
            f"at {collision.position} at step {collision.step}"
        )
    return f"- {result.name}, {result.position} {result.direction.name}"

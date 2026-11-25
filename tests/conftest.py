"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Callable, Iterable

import pytest

from auto_driving.cli import AutoDrivingCLI

from .helpers import ScriptedIO


@pytest.fixture
def run_cli() -> Callable[[Iterable[str]], str]:
    """Run a whole CLI session with the given input lines and return everything printed."""

    def _run(inputs: Iterable[str]) -> str:
        io = ScriptedIO(inputs)
        AutoDrivingCLI(io.input, io.output, show_grid=False).run()
        return io.text

    return _run


@pytest.fixture
def run_cli_with_grid() -> Callable[[Iterable[str]], str]:
    """Like `run_cli`, but draws the field (without colour) after each simulation."""

    def _run(inputs: Iterable[str]) -> str:
        io = ScriptedIO(inputs)
        AutoDrivingCLI(io.input, io.output, show_grid=True, color=False).run()
        return io.text

    return _run

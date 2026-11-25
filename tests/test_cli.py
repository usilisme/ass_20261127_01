"""End-to-end tests that drive a whole CLI session and check the printed transcript."""

import io
import subprocess
import sys

import pytest

from auto_driving.cli import GOODBYE, WELCOME, main, pick_symbols, use_color
from auto_driving.visualization import ASCII_SYMBOLS, UNICODE_SYMBOLS

SCENARIO_1_INPUT = ["10 10", "1", "A", "1 2 N", "FFRFFFFRRL", "2", "2"]

SCENARIO_1_TRANSCRIPT = """\
Welcome to Auto Driving Car Simulation!

Please enter the width and height of the simulation field in x y format:
You have created a field of 10 x 10.

Please choose from the following options:
[1] Add a car to field
[2] Run simulation
Please enter the name of the car:
Please enter initial position of car A in x y Direction format:
Please enter the commands for car A:
Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL

Please choose from the following options:
[1] Add a car to field
[2] Run simulation
Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL

After simulation, the result is:
- A, (5,4) S

Please choose from the following options:
[1] Start over
[2] Exit
Thank you for running the simulation. Goodbye!"""

SCENARIO_2_RESULT = """\
Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL
- B, (7,8) W, FFLFFFFFFF

After simulation, the result is:
- A, collides with B at (5,4) at step 7
- B, collides with A at (5,4) at step 7

Please choose from the following options:
[1] Start over
[2] Exit
Thank you for running the simulation. Goodbye!"""


def test_scenario_1_transcript(run_cli):
    assert run_cli(SCENARIO_1_INPUT) == SCENARIO_1_TRANSCRIPT


def test_scenario_2_transcript(run_cli):
    out = run_cli(
        ["10 10", "1", "A", "1 2 N", "FFRFFFFRRL", "1", "B", "7 8 W", "FFLFFFFFFF", "2", "2"]
    )
    assert (
        "Your current list of cars are:\n"
        "- A, (1,2) N, FFRFFFFRRL\n"
        "- B, (7,8) W, FFLFFFFFFF\n"
        "\n"
        "Please choose from the following options:\n"
        "[1] Add a car to field\n"
        "[2] Run simulation\n"
    ) in out
    assert out.endswith(SCENARIO_2_RESULT)


def test_start_over_resets_field_and_cars(run_cli):
    out = run_cli(
        ["10 10", "1", "A", "0 0 N", "F", "2", "1", "5 5", "1", "Z", "4 4 E", "F", "2", "2"]
    )
    assert out.count(WELCOME) == 2
    assert "You have created a field of 5 x 5." in out
    assert out.endswith(
        "After simulation, the result is:\n- Z, (4,4) E\n\n"
        "Please choose from the following options:\n[1] Start over\n[2] Exit\n" + GOODBYE
    )


def test_invalid_inputs_are_reported_and_reprompted(run_cli):
    out = run_cli(
        [
            "a b", "10", "10 10",           # non-numeric, one number, then valid
            "3", "2", "1",                  # bad menu choice, run with no cars, add a car
            "", "A",                        # empty name
            "1 2 Q", "99 1 N", "1 2 N",     # bad direction, outside the field
            "FFX", "FF",                    # bad command
            "1", "A", "B",                  # duplicate name
            "1 2 S", "3 3 S",               # occupied position
            "",                             # B has no commands
            "2", "9", "2",                  # run, bad end-menu choice, exit
        ]
    )  # fmt: skip
    expected_errors = [
        "Invalid input: Width and height must be whole numbers",
        "Invalid input: Please enter exactly two numbers",
        "Invalid input: Please enter 1 or 2.",
        "Invalid input: please add at least one car",
        "Invalid input: Car name cannot be empty.",
        "Invalid input: Direction must be one of N, S, E, W.",
        "Invalid input: Position (99,1) is outside the field.",
        "Invalid input: Invalid command(s): X.",
        "Invalid input: A car named A already exists.",
        "Invalid input: Position (1,2) is already occupied by car A.",
    ]
    for error in expected_errors:
        assert error in out
    assert out.count("Invalid input: Please enter 1 or 2.") == 2
    assert "After simulation, the result is:\n- A, (1,4) N\n- B, (3,3) S\n" in out
    assert out.endswith(GOODBYE)


def test_error_is_followed_by_the_same_prompt(run_cli):
    lines = run_cli(["x", "10 10", "2", "2"]).splitlines()
    error_index = next(i for i, line in enumerate(lines) if line.startswith("Invalid input"))
    assert lines[error_index + 1] == (
        "Please enter the width and height of the simulation field in x y format:"
    )


def test_eof_exits_cleanly(run_cli):
    assert run_cli([]).endswith(GOODBYE)
    assert run_cli(["10 10", "1", "A"]).endswith(GOODBYE)


def test_module_entry_point_runs_end_to_end():
    completed = subprocess.run(
        [sys.executable, "-m", "auto_driving", "--no-grid"],
        input="\n".join(SCENARIO_1_INPUT) + "\n",
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert completed.stdout.rstrip("\n") == SCENARIO_1_TRANSCRIPT


def test_main_reads_stdin_and_returns_zero(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(SCENARIO_1_INPUT) + "\n"))
    assert main(["--no-grid"]) == 0
    assert capsys.readouterr().out.rstrip("\n") == SCENARIO_1_TRANSCRIPT


class TestGrid:
    def test_grid_is_drawn_after_results_and_before_menu(self, run_cli_with_grid):
        out = run_cli_with_grid(SCENARIO_1_INPUT)
        assert (
            "After simulation, the result is:\n- A, (5,4) S\n\n  ┌──────────────────────────────┐\n"
        ) in out
        assert "4 │    ·  ·  ·  ·  ●             │" in out
        assert "2 │    +                         │" in out
        assert ("Cars:   ● A\n\nPlease choose from the following options:\n[1] Start over") in out

    def test_grid_shows_crash(self, run_cli_with_grid):
        out = run_cli_with_grid(
            ["10 10", "1", "A", "1 2 N", "FFRFFFFRRL", "1", "B", "7 8 W", "FFLFFFFFFF", "2", "2"]
        )
        assert "4 │    ·  ·  ·  ·  X             │" in out
        assert "Cars:   ● A   ● B" in out

    def test_no_grid_flag_matches_spec_exactly(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(SCENARIO_1_INPUT) + "\n"))
        main(["--no-grid"])
        assert "┌" not in capsys.readouterr().out

    def test_grid_is_on_by_default_and_plain_when_piped(self, monkeypatch, capsys):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(SCENARIO_1_INPUT) + "\n"))
        main([])
        out = capsys.readouterr().out
        assert "Legend:" in out
        assert "\033[" not in out  # captured output is not a terminal

    def test_color_always_adds_ansi_codes(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", io.StringIO("\n".join(SCENARIO_1_INPUT) + "\n"))
        main(["--color=always"])
        assert "\033[96m●\033[0m A" in capsys.readouterr().out

    def test_invalid_option_is_rejected(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--color=purple"])
        assert exc.value.code == 2


class _FakeStream:
    def __init__(self, tty, encoding="utf-8"):
        self._tty = tty
        self.encoding = encoding

    def isatty(self):
        return self._tty


@pytest.mark.parametrize(
    ("mode", "tty", "environ", "expected"),
    [
        ("always", False, {"NO_COLOR": "1"}, True),
        ("never", True, {}, False),
        ("auto", True, {}, True),
        ("auto", False, {}, False),
        ("auto", True, {"NO_COLOR": ""}, False),
        ("auto", True, {"TERM": "dumb"}, False),
    ],
)
def test_use_color(mode, tty, environ, expected):
    assert use_color(mode, _FakeStream(tty), environ) is expected


@pytest.mark.parametrize(
    ("encoding", "expected"),
    [
        ("utf-8", UNICODE_SYMBOLS),
        ("UTF-8", UNICODE_SYMBOLS),
        ("cp1252", ASCII_SYMBOLS),
        (None, ASCII_SYMBOLS),
    ],
)
def test_pick_symbols(encoding, expected):
    assert pick_symbols(_FakeStream(False, encoding)) is expected
